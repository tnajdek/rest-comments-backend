from lxml import etree
from datetime import datetime

from django.utils import timezone

from models import Comment
from utils import mask_links, bleach_clean


# probably not very efficient recursive approach to sorting comments ahead of replies to that comment 
def find_replies(parent_comment_data, sorted_comments_data, unsorted_comments_data):
	for i in xrange(len(unsorted_comments_data) - 1, -1, -1):
		if(i >= len(unsorted_comments_data)):
			return

		comment_data = unsorted_comments_data[i]

		if((parent_comment_data and comment_data.get('reply_to_wp_id') == parent_comment_data['comment_id']) or (not parent_comment_data and not comment_data['reply_to_wp_id'])):
			sorted_comments_data.append(comment_data)
			del unsorted_comments_data[i]
			find_replies(comment_data, sorted_comments_data, unsorted_comments_data)


def process_wp_comment(comment):
	text = comment.comment_original
	text = u"<p>{}</p>".format(text)
	text = bleach_clean(text)
	text = mask_links(text, comment.site.url)
	comment.comment = text

	return comment


def migrate_wordpress(site, xml_src):
	context = etree.iterparse(xml_src, events=('end',), tag='item')
	unsorted_comments_data = []
	sorted_comments_data = []

	for event, elem in context:
		slug = elem.find('{%s}post_name' % elem.nsmap['wp']).text
		comments = elem.findall('{%s}comment' % elem.nsmap['wp'])

		for comment in comments:
			comment_data = {}
			comment_data['comment_id'] = int(comment.find('{%s}comment_id' % comment.nsmap['wp']).text)
			comment_data['author_name'] = comment.find('{%s}comment_author' % comment.nsmap['wp']).text
			comment_data['author_email'] = comment.find('{%s}comment_author_email' % comment.nsmap['wp']).text
			comment_data['author_website'] = comment.find('{%s}comment_author_url' % comment.nsmap['wp']).text
			comment_data['client_ip'] = comment.find('{%s}comment_author_IP' % comment.nsmap['wp']).text
			comment_data['created_date'] = comment.find('{%s}comment_date_gmt' % comment.nsmap['wp']).text
			comment_data['comment'] = comment.find('{%s}comment_content' % comment.nsmap['wp']).text
			comment_data['public'] = comment.find('{%s}comment_approved' % comment.nsmap['wp']).text == '1'
			comment_data['reply_to_wp_id'] = int(comment.find('{%s}comment_parent' % comment.nsmap['wp']).text)
			comment_data['comment_type'] = comment.find('{%s}comment_type' % comment.nsmap['wp']).text
			comment_data['post_slug'] = slug
			if(comment_data['comment_type'] != 'pingback'):
				unsorted_comments_data.append(comment_data)

		elem.clear()

		while elem.getprevious() is not None:
			del elem.getparent()[0]

	for i in xrange(len(unsorted_comments_data) - 1, -1, -1):
		find_replies(None, sorted_comments_data, unsorted_comments_data)

	lookup = {}

	for comment_data in sorted_comments_data:
		comment = Comment()
		comment.site = site
		comment.user_processed = True
		comment.user_approved = comment_data['public']
		comment.akismet_approved = True
		comment.akismet_processed = True
		comment.comment = comment.comment_original = comment_data['comment']
		for prop in ['author_name', 'author_email', 'author_website', 'client_ip', 'public', 'post_slug']:
			setattr(comment, prop, comment_data.get(prop))
		if(comment_data['reply_to_wp_id']):
			comment.reply_to = lookup[comment_data['reply_to_wp_id']]
		comment.save()

		comment.created_date = datetime.strptime(comment_data['created_date'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
		comment = process_wp_comment(comment)
		comment.save(prevent_content_processing=True)

		lookup[comment_data['comment_id']] = comment
