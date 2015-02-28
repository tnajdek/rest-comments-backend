from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'rest_comments_backend.views.home', name='home'),
    url(r'^api/', include('comments.urls', namespace="api")),
    url(r'^admin/', include(admin.site.urls)),
)
