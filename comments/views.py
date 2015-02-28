from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ParseError

from .models import Comment, Site
from .serializers import PublicCommentSerializer, SubmitCommentSerializer


class PublicCommentsView(generics.ListAPIView):
	"""
	API endpoint that allows users to be viewed or edited.
	"""

	serializer_class = PublicCommentSerializer
	permission_classes = (AllowAny,)

	def get_queryset(self):
		token = self.kwargs['token']
		permalink = self.kwargs['permalink']
		return Comment.objects.filter(site__public_token=token, permalink=permalink, public=True)


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
		return super(SubmitCommentView, self).perform_create(serializer)

	def post(self, request, *args, **kwargs):
		site_token = kwargs.get('token')
		try:
			site = Site.objects.get(public_token=site_token)
		except Site.DoesNotExist:
			raise ParseError('Token {} is invalid'.format(site_token))

		self.site = site
		return super(SubmitCommentView, self).post(request, *args, **kwargs)