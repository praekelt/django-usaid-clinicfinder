from .models import (Location, PointOfInterest,
                     LookupLocation, LookupPointOfInterest)
from rest_framework.serializers import HyperlinkedModelSerializer
from rest_framework_gis.serializers import GeoModelSerializer


class LocationSerializer(GeoModelSerializer):

    """ A class to serialize locations as GeoJSON compatible data """

    class Meta:
        model = Location
        geo_field = "point"

        # you can also explicitly declare which fields you want to include
        # as with a ModelSerializer.
        fields = ('id', 'point')


class PointOfInterestSerializer(HyperlinkedModelSerializer):
    location = LocationSerializer(many=False, read_only=True)

    class Meta:
        model = PointOfInterest
        fields = ('url', 'id', 'data', 'location', 'created_at', 'updated_at')


class LookupLocationSerializer(GeoModelSerializer):

    """ A class to serialize locations as GeoJSON compatible data """

    class Meta:
        model = LookupLocation
        geo_field = "point"

        # you can also explicitly declare which fields you want to include
        # as with a ModelSerializer.
        fields = ('id', 'point')


class LookupPointOfInterestSerializer(HyperlinkedModelSerializer):
    # location = LocationSerializer(many=False, read_only=True)

    class Meta:
        model = LookupPointOfInterest
        fields = ('url', 'search', 'response', 'location', 'created_at', 'updated_at')

