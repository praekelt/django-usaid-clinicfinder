#!/bin/sh
export DATABASE_URL='postgres://postgres:@/test_django_usaid_clinicfinder'
export DJANGO_SETTINGS_MODULE="django_usaid_clinicfinder.testsettings"
./manage.py test "$@"