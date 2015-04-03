from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ParseError

from .models import Comment, Site
from .serializers import PublicCommentSerializer, SubmitCommentSerializer, ModerateCommentSerializer
from .processing import spam_comment
from .utils import get_client_ip


class PublicCommentsView(generics.ListAPIView):
	"""
	API endpoint that allows users to be viewed or edited.
	"""

	serializer_class = PublicCommentSerializer
	permission_classes = (AllowAny,)

	def get_queryset(self):
		token = self.kwargs['token']
		post_slug = self.kwargs['post_slug']
		return Comment.objects.filter(site__public_token=token, post_slug=post_slug, public=True)


class SubmitCommentView(generics.CreateAPIView):
	"""
	API endpoint that allows user to post new comments
	that will be processed by the backend before potentially
	becoming public
	"""

	serializer_class = SubmitCommentSerializer
	permission_classes = (AllowAny, )

	def perform_create(self, serializer):
		serializer.validated_data['site'] = self.site
		serializer.validated_data['client_ip'] = self.client_ip
		serializer.validated_data['client_user_agent'] = self.client_user_agent
		return super(SubmitCommentView, self).perform_create(serializer)

	def post(self, request, *args, **kwargs):
		site_token = kwargs.get('token')
		try:
			site = Site.objects.get(public_token=site_token)
		except Site.DoesNotExist:
			raise ParseError('Token {} is invalid'.format(site_token))

		self.site = site
		self.client_ip = get_client_ip(request)
		self.client_user_agent = request.META.get('HTTP_USER_AGENT')
		return super(SubmitCommentView, self).post(request, *args, **kwargs)


class ModerateCommentView(generics.UpdateAPIView):
	"""
	API endpoint to allow one-off comment moderation using pre-generated token
	"""

	serializer_class = ModerateCommentSerializer
	permission_classes = (AllowAny,)

	def get_object(self):
		return Comment.objects.get(user_approval_token=self.approval_token, user_processed=False)

	def perform_update(self, serializer):
		serializer.validated_data['user_approved'] = self.approved
		serializer.validated_data['user_processed'] = True
		serializer.validated_data['user_approval_token'] = None

		if(self.markspam):
			spam_comment(self)
		return super(ModerateCommentView, self).perform_update(serializer)

	def get(self, request, *args, **kwargs):
		self.approval_token = kwargs.get('token')
		self.approved = kwargs.get('decision') == 'approve'
		self.markspam = kwargs.get('decision') == 'spam'

		try:
			comment = Comment.objects.get(user_approval_token=self.approval_token, user_processed=False)
		except Site.DoesNotExist:
			raise ParseError('Token {} is invalid or expired'.format(self.approval_token))

		return super(ModerateCommentView, self).put(request, *args, **kwargs)
