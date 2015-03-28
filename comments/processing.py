import uuid
import urlparse
import urllib
import hashlib
import re

from akismet import Akismet
from markdown2 import markdown

from django.core.mail import send_mail
from django.template import loader, Context
from django.conf import settings
from django.utils.html import urlize, escape
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

from utils import mask_links, bleach_clean


def get_gravatar(email):
	size = 96
	default = 'retro'
	gravatar_url = "//www.gravatar.com/avatar/" + hashlib.md5(email.lower()).hexdigest() + "?"
	gravatar_url += urllib.urlencode({'d': default, 's': str(size)})
	return gravatar_url


def spam_comment(comment):
	api = Akismet(comment.site.akismet_key, blog_url=comment.site.url, agent='RestComments/0.1')
	api.submit_spam(comment.comment,
		data={
			'user_ip': comment.client_ip,
			'user_agent': comment.client_user_agent,
			'referrer': 'unknown',
			'post_slug': comment.post_slug,
			'comment_type': 'comment',
			'comment_author': comment.author_name,
			'comment_author_email': comment.author_email,
			'comment_author_url': comment.author_website,
		}
	)


def process_comment(comment):
	comment.comment_original = comment.comment
	if(comment.site.require_user_approval and not comment.user_processed):
		comment.user_approval_token = uuid.uuid4().hex
		template = loader.get_template('approve-comment-email.txt')
		context = Context({
			'username': comment.site.owner.username,
			'comment': comment
		})
		send_mail(
			'[{}] Moderate Comment: {}'.format(comment.site.url, comment.post_slug),
			template.render(context),
			settings.FROM_EMAIL,
			(comment.site.owner.email, )
		)

	if(comment.site.require_akismet_approval and not comment.akismet_processed):
		if(not comment.site.akismet_key):
			raise Exception("Akismet key is not specified")

		api = Akismet(comment.site.akismet_key, blog_url=comment.site.url, agent='RestComments/0.1')

		comment.akismet_approved = api.comment_check(
			comment.comment,
			data={
				'user_ip': comment.client_ip,
				'user_agent': comment.client_user_agent,
				'referrer': 'unknown',
				'post_slug': comment.post_slug,
				'comment_type': 'comment',
				'comment_author': comment.author_name,
				'comment_author_email': comment.author_email,
				'comment_author_url': comment.author_website,
			},
			DEBUG=True
		)
		comment.akismet_processed = True


def publish_comment_if_approved(comment):
	user_approved = comment.user_approved or not comment.site.require_user_approval
	akismet_approved = comment.akismet_approved or not comment.site.require_akismet_approval

	if(akismet_approved and user_approved):
		comment.public = True


def process_comment_content(comment):
	text = comment.comment_original
	# escape all html
	text = escape(text)

	# markdown uses > for quotes so recover that after escaping
	if(comment.site.comments_use_markdown):
		text = re.sub(r'(^|\n)&gt;', '>', text)

	# urlize things that appear as urls in the text
	text = urlize(text)

	# process markdown
	if(comment.site.comments_use_markdown):
		text = markdown(text, extras=["fenced-code-blocks", "toc", "tables"])

	# sanitize markup
	text = bleach_clean(text)

	# make external links rel=nofollow and open in _blank
	text = mask_links(text, comment.site.url)

	comment.comment = text
	comment.author_name = escape(comment.author_name)
	comment.author_website = escape(comment.author_website)
	comment.author_avatar = get_gravatar(comment.author_email)

	val = URLValidator()
	try:
		val(comment.author_website)
	except ValidationError, e:
		comment.author_website = ''
