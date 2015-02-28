from django.conf.urls import patterns, url

from views import PublicCommentsView, SubmitCommentView

urlpatterns = patterns(
	'',
	url(r'comments/(?P<token>.+)/(?P<permalink>.+)/$', PublicCommentsView.as_view(), name='public_comments'),
	url(r'comments/(?P<token>.+)/$', SubmitCommentView.as_view(), name="submit_comment"),
)

from django.contrib import admin
from .models import Comment, Site

admin.site.register(Site)
admin.site.register(Comment)
