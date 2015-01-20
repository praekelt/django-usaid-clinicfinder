from django.db import models as djangomodels
from django.contrib.gis.db import models as gismodels
from django_hstore import hstore
from django.db.models.signals import post_save
from django.dispatch import receiver
from .tasks import lbs_lookup, location_finder


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
        LookupLocation, related_name='lookup_location',
        blank=True, null=True)


class LBSRequest(HStoreModel):

    """
    Inbound request for LBS lookup. Triggers LBS API call.
    """
    created_at = djangomodels.DateTimeField(auto_now_add=True)
    updated_at = djangomodels.DateTimeField(auto_now=True)
    search = hstore.DictionaryField()
    response = hstore.DictionaryField(blank=True, null=True)
    pointofinterest = djangomodels.ForeignKey(
        LookupPointOfInterest, related_name='pointofinterest')


# Make sure new LBS Requests tasks are run via Celery
@receiver(post_save, sender=LBSRequest)
def fire_lbs_task_if_new(sender, instance, created, **kwargs):
    if created:
        lbs_lookup.delay(instance.id)


@receiver(post_save, sender=LookupPointOfInterest)
def fire_location_finder_task_if_complete(sender, instance, created, **kwargs):
    # Lookup locaction in place and results not in place already
    if instance.location != None and "results" not in instance.response:
        # find match and prepare response
        location_finder.delay(instance.id)
