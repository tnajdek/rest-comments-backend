from mock import patch
from model_mommy import mommy

from django.test import TestCase, RequestFactory
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from rest_framework.exceptions import ParseError

from .models import Site, Comment
from .views import SubmitCommentView, PublicCommentsView, ModerateCommentView
from .processing import process_comment


class SubmitCommentsTestCase(TestCase):
	def setUp(self):
		self.site = mommy.make(Site,
			require_akismet_approval=False,
			require_user_approval=False,
			)
		self.factory = RequestFactory()
		self.comment_data = {
			'name': 'test comment',
			'comment': 'text comment',
			'website': 'www.example.com',
			'email': 'aloha@example.com',
			'permalink': 'some-article'
		}

	def test_can_submit_comment(self):
		kwargs = {
			'token': self.site.public_token,
		}
		request = self.factory.post(
			reverse('api:submit_comment', kwargs=kwargs),
			data=self.comment_data
		)
		response = SubmitCommentView.as_view()(request, **kwargs)
		self.assertEqual(response.status_code, 201)
		comments = Comment.objects.all()
		self.assertEqual(len(comments), 1)
		self.assertEqual(comments[0].name, 'test comment')
		self.assertEqual(comments[0].client_ip, '127.0.0.1')

	def test_wrong_tokens_are_rejected(self):
		kwargs = {
			'token': 'jabberish',
		}
		request = self.factory.post(
			reverse('api:submit_comment', kwargs=kwargs),
			data=self.comment_data
		)
		response = SubmitCommentView.as_view()(request, **kwargs)
		self.assertEqual(response.status_code, 400)


class ContentProcessingCommentTestCase(TestCase):
	def setUp(self):
		self.site = mommy.make(Site,
			require_akismet_approval=False,
			require_user_approval=False,
			comments_use_markdown=True
		)
		self.factory = RequestFactory()

	def test_sanitization(self):
		self.comment_data = {
			'name': '<script>alert("xss");</script>',
			'comment': '<img src="foo" onerror="javascript:alert(\'xss\');">',
			'website': '" onclick="alert(\'xss\');',
			'email': 'aloha@example.com',
			'permalink': 'some-article'
		}

		kwargs = {
			'token': self.site.public_token,
		}
		request = self.factory.post(
			reverse('api:submit_comment', kwargs=kwargs),
			data=self.comment_data
		)
		response = SubmitCommentView.as_view()(request, **kwargs)
		comments = Comment.objects.all()
		self.assertEqual(comments[0].name, '&lt;script&gt;alert(&quot;xss&quot;);&lt;/script&gt;')
		self.assertEqual(comments[0].comment, '<p>&lt;img src="foo" onerror="javascript:alert(\'xss\');"&gt;</p>\n')
		self.assertEqual(comments[0].website, '')

	def test_markdown(self):
		self.comment_data = {
			'name': 'foo bar',
			'comment': 'some [url](http://google.com)',
			'website': '',
			'email': 'aloha@example.com',
			'permalink': 'some-article'
		}
		kwargs = {
			'token': self.site.public_token,
		}
		request = self.factory.post(
			reverse('api:submit_comment', kwargs=kwargs),
			data=self.comment_data
		)
		response = SubmitCommentView.as_view()(request, **kwargs)
		comments = Comment.objects.all()
		self.assertEqual(comments[0].comment, '<p>some <a href="http://google.com">url</a></p>\n')


class AkismetProcessingTestCase(TestCase):
	def setUp(self):
		self.site = mommy.make(Site, require_akismet_approval=True, require_user_approval=False, akismet_key='qwerty')
		self.comment = mommy.make(Comment, permalink='some-article', public=False, site=self.site)
		self.factory = RequestFactory()

	def test_akismet_approves_comment(self):
		with patch('comments.processing.Akismet') as mock_akismet:
			instance = mock_akismet.return_value
			instance.comment_check.return_value = True
			process_comment(self.comment)
			comment = Comment.objects.all()[0]
			self.assertTrue(comment.public, True)
			self.assertTrue(comment.akismet_approved, True)


class UserProcessingTestCase(TestCase):
	def setUp(self):
		self.user = mommy.make(User)
		self.site = mommy.make(Site, require_akismet_approval=False, require_user_approval=True, owner=self.user)
		self.factory = RequestFactory()

	def test_user_approves_comment(self):
		with patch('comments.processing.send_mail') as mock_send_mail:
			mock_send_mail.return_value = 1
			org_comment = mommy.make(Comment,
				permalink='some-article',
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


class PublicCommentsTestCase(TestCase):
	def setUp(self):
		self.site = mommy.make(Site, require_akismet_approval=False, require_user_approval=False)
		self.comment = mommy.make(Comment, permalink='some-article', public=True, site=self.site)
		self.factory = RequestFactory()

	def test_can_obtain_public_comment_data(self):
		kwargs = {
			'token': self.site.public_token,
			'permalink': 'some-article'
		}
		request = self.factory.get(reverse('api:public_comments', kwargs=kwargs))
		response = PublicCommentsView.as_view()(request, **kwargs)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 1)
		comment = response.data[0]
		self.assertEqual(
			comment.keys(),
			['id', 'name', 'comment', 'website', 'created_date', 'permalink', 'reply_to']
		)
		self.assertEqual(comment['name'], self.comment.name)
