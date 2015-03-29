import os
import sys
from django.core.wsgi import get_wsgi_application

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if BASE_DIR not in sys.path:
	sys.path.append(BASE_DIR)

os.environ['DJANGO_SETTINGS_MODULE'] = 'rest_comments_backend.settings'


def application(environ, start_response):
	os.environ['APPLICATION_ENV'] = environ.get('APPLICATION_ENV')
	_application = get_wsgi_application()
	return _application(environ, start_response)
