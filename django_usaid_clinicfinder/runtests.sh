#!/bin/sh
createuser --createdb -R -S postgis_test
psql -c 'ALTER ROLE postgis_test SUPERUSER;'
export DJANGO_SETTINGS_MODULE="django_usaid_clinicfinder.testsettings"
./manage.py test "$@"
dropuser postgis_test