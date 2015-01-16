from __future__ import absolute_import

from celery.task import Task
from celery.utils.log import get_task_logger
from celery.exceptions import SoftTimeLimitExceeded
from suds.client import Client
from django.contrib.gis.geos import Point

from django.conf import settings

from clinicfinder.models import (LBSRequest, LookupPointOfInterest,
                                LookupLocation)

logger = get_task_logger(__name__)


class LBS_Lookup(Task):

    """
    Task to request location from LBS API
    """
    name = "clinicfinder.tasks.lbs_lookup"

    class FailedEventRequest(Exception):

        """
        The attempted task failed because of a non-200 HTTP return
        code.
        """

    def lbs_api_client(self):
        return Client(settings.LBS_API_WSDL)

    def run(self, lbsrequest_id, **kwargs):
        """
        Gets user details, adds to whitelist and gets current location
        """
        l = self.get_logger(**kwargs)

        l.info("Processing new LBS lookup")
        response = "No response"
        try:
            lbsrequest = LBSRequest.objects.get(pk=lbsrequest_id)
            client = self.lbs_api_client()
            whitelist = client.service.AddAllowedMsisdn(
                username=settings.LBS_API_USERNAME, 
                password=settings.LBS_API_PASSWORD, 
                msisdn=lbsrequest.search["msisdn"], permissionType=2)
            if whitelist[0][0]["_code"] != "101":
                response = whitelist[0][0]["_message"]
                l.info("Failed to Add MSISDN to allowed list")
                lbsrequest.response = {
                    "whitelist_message": whitelist[0][0]["_message"]
                }
                lbsrequest.save()
            else:
                # Do a lookup now we have whitelisted
                result = client.service.GetLocation(
                    username=settings.LBS_API_USERNAME, 
                    password=settings.LBS_API_PASSWORD, 
                    msisdn=lbsrequest.search["msisdn"])
                if result[0][0]["_code"] != "101":
                    l.info("Failed to return location")
                    lbsrequest.response = {
                        "lookup_message": result[0][0]["_message"]
                    }
                    lbsrequest.save()
                    response = result[0][0]["_message"]
                else:
                    l.info("Location found, creating lookup")
                    lbsrequest.response = {
                        "x": result[0][0]["x"],
                        "y": result[0][0]["y"],
                        "lookup_message": result[0][0]["_message"]
                    }
                    lbsrequest.save()
                    # Create location point
                    location = LookupLocation()
                    location.point = Point(
                        float(result[0][0]["x"]), float(result[0][0]["y"]))
                    location.save()
                    # set the location object for POI to the location
                    lookup_poi = lbsrequest.pointofinterest
                    lookup_poi.location = location
                    lookup_poi.save()
                    l.info("Location and Point of Interest linked")
                    response = result[0][0]["_message"]
            return response
        except SoftTimeLimitExceeded:
            logger.error(
                'Soft time limit exceed processing LBS lookup through \
                SOAP API via Celery.',
                exc_info=True)

lbs_lookup = LBS_Lookup()
