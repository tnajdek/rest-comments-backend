from django.db import models
from django.contrib.auth.models import User

from .processing import process_comment, publish_comment_if_approved

class BaseClass(models.Model):
	created_date = models.DateTimeField(auto_now_add=True)
	updated_date = models.DateTimeField(auto_now=True)

	class Meta:
		abstract = True


class Site(BaseClass):
	public_token = models.CharField(max_length=32, unique=True)
	url = models.CharField(max_length=200)
	akismet_key = models.CharField(max_length=200, blank=True, null=True)
	require_akismet_approval = models.BooleanField(default=True)
	require_user_approval = models.BooleanField(default=True)
	owner = models.ForeignKey(User)


class Comment(BaseClass):
	name = models.CharField(max_length=200)
	comment = models.TextField()
	permalink = models.CharField(max_length=200)
	website = models.CharField(max_length=200, blank=True, null=True)
	notify_replies = models.BooleanField(default=False)
	reply_to = models.ForeignKey('self', blank=True, null=True, related_name="replies")
	email = models.CharField(max_length=200)
	akismet_processed = models.BooleanField(default=False)
	akismet_approved = models.BooleanField(default=False)
	user_processed = models.BooleanField(default=False)
	user_approved = models.BooleanField(default=False)
	user_approval_token = models.CharField(max_length=32, unique=True, blank=True, null=True, default=None)
	public = models.BooleanField(default=False)
	site = models.ForeignKey(Site, related_name="comments")
	client_ip = models.CharField(max_length=46)
	client_user_agent = models.CharField(max_length=200)

	def save(self, *args, **kwargs):
		if(not self.pk):
			process_comment(self)
		publish_comment_if_approved(self)
		super(Comment, self).save(*args, **kwargs)
