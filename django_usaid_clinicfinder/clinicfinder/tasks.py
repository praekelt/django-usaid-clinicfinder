from __future__ import absolute_import

from celery.task import Task
from celery.utils.log import get_task_logger
from celery.exceptions import SoftTimeLimitExceeded
from suds.client import Client
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
from go_http.send import HttpApiSender

from django.conf import settings

from clinicfinder.models import (LBSRequest, LookupPointOfInterest,
                                 LookupLocation, PointOfInterest,
                                 Location)

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
        LBS_API_SUCCESS = 101

        l.info("Processing new LBS lookup")
        response = "No response"
        lbsrequest = LBSRequest.objects.get(pk=lbsrequest_id)
        lbsrequest.response = {}
        try:
            client = self.lbs_api_client()
            whitelist = client.service.AddAllowedMsisdn(
                username=settings.LBS_API_USERNAME,
                password=settings.LBS_API_PASSWORD,
                msisdn=lbsrequest.search["msisdn"], permissionType=2)
            if whitelist[0][0]["_code"] != LBS_API_SUCCESS:
                response = whitelist[0][0]["_message"]
                l.info("Failed to Add MSISDN to allowed list")
                lbsrequest.response[
                    "whitelist_code"] = whitelist[0][0]["_code"]
                lbsrequest.response["whitelist_message"] = whitelist[
                    0][0]["_message"]
                lbsrequest.response["success"] = "false"
            else:
                # Do a lookup now we have whitelisted
                result = client.service.GetLocation(
                    username=settings.LBS_API_USERNAME,
                    password=settings.LBS_API_PASSWORD,
                    msisdn=lbsrequest.search["msisdn"])
                if result[0][0]["_code"] != LBS_API_SUCCESS:
                    l.info("Failed to return location")
                    lbsrequest.response["lookup_code"] = result[0][0]["_code"]
                    lbsrequest.response["lookup_message"] = result[
                        0][0]["_message"]
                    lbsrequest.response["success"] = "false"
                    response = result[0][0]["_message"]
                else:
                    l.info("Location found, creating lookup")
                    lbsrequest.response["x"] = result[0][0]["x"]
                    lbsrequest.response["y"] = result[0][0]["y"]
                    lbsrequest.response["lookup_message"] = result[
                        0][0]["_message"]
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
        finally:
            lbsrequest.save()

lbs_lookup = LBS_Lookup()


class Location_Sender(Task):

    """
    Task to take results and send them off. SMS only for now.
    """
    name = "clinicfinder.tasks.location_sender"

    class FailedEventRequest(Exception):

        """
        The attempted task failed because of a non-200 HTTP return
        code.
        """

    def run(self, lookuppointofinterest_id, **kwargs):
        """
        Returns a filtered list of locations for query
        """
        l = self.get_logger(**kwargs)

        l.info("Processing new location result sending")
        try:
            lookuppoi = LookupPointOfInterest.objects.get(
                pk=lookuppointofinterest_id)
            response = lookuppoi.response
            if response["type"] == "SMS" and "sent" not in response:
                # send via Vumi
                sender = HttpApiSender(
                    account_key=settings.VUMI_GO_ACCOUNT_KEY,
                    conversation_key=settings.VUMI_GO_CONVERSATION_KEY,
                    conversation_token=settings.VUMI_GO_ACCOUNT_TOKEN
                )
                content = response["template"].replace(
                    "{{ results }}", response["results"])
                if len(content) <= settings.LOCATION_RESPONSE_MAX_LENGTH:
                    # Defaults to 320
                    vumiresponse = sender.send_text(
                        response["to_addr"], content)
                    lookuppoi.response["sent"] = "true"
                    l.info("Sent message to <%s>" % response["to_addr"])
                else:
                    l.info("Message not sent to <%s>. Too long at <%s> chars." %
                           (response["to_addr"], str(len(content))))
                lookuppoi.save()

                return vumiresponse
            else:
                l.info("No message sent for lookuppointofinterest <%s>" %
                       str(lookuppointofinterest_id))
        except SoftTimeLimitExceeded:
            logger.error(
                'Soft time limit exceed processing location search \
                 via Celery.',
                exc_info=True)

location_sender = Location_Sender()


class Location_Finder(Task):

    """
    Task to take location and search for results
    """
    name = "clinicfinder.tasks.location_finder"

    class FailedEventRequest(Exception):

        """
        The attempted task failed because of a non-200 HTTP return
        code.
        """

    def run(self, lookuppointofinterest_id, **kwargs):
        """
        Returns a filtered list of locations for query
        """
        l = self.get_logger(**kwargs)

        l.info("Processing new location search")
        try:
            lookuppoi = LookupPointOfInterest.objects.get(
                pk=lookuppointofinterest_id)
            distance = Distance(km=10)
            locations = Location.objects.filter(
                point__distance_lte=(lookuppoi.location.point, distance))
            matches = PointOfInterest.objects.filter(
                data__contains=lookuppoi.search).filter(location=locations)
            output = ""
            for match in matches:
                output += "%s (%s)\n" % (
                    match.data["Clinic Name"], match.data["Street Address"])
            lookuppoi.response["results"] = output
            lookuppoi.save()
            l.info("Results: %s" % output)
            l.info("Locations found, sending results")
            location_sender.delay(lookuppointofinterest_id)
            return True
        except SoftTimeLimitExceeded:
            logger.error(
                'Soft time limit exceed processing location search \
                 via Celery.',
                exc_info=True)

location_finder = Location_Finder()
