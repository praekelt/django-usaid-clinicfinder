from django.conf.urls import patterns, include, url
from django.contrib import admin


urlpatterns = patterns('',
                       url(r'^grappelli/', include('grappelli.urls')),
                       url(r'^admin/',  include(admin.site.urls)),
                       url(r'^clinicfinder/',
                           include('clinicfinder.urls')),
                       )