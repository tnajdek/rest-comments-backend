import uuid

from akismet import Akismet

from django.core.mail import send_mail
from django.template import loader, Context
from django.conf import settings



def spam_comment(comment):
	api = Akismet(comment.site.akismet_key, blog_url=comment.site.url, agent='RestComments/0.1')
	api.submit_spam(comment.comment,
		data={
			'user_ip': comment.client_ip,
			'user_agent': comment.client_user_agent,
			'referrer': 'unknown',
			'permalink': comment.permalink,
			'comment_type': 'comment',
			'comment_author': comment.name,
			'comment_author_email': comment.email,
			'comment_author_url': comment.website,
		}
	)


def process_comment(comment):
	if(comment.site.require_user_approval and not comment.user_processed):
		comment.user_approval_token = uuid.uuid4().hex
		template = loader.get_template('approve-comment-email.txt')
		context = Context({
			'username': comment.site.owner.username,
			'comment': comment
		})
		send_mail(
			'[{}] Moderate Comment: {}'.format(comment.site.url, comment.permalink),
			template.render(context),
			settings.FROM_EMAIL,
			comment.site.owner.email
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
				'permalink': comment.permalink,
				'comment_type': 'comment',
				'comment_author': comment.name,
				'comment_author_email': comment.email,
				'comment_author_url': comment.website,
			},
			DEBUG=True
		)
		comment.akismet_processed = True


def publish_comment_if_approved(comment):
	user_approved = comment.user_approved or not comment.site.require_user_approval
	akismet_approved = comment.akismet_approved or not comment.site.require_akismet_approval

	if(akismet_approved and user_approved):
		comment.public = True