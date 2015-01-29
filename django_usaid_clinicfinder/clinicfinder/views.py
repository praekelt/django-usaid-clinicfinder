from .models import (PointOfInterest, Location, LookupLocation,
                     LookupPointOfInterest, LBSRequest)
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .serializers import (PointOfInterestSerializer, LocationSerializer,
                          LookupPointOfInterestSerializer,
                          LookupLocationSerializer, LBSRequestSerializer)
from .forms import LocationsCSVUploader
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib import messages
from django.core.context_processors import csrf

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


class LBSRequestViewSet(viewsets.ModelViewSet):

    """
    API endpoint that allows LBS Request models to be viewed or edited.
    """
    permission_classes = (IsAuthenticated,)
    queryset = LBSRequest.objects.all()
    serializer_class = LBSRequestSerializer


@staff_member_required
def locations_uploader(request, page_name):
    if request.method == "POST":
        form = LocationsCSVUploader(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request,
                             "CSV has been uploaded for processing",
                             extra_tags="success")
            context = {"form": form}
        else:
            for errors_key, error_value in form.errors.iteritems():
                messages.error(request,
                               "%s: %s" % (errors_key, error_value),
                               extra_tags="danger")
            context = {"form": form}
        context.update(csrf(request))

        return render_to_response("custom_admin/upload_locations.html", context,
                                  context_instance=RequestContext(request))
    else:
        form = LocationsCSVUploader()
        context = {"form": form}
        context.update(csrf(request))
        return render_to_response("custom_admin/upload_locations.html", context,
                                  context_instance=RequestContext(request))

