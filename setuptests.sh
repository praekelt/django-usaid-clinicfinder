#!/bin/bash
psql -c 'create database django_usaid_clinicfinder;' -U postgres
psql -c 'CREATE EXTENSION hstore;' -U postgres -d django_usaid_clinicfinder
psql -c 'CREATE EXTENSION postgis;' -U postgres -d django_usaid_clinicfinder
psql -c 'CREATE EXTENSION postgis_topology;' -U postgres -d django_usaid_clinicfinder

echo "DATABASES = {'default': {'ENGINE': 'django.contrib.gis.db.backends.postgis','NAME': 'django_usaid_clinicfinder','USER': 'postgres'}}" > django_usaid_clinicfinder/django_usaid_clinicfinder/local_settings.py
