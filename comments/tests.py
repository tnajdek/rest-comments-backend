# coding=utf-8
import random

from StringIO import StringIO

from datetime import datetime
from functools import partial
from mock import patch
from model_mommy import mommy

from django.test import TestCase, RequestFactory
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.utils import timezone

from rest_framework.exceptions import ParseError

from .models import Site, Comment
from .views import SubmitCommentView, PublicCommentsView, ModerateCommentView
from .processing import process_comment
from .migrate import migrate_wordpress


class BaseTestCase(TestCase):
	def setUp(self):
		self.factory = RequestFactory()
		self.site = mommy.make(Site)
		self.kwargs = {
			'token': self.site.public_token,
		}

		self.submit_comment_request = partial(
			self.factory.post,
			reverse('api:submit_comment', kwargs=self.kwargs),
			HTTP_USER_AGENT='Mozilla/5.0'
		)


class SubmitCommentsTestCase(BaseTestCase):
	def setUp(self):
		super(SubmitCommentsTestCase, self).setUp()
		self.site.require_akismet_approval = False
		self.site.require_user_approval = False
		self.site.save()

		self.comment_data = {
			'author_name': 'test comment',
			'comment': 'text comment',
			'author_website': 'www.example.com',
			'author_email': 'aloha@example.com',
			'post_slug': 'some-article'
		}
		self.request = self.submit_comment_request(
			data=self.comment_data
		)

	def test_can_submit_comment(self):
		response = SubmitCommentView.as_view()(self.request, **self.kwargs)
		self.assertEqual(response.status_code, 201)
		comments = Comment.objects.all()
		self.assertEqual(len(comments), 1)
		self.assertEqual(comments[0].author_name, 'test comment')
		self.assertEqual(comments[0].client_ip, '127.0.0.1')

	def test_wrong_tokens_are_rejected(self):
		kwargs = {
			'token': 'jabberish',
		}
		self.factory.post('api:submit_comment', kwargs=kwargs, HTTP_USER_AGENT='Mozilla/5.0')

		response = SubmitCommentView.as_view()(self.request, **kwargs)
		self.assertEqual(response.status_code, 400)


class ContentProcessingCommentTestCase(BaseTestCase):
	def setUp(self):
		super(ContentProcessingCommentTestCase, self).setUp()
		self.site.url = 'http://nice-site.com'
		self.site.require_akismet_approval = False
		self.site.require_user_approval = False
		self.site.comments_use_markdown = True
		self.site.save()

		self.comment_data = {
			'author_name': 'foo bar',
			'comment': 'foobar!',
			'author_website': '',
			'author_email': 'aloha@example.com',
			'post_slug': 'some-article'
		}

	def test_sanitization(self):
		self.comment_data['author_name'] = '<script>alert("xss");</script>'
		self.comment_data['comment'] = '<img src="foo" onerror="javascript:alert(\'xss\');">'
		self.comment_data['author_website'] = 'onclick="alert(\'xss\');',

		request = self.submit_comment_request(
			data=self.comment_data,
		)

		response = SubmitCommentView.as_view()(request, **self.kwargs)
		comments = Comment.objects.all()
		self.assertEqual(comments[0].author_name, '&lt;script&gt;alert(&quot;xss&quot;);&lt;/script&gt;')
		self.assertEqual(comments[0].comment, '<p>&lt;img src="foo" onerror="javascript:alert(\'xss\');"&gt;</p>\n')
		self.assertEqual(comments[0].author_website, '')

	def test_markdown(self):
		self.comment_data['comment'] = (
			'#header!\n'
			'I can has `code`\n\n'
			'> So quote wow\n')

		request = self.submit_comment_request(
			data=self.comment_data
		)
		response = SubmitCommentView.as_view()(request, **self.kwargs)
		comments = Comment.objects.all()
		self.assertEqual(comments[0].comment, '<div><h1>header!</h1>\n\n<p>I can has <code>code</code></p>\n\n<blockquote>\n  <p>So quote wow</p>\n</blockquote>\n</div>')

	def test_url_masking(self):
		self.comment_data['comment'] = (
			'local: [article](http://nice-site.com/costam)\n'
			'external: [spam](http://spam.com/spam?for=spammers)\n'
			'broken: [foo](bar)\n')

		request = self.submit_comment_request(
			data=self.comment_data
		)
		response = SubmitCommentView.as_view()(request, **self.kwargs)
		comments = Comment.objects.all()
		self.assertEqual(comments[0].comment, '<p>local: <a href="http://nice-site.com/costam">article</a>\nexternal: <a href="http://spam.com/spam?for=spammers" target="_blank" rel="nofollow">spam</a>\nbroken: <a href="bar" target="_blank" rel="nofollow">foo</a></p>\n')


class AkismetProcessingTestCase(BaseTestCase):
	def setUp(self):
		super(AkismetProcessingTestCase, self).setUp()
		self.site.require_akismet_approval = True
		self.site.require_user_approval = False
		self.site.akismet_key = 'qwerty'
		self.site.save()

		self.comment = mommy.make(Comment, post_slug='some-article', public=False, site=self.site)
		self.factory = RequestFactory()

	def test_akismet_approves_comment(self):
		with patch('comments.processing.Akismet') as mock_akismet:
			instance = mock_akismet.return_value
			instance.comment_check.return_value = True
			process_comment(self.comment)
			comment = Comment.objects.all()[0]
			self.assertTrue(comment.public, True)
			self.assertTrue(comment.akismet_approved, True)


class UserProcessingTestCase(BaseTestCase):
	def setUp(self):
		super(UserProcessingTestCase, self).setUp()
		self.user = mommy.make(User)
		self.site.url = 'http://nice-site.com'
		self.site.require_akismet_approval = False
		self.site.require_user_approval = True
		self.site.owner = self.user
		self.site.save()

	def test_user_approves_comment(self):
		with patch('comments.processing.send_mail') as mock_send_mail:
			mock_send_mail.return_value = 1
			org_comment = mommy.make(Comment,
				post_slug='some-article',
				public=False,
				site=self.site
			)
			kwargs = {
				'token': org_comment.user_approval_token,
				'decision': 'approve'
			}

			comment = Comment.objects.all()[0]
			self.assertEqual(comment.user_approved, False)
			self.assertEqual(comment.public, False)
			request = self.factory.put(
				reverse('api:moderate_comment', kwargs=kwargs)
			)
			response = ModerateCommentView.as_view()(request, **kwargs)
			comment = Comment.objects.all()[0]
			self.assertEqual(comment.user_approved, True)
			self.assertEqual(comment.public, True)


class PublicCommentsTestCase(BaseTestCase):
	def setUp(self):
		super(PublicCommentsTestCase, self).setUp()
		self.site.require_akismet_approval = False
		self.site.require_user_approval = False
		self.site.save()
		self.comment = mommy.make(Comment, post_slug='some-article', public=True, site=self.site)

	def test_can_obtain_public_comment_data(self):
		kwargs = {
			'token': self.site.public_token,
			'post_slug': 'some-article'
		}
		request = self.factory.get(reverse('api:public_comments', kwargs=kwargs))
		response = PublicCommentsView.as_view()(request, **kwargs)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 1)
		comment = response.data[0]
		self.assertEqual(
			comment.keys(),
			['id', 'author_name', 'author_avatar', 'author_website', 'comment', 'created_date', 'post_slug', 'reply_to']
		)
		self.assertEqual(comment['author_name'], self.comment.author_name)


class MigrateWordpressTestCase(BaseTestCase):
	def setUp(self):
		super(MigrateWordpressTestCase, self).setUp()
		self.comment_tpl = """<wp:comment>
					<wp:comment_id>{id}</wp:comment_id>
					<wp:comment_author><![CDATA[foobar]]></wp:comment_author>
					<wp:comment_author_email>foo@bar.co</wp:comment_author_email>
					<wp:comment_author_url>http://www.foobar.com</wp:comment_author_url>
					<wp:comment_author_IP>1.2.3.4</wp:comment_author_IP>
					<wp:comment_date_gmt>2012-01-02 03:04:05</wp:comment_date_gmt>
					<wp:comment_content><![CDATA[I ☃ <a href="http://foobar.com">foobar</a>!]]></wp:comment_content>
					<wp:comment_approved>1</wp:comment_approved>
					<wp:comment_parent>{reply_to}</wp:comment_parent>
					<wp:comment_type></wp:comment_type>
				</wp:comment>"""

		self.xml = """<?xml version="1.0" encoding="UTF-8" ?><channel xmlns:wp="http://wordpress.org/export/1.2/">
				<item>
				<wp:post_name>some-slug</wp:post_name>
					{comment}
				</item>
				</channel>"""

	def test_simple_comment_migration(self):
		xml = self.xml.format(comment=self.comment_tpl.format(id=10, reply_to=0))

		migrate_wordpress(self.site, StringIO(xml))

		comments = self.site.comments.all()
		self.assertEqual(len(comments), 1)
		self.assertEqual(comments[0].post_slug, 'some-slug')
		self.assertEqual(comments[0].author_name, 'foobar')
		self.assertEqual(comments[0].author_email, 'foo@bar.co')
		self.assertEqual(comments[0].author_website, 'http://www.foobar.com')
		self.assertEqual(comments[0].comment, '<p>I &#9731; <a href="http://foobar.com" target="_blank" rel="nofollow">foobar</a>!</p>')
		self.assertEqual(comments[0].created_date, datetime(2012, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
		self.assertEqual(comments[0].user_approved, True)
		self.assertEqual(comments[0].user_processed, True)
		self.assertEqual(comments[0].akismet_approved, True)
		self.assertEqual(comments[0].akismet_processed, True)
		self.assertEqual(comments[0].public, True)

	def test_comments_replies(self):
		comments = []
		random.seed(42)
		for i in range(50):
			comments.append(self.comment_tpl.format(id=i + 1, reply_to=i))

		random.shuffle(comments)
		xml = self.xml.format(comment=''.join(comments))
		migrate_wordpress(self.site, StringIO(xml))

		comments = self.site.comments.all()
		self.assertEqual(len(comments), 50)
