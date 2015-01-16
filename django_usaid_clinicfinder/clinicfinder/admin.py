from django.contrib import admin as djangoadmin
from django.contrib.gis import admin as gisadmin

from .models import (Location, PointOfInterest,
                     LookupLocation, LookupPointOfInterest)

djangoadmin.site.register(PointOfInterest)
djangoadmin.site.register(LookupPointOfInterest)
gisadmin.site.register(Location)
gisadmin.site.register(LookupLocation)
