from .models import PointOfInterest, Location
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .serializers import (PointOfInterestSerializer, LocationSerializer)


class LocationViewSet(viewsets.ModelViewSet):

    """
    API endpoint that allows location models to be viewed or edited.
    """
    permission_classes = (IsAuthenticated,)
    queryset = Location.objects.all()
    serializer_class = LocationSerializer

class PointofInterestViewSet(viewsets.ModelViewSet):

    """
    API endpoint that allows location models to be viewed or edited.
    """
    permission_classes = (IsAuthenticated,)
    queryset = PointOfInterest.objects.all()
    serializer_class = PointOfInterestSerializer



