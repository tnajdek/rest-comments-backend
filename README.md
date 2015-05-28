# Configure

Create file named `secrets.py` in folder `rest_comments_backend` with contents filling in the blanks:

	SECRET_KEY = ''

	ALLOWED_HOSTS = ()
	DATABASES = {
		'default': {
			'ENGINE': '',
			'NAME': '',
			'USER': '',
			'PASSWORD': '',
			'HOST': '',
			'PORT': '',
		}
	}

	FROM_EMAIL = ''
	EMAIL_HOST = ''
	EMAIL_PORT = 
	EMAIL_USE_TLS = 
	EMAIL_USE_SSL = 
	EMAIL_HOST_USER = ''
	EMAIL_HOST_PASSWORD = ''

	CORS_ORIGIN_WHITELIST = ()

	ADMINS = ()

	# deployment
	PRODUCTION_HOST = []
	PRODUCTION_DIR = ''
	PRODUCTION_SSL_PATH = ''
	PRODUCTION_PYTHON_PATH = ''
	PRODUCTION_VHOST_DIR = ''
	PRODUCTION_SSL_INTERMEDIARY = ''
	PRODUCTION_SSL_CRT = ''
	PRODUCTION_SSL_KEY = ''

# Deploy to the server

    fab bootstrap apache_restart

Add crontab for asynchroneus mail sending:

    * * * * * (source /srv/http/restcomments/env/bin/activate && APPLICATION_ENV="production" /srv/http/restcomments/app/manage.py send_mail >> /var/log/restcomments_mail.log 2>&1)
    0,20,40 * * * * (source /srv/http/restcomments/env/bin/activate && APPLICATION_ENV="production" /srv/http/restcomments/app/manage.py retry_deferred >> /var/log/restcomments_mail_deferred.log 2>&1)