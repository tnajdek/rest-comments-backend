# -*- coding: utf-8 -*-
import logging
import os
from fabric.api import env, task
from fabric.operations import local
from fabric.contrib.project import rsync_project
from fabric.api import *
from fabric import utils
from fabric.context_managers import lcd
from fabric.context_managers import shell_env

from rest_comments_backend.secrets import PRODUCTION_HOST, PRODUCTION_DIR, PRODUCTION_SSL_PATH, PRODUCTION_PYTHON_PATH, PRODUCTION_VHOST_DIR, PRODUCTION_SSL_INTERMEDIARY, PRODUCTION_SSL_CRT, PRODUCTION_SSL_KEY


BASEDIR = os.path.dirname(__file__)
LOGGER = logging.getLogger(__name__)

RSYNC_EXCLUDE = (
	'.DS_Store',
	'.git',
	'.gitignore',
	'*.pyc',
	'fabfile.py',
	'db.sqlite3'
)

requirements_file = os.path.abspath(os.path.join(os.path.abspath(BASEDIR), 'requirements', 'dev-requirements.txt'))


def get_venv():
	""" Get the current virtual environment name
		Bail out if we're not in one
	"""
	try:
		return os.environ['VIRTUAL_ENV']
	except KeyError:
		print('Not in a virtualenv')
		exit(1)


def get_pip():
	""" Get an absolute path to the pip executable
		for the current virtual environment
	"""
	return join(get_venv(), 'bin', 'pip')


def check_for(what, unrecoverable_msg, installation_cmd=None):
	def failure():
		print(unrecoverable_msg)
		exit()

	try:
		test_result = local("which %s" % what, capture=True)
		return test_result
	except:
		if(installation_cmd):
			print("Unable to find %s, will attempt installation (you might be asked for sudo password below)")
			local(installation_cmd)
		else:
			failure()
		try:
			test_result = local(cmd, capture=True)
			return test_result
		except:
			failure()

@task
def rsync():
	require('root', provided_by=('production',))
	# if env.environment == 'production':
	# 	if not console.confirm('Are you sure you want to deploy production?',
	# 						   default=False):
	# 		utils.abort('Production deployment aborted.')
	# defaults rsync options:
	# -pthrvz
	# -p preserve permissions
	# -t preserve times
	# -h output numbers in a human-readable format
	# -r recurse into directories
	# -v increase verbosity
	# -z compress file data during the transfer
	extra_opts = '-l --omit-dir-times'
	rsync_project(
		env.code_root,
		'.',
		exclude=RSYNC_EXCLUDE,
		delete=True,
		extra_opts=extra_opts,
	)


@task
def install_deps():
	""" Install python dependencies from requirements.txt file
	"""
	with lcd(BACKENDDIR):
		cmd = '%(pip)s install -r %(requirements_file)s' % {
			'pip': get_pip(),
			'requirements_file': requirements_file
		}
		local(cmd)


@task
def build():
	with lcd(BACKENDDIR):
		with shell_env(APPLICATION_ENV='build'):
			local("./manage.py collectstatic --noinput")


@task
def develop():
	with lcd(FRONTENDDIR):
		cmd = '%(grunt)s develop' % {'grunt': get_grunt()}
		local(cmd)


@task
def production():
	""" use production environment on remote host"""
	env.user = 'root'
	env.environment = 'production'
	env.hosts = PRODUCTION_HOST
	env.root = PRODUCTION_DIR
	env.ssl_path = PRODUCTION_SSL_PATH
	env.python = PRODUCTION_PYTHON_PATH
	env.apache_config_dir = PRODUCTION_VHOST_DIR
	env.code_root = env.root + '/app'
	env.virtualenv_root = env.root + '/env'
	env.activate = 'source %s' % "/".join([env.virtualenv_root, 'bin', 'activate'])


@task
def bootstrap():
	""" initialize remote host environment (virtualenv, deploy, update) """
	require('root', provided_by=('production',))
	run('mkdir -p %(root)s' % env)
	create_virtualenv()
	rsync()
	update_requirements()
	migrate()
	apache_config()
	touch()


def create_virtualenv():
	""" setup virtualenv on remote host """
	require('virtualenv_root', provided_by=('production',))
	args = '--clear --distribute -p %s' % env.python
	run('virtualenv %s %s' % (args, env.virtualenv_root))


def migrate():
	""" migrate schema on the far end """
	require('root', provided_by=('production',))

	with prefix(env.activate), shell_env(APPLICATION_ENV=env.environment):
		run(env.code_root + '/manage.py syncdb --noinput')
		run(env.code_root + '/manage.py migrate')


@task
def apache_config():
	""" install apache config file """
	require('root', provided_by=('production',))

	rsync_project(
		env.apache_config_dir,
		"configs/apache/%s.conf" % env.environment
	)

	if(hasattr(env, 'ssl_path')):
		# intermediary
		if(PRODUCTION_SSL_INTERMEDIARY):
			rsync_project(
				env.ssl_path + '/certs',
				os.path.join('configs', 'certs', PRODUCTION_SSL_INTERMEDIARY)
			)

		rsync_project(
			env.ssl_path + '/certs',
			os.path.join('configs', 'certs', PRODUCTION_SSL_CRT)
		)

		rsync_project(
			env.ssl_path + '/private',
			os.path.join('configs', 'certs', PRODUCTION_SSL_KEY)
		)


@task
def deploy():
	""" rsync code to remote host """
	rsync()
	migrate()
	apache_config()
	touch()


@task
def update_requirements():
	""" update external dependencies on remote host """
	require('code_root', provided_by=('production',))
	requirements = "/".join([env.code_root, 'requirements', 'requirements.txt'])
	cmd = ['pip install']
	cmd += ['--requirement %s' % requirements]
	with prefix(env.activate):
		run(' '.join(cmd))


def touch():
	""" touch wsgi file to trigger reload """
	require('code_root', provided_by=('production',))
	run('touch django.wsgi')


@task
def configtest():
	""" test Apache configuration """
	require('root', provided_by=('production',))
	run('apachectl configtest')


@task
def apache_restart():
	""" restart Apache on remote host """
	require('root', provided_by=('production',))
	run('sudo systemctl restart httpd')
