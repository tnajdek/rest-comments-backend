from mock import patch
from model_mommy import mommy

from django.test import TestCase, RequestFactory
from django.core.urlresolvers import reverse

from rest_framework.exceptions import ParseError

from .models import Site, Comment
from .views import SubmitCommentView, PublicCommentsView
from .processing import akismet_check_comment, process_comment


class SubmitCommentsTestCase(TestCase):
	def setUp(self):
		self.site = mommy.make(Site)
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


class AkismetProcessingTestCase(TestCase):
	def setUp(self):
		self.site = mommy.make(Site, require_akismet_approval=True, require_user_approval=False, akismet_key='qwerty')
		self.comment = mommy.make(Comment, permalink='some-article', public=False, site=self.site)
		self.factory = RequestFactory()

	def test_akismet_approves_comment(self):
		with patch('comments.processing.Akismet') as mock_akismet:
			instance = mock_akismet.return_value
			instance.comment_check.return_value = True
			self.assertTrue(akismet_check_comment(self.comment))

	def test_processing_publish_comment(self):
		with patch('comments.processing.Akismet') as mock_akismet:
			instance = mock_akismet.return_value
			instance.comment_check.return_value = True
			process_comment(self.comment)
			comment = Comment.objects.all()[0]
			self.assertTrue(comment.public, True)
			self.assertTrue(comment.akismet_approved, True)



class PublicCommentsTestCase(TestCase):
	def setUp(self):
		self.site = mommy.make(Site)
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
			['name', 'comment', 'website', 'created_date', 'permalink', 'reply_to']
		)
		self.assertEqual(comment['name'], self.comment.name)
