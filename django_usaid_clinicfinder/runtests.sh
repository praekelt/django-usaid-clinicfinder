#!/bin/sh

export DJANGO_SETTINGS_MODULE="django_usaid_clinicfinder.testsettings"
cd django_usaid_clinicfinder
./manage.py test "$@"
