import os.path

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DEPLOY_PATH = os.path.dirname(__file__) # This is the base dir for everything

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = 'database.sqlite3'
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

TIME_ZONE = 'America/Chicago'

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

USE_I18N = True

# Absolute path to the directory that holds media.
MEDIA_ROOT = os.path.join(DEPLOY_PATH, 'media')
MEDIA_URL = 'http://localhost:8000/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
ADMIN_MEDIA_PREFIX = '/media/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
)

ROOT_URLCONF = 'archlinux.urls'

TEMPLATE_DIRS = (
    os.path.join(DEPLOY_PATH, 'templates'),
)

FIXTURE_DIRS = (
    os.path.join(DEPLOY_PATH, 'fixtures'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.sites',
    'archlinux.aur',
    'registration',
    'aurprofile',
    'tagging',
)

# Third party settings

# django-registration
ACCOUNT_ACTIVATION_DAYS = 1

# django-tagging
FORCE_LOWERCASE_TAGS = True

# Import local settings if they exist
try:
    from settings_local import *
except ImportError:
    pass
