from django_usaid_clinicfinder.settings import *  # flake8: noqa

DATABASES = {
    'default': dj_database_url.config(
        default='postgis://postgres:@localhost/django_usaid_clinicfinder'),
}

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'TESTSEKRET'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
CELERY_ALWAYS_EAGER = True
BROKER_BACKEND = 'memory'
CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'

LBS_API_WSDL = "https://lbs.gsm.co.za/lbsservice.asmx?WSDL"
LBS_API_USERNAME = ""
LBS_API_PASSWORD = ""

LOCATION_SEARCH_RADIUS = 20  # KM
LOCATION_MAX_RESPONSES = 2
