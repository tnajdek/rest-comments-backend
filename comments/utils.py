from urlparse import urlparse
from lxml import html


def get_client_ip(request):
	x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
	if x_forwarded_for:
		ip = x_forwarded_for.split(',')[0]
	else:
		ip = request.META.get('REMOTE_ADDR')
	return ip


def mask_links(html_text, site_url):
	document = html.fromstring(html_text)
	for el, attr, val, pos in html.iterlinks(document):
		if el.tag.lower() == "a":
			if(attr == 'href' and not is_internal_link(val, site_url)):
				el.attrib['target'] = '_blank'
				el.attrib['rel'] = 'nofollow'
	return html.tostring(document)


def is_internal_link(link, site_url):
	parsed = urlparse(link)
	site_url = urlparse(site_url)
	return parsed.netloc.lower() == site_url.netloc.lower()
