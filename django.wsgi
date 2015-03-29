import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if BASE_DIR not in sys.path:
	sys.path.append(BASE_DIR)

os.environ['DJANGO_SETTINGS_MODULE'] = 'rest_comments_backend.settings'

import django.core.handlers.wsgi
_application = django.core.handlers.wsgi.WSGIHandler()

def application(environ, start_response):
	os.environ['APPLICATION_ENV'] = environ['APPLICATION_ENV']
	return _application(environ, start_response)