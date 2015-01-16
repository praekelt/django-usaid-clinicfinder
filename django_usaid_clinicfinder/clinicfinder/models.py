from django.db import models as djangomodels
from django.contrib.gis.db import models as gismodels
from django_hstore import hstore


class HStoreModel(djangomodels.Model):
    objects = hstore.HStoreManager()

    class Meta:
        abstract = True


class Location(gismodels.Model):
    point = gismodels.PointField()
    created_at = djangomodels.DateTimeField(auto_now_add=True)
    updated_at = djangomodels.DateTimeField(auto_now=True)

    # GeoDjango-specific overriding the default manager with a
    # GeoManager instance.
    objects = gismodels.GeoManager()

    def __unicode__(self):
        return "%s" % (self.point)


class PointOfInterest(HStoreModel):

    """
    Extendable point of interest model
    """
    created_at = djangomodels.DateTimeField(auto_now_add=True)
    updated_at = djangomodels.DateTimeField(auto_now=True)
    # can pass attributes like null, blank, etc.
    data = hstore.DictionaryField()
    location = djangomodels.ForeignKey(Location, related_name='location')


class LookupLocation(gismodels.Model):

    """
    Inbound lookups are stored here and trigger
    """
    point = gismodels.PointField()

    created_at = djangomodels.DateTimeField(auto_now_add=True)
    updated_at = djangomodels.DateTimeField(auto_now=True)

    # GeoDjango-specific overriding the default manager with a
    # GeoManager instance.
    objects = gismodels.GeoManager()

    def __unicode__(self):
        return "%s" % (self.point)


class LookupPointOfInterest(HStoreModel):

    """
    Extendable point of interest request model
    """
    created_at = djangomodels.DateTimeField(auto_now_add=True)
    updated_at = djangomodels.DateTimeField(auto_now=True)
    # can pass attributes like null, blank, etc.
    search = hstore.DictionaryField()
    response = hstore.DictionaryField()
    location = djangomodels.ForeignKey(
        LookupLocation, related_name='lookup_location')
