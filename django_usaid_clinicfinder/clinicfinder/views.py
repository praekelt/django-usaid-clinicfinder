from .models import (PointOfInterest, Location, LookupLocation,
                     LookupPointOfInterest)
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .serializers import (PointOfInterestSerializer, LocationSerializer,
                          LookupPointOfInterestSerializer,
                          LookupLocationSerializer)


class LocationViewSet(viewsets.ModelViewSet):

    """
    API endpoint that allows location models to be viewed or edited.
    """
    permission_classes = (IsAuthenticated,)
    queryset = Location.objects.all()
    serializer_class = LocationSerializer


class PointofInterestViewSet(viewsets.ModelViewSet):

    """
    API endpoint that allows PoI models to be viewed or edited.
    """
    permission_classes = (IsAuthenticated,)
    queryset = PointOfInterest.objects.all()
    serializer_class = PointOfInterestSerializer


class LookupLocationViewSet(viewsets.ModelViewSet):

    """
    API endpoint that allows location lookup models to be viewed or edited.
    """
    permission_classes = (IsAuthenticated,)
    queryset = LookupLocation.objects.all()
    serializer_class = LookupLocationSerializer


class LookupPointofInterestViewSet(viewsets.ModelViewSet):

    """
    API endpoint that allows PoI lookup models to be viewed or edited.
    """
    permission_classes = (IsAuthenticated,)
    queryset = LookupPointOfInterest.objects.all()
    serializer_class = LookupPointOfInterestSerializer
