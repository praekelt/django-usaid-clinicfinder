from django.contrib import admin as djangoadmin
from django.contrib.gis import admin as gisadmin

from .models import Location, PointOfInterest

djangoadmin.site.register(PointOfInterest)
gisadmin.site.register(Location)
