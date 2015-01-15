#!/bin/sh

export DJANGO_SETTINGS_MODULE="django_usaid_clinicfinder.testsettings"
./manage.py test "$@"
