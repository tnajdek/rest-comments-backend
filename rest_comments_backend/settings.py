"""
Django settings for rest_comments_backend project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
from ..secrets import SECRET_KEY, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, CORS_ORIGIN_WHITELIST, ALLOWED_HOSTS, DATABASES
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Application definition

INSTALLED_APPS = (
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'rest_framework',
	'corsheaders',
	'comments'

)

MIDDLEWARE_CLASSES = (
	'django.contrib.sessions.middleware.SessionMiddleware',
	'corsheaders.middleware.CorsMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'rest_comments_backend.urls'

WSGI_APPLICATION = 'rest_comments_backend.wsgi.application'


if(environment == 'production'):
	DEBUG = False
	PREPEND_WWW = False
else:
	DEBUG = True
	TEMPLATE_DEBUG = True
	INTERNAL_IPS = ["127.0.0.1", ]
	DATABASES = {
		'default': {
			'ENGINE': 'django.db.backends.sqlite3',
			'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
		}
	}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'

REST_FRAMEWORK = {
	'DEFAULT_PERMISSION_CLASSES': [
		'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
	]
}

if(DEBUG):
	FROM_EMAIL = 'no-reply@localhost.com'
	EMAIL_HOST = 'localhost'
	EMAIL_PORT = '1025'
	EMAIL_USE_TLS = False
	EMAIL_USE_SSL = False
	EMAIL_HOST_USER = None
	EMAIL_HOST_PASSWORD = None

CORS_ORIGIN_ALLOW_ALL = DEBUG
