from django.conf.urls import patterns, include, url
from django.contrib import admin


urlpatterns = patterns('',
                       url(r'^grappelli/', include('grappelli.urls')),
                       url(r'^admin/',  include(admin.site.urls)),
                       url(r'^clinicfinder/',
                           include('clinicfinder.urls')),
                       url(r'^admin/clinicfinder/upload/',
                           'clinicfinder.views.locations_uploader',
                           {'page_name': 'locations_uploader'},
                           name="locations_uploader"),
                       )
