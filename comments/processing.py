from akismet import Akismet


def akismet_check_comment(comment):
	if(not comment.site.require_akismet_approval):
		return True

	if(not comment.site.akismet_key):
		raise Exception("Akismet key is not specified")

	api = Akismet(comment.site.akismet_key, blog_url=comment.site.url, agent='RestComments/0.1')

	return api.comment_check(
		comment.comment,
		{
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
	if(comment.site.require_akismet_approval):
		comment.akismet_approved = akismet_check_comment(comment)

	user_approved = comment.user_approved or not comment.site.require_user_approval
	akismet_approved = comment.akismet_approved or not comment.site.require_akismet_approval

	if(akismet_approved and user_approved):
		comment.public = True

	comment.save()