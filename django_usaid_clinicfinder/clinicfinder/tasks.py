from __future__ import absolute_import
import requests
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


class Metric_Sender(Task):

    """
    Task to fire metrics at Vumi
    """
    name = "clinicfinder.tasks.metric_sender"

    class FailedEventRequest(Exception):

        """
        The attempted task failed because of a non-200 HTTP return
        code.
        """

    def vumi_client(self):
        return HttpApiSender(
            account_key=settings.VUMI_GO_ACCOUNT_KEY,
            conversation_key=settings.VUMI_GO_CONVERSATION_KEY,
            conversation_token=settings.VUMI_GO_ACCOUNT_TOKEN
        )
        # return LoggingSender('go_http.test')

    def run(self, metric, value, agg, **kwargs):
        """
        Returns count of imported records
        """
        l = self.get_logger(**kwargs)

        l.info("Firing metric: %r [%s] -> %g" % (metric, agg, float(value)))
        try:
            sender = self.vumi_client()
            result = sender.fire_metric(metric, value, agg=agg)
            l.info("Result of firing metric: %s" % (result["success"]))
            return result

        except SoftTimeLimitExceeded:
            logger.error(
                'Soft time limit exceed processing metric fire \
                 via Celery.',
                exc_info=True)

metric_sender = Metric_Sender()

class LBS_Lookup(Task):

    """
    Task to request location from LBS API
    """
    name = "clinicfinder.tasks.lbs_lookup"
    LBS_API_SUCCESS = "101"

    class FailedEventRequest(Exception):

        """
        The attempted task failed because of a non-200 HTTP return
        code.
        """
    def normalize_msisdn(self, msisdn):
        return msisdn.replace("+", "")

    def lbs_api_client(self):
        return Client(settings.LBS_API_WSDL)

    def add_allowed_msisdn(self, msisdn):
        client = self.lbs_api_client()
        whitelist = client.service.AddAllowedMsisdn(
            username=settings.LBS_API_USERNAME,
            password=settings.LBS_API_PASSWORD,
            msisdn=self.normalize_msisdn(msisdn), permissionType=2)
        response = {
            "_code": whitelist[0][0]["_code"],
            "_message": whitelist[0][0]["_message"]
        }
        return response

    def get_location(self, msisdn):
        client = self.lbs_api_client()
        result = client.service.GetLocation(
            username=settings.LBS_API_USERNAME,
            password=settings.LBS_API_PASSWORD,
            msisdn=self.normalize_msisdn(msisdn))
        response = {
            "_code": result[0][0]["_code"],
            "_message": result[0][0]["_message"]
        }
        if response["_code"] == self.LBS_API_SUCCESS:
            response["x"] = result[0][0]["x"]
            response["y"] = result[0][0]["y"]
        return response

    def run(self, lbsrequest_id, **kwargs):
        """
        Gets user details, adds to whitelist and gets current location
        """
        l = self.get_logger(**kwargs)

        l.info("Processing new LBS lookup")
        response = "No response"
        lbsrequest = LBSRequest.objects.get(pk=lbsrequest_id)
        lbsrequest.response = {}
        try:
            whitelist = self.add_allowed_msisdn(lbsrequest.search["msisdn"])
            if whitelist["_code"] != self.LBS_API_SUCCESS:
                response = whitelist["_message"]
                l.info("Failed to Add MSISDN to allowed list")
                lbsrequest.response["whitelist_code"] = whitelist["_code"]
                lbsrequest.response[
                    "whitelist_message"] = whitelist["_message"]
                lbsrequest.response["success"] = "false"
            else:
                # Do a lookup now we have whitelisted
                result = self.get_location(lbsrequest.search["msisdn"])
                lbsrequest.response["lookup_code"] = result["_code"]
                lbsrequest.response["lookup_message"] = result["_message"]
                if result["_code"] != self.LBS_API_SUCCESS:
                    l.info("Failed to return location")
                    lbsrequest.response["success"] = "false"
                else:
                    l.info("Location found, creating lookup")
                    lbsrequest.response["x"] = result["x"]
                    lbsrequest.response["y"] = result["y"]
                    # Create location point
                    location = LookupLocation()
                    location.point = Point(
                        float(result["x"]), float(result["y"]))
                    location.save()
                    # set the location object for POI to the location
                    lookup_poi = lbsrequest.pointofinterest
                    lookup_poi.location = location
                    lookup_poi.save()
                    l.info("Location and Point of Interest linked")
                response = result["_message"]
        except SoftTimeLimitExceeded:
            logger.error(
                'Soft time limit exceed processing LBS lookup through \
                SOAP API via Celery.',
                exc_info=True)
        finally:
            lbsrequest.save()
            return response

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

    def vumi_client(self):
        return HttpApiSender(
            account_key=settings.VUMI_GO_ACCOUNT_KEY,
            conversation_key=settings.VUMI_GO_CONVERSATION_KEY,
            conversation_token=settings.VUMI_GO_ACCOUNT_TOKEN
        )

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
                sender = self.vumi_client()
                if response["results"] != "":
                    content = response["template"].replace(
                        "{{ results }}", response["results"])
                    vumiresponse = False
                    if len(content) <= settings.LOCATION_RESPONSE_MAX_LENGTH:
                        # Defaults to 320
                        vumiresponse = sender.send_text(
                            response["to_addr"], content)
                        lookuppoi.response["sent"] = "true"
                        l.info("Sent message to <%s>" % response["to_addr"])
                        metric_sender.delay(
                            metric="sms.results",
                            value=1, agg="sum")
                    else:
                        l.info(
                            "Message not sent to <%s>. "
                            "Too long at <%s> chars." %
                            (response["to_addr"], str(len(content))))
                else:
                    vumiresponse = sender.send_text(
                        response["to_addr"], settings.LOCATION_NONE_FOUND)
                    lookuppoi.response["sent"] = "true"
                    l.info("Sent no results message to <%s>" %
                           response["to_addr"])
                    metric_sender.delay(
                            metric="sms.noresults",
                            value=1, agg="sum")
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

            search_method_name = lookuppoi.search.get('source', 'internal')
            search_method = {
                'aat': self.search_aat,
                'internal': self.search_internal,
            }.get(search_method_name, self.search_internal)
            matches = search_method(lookuppoi)

            matches = matches[:settings.LOCATION_MAX_RESPONSES]
            total = len(matches)

            output = ' AND '.join(matches)

            lookuppoi.response["results"] = output
            lookuppoi.save()
            l.info("Completed location search. Found: %s" % str(total))
            location_sender.delay(lookuppointofinterest_id)
            return True
        except SoftTimeLimitExceeded:
            logger.error(
                'Soft time limit exceed processing location search \
                 via Celery.',
                exc_info=True)

    def format_match_aat(self, match):
        return "%s (%s)" % (
            match.get('OrganisationName'),
            match.get('FullAddress'))

    def search_aat(self, lookuppoi):
        url = (
            "%(url)s?username=%(username)s&password=%(password)s&meters=50000"
            "&category=%(category)s&x=%(x)s&y=%(y)s") % {
                'url': settings.AAT_API_URL,
                'username': settings.AAT_USERNAME,
                'password': settings.AAT_PASSWORD,
                'category': self.get_aat_category_id(lookuppoi.search),
                'x': lookuppoi.location.point.x,
                'y': lookuppoi.location.point.y
        }
        response = requests.get(url, verify=False)
        matches = response.json().get('clinics')
        return [self.format_match_aat(match) for match in matches]

    def get_aat_category_id(self, search):
        category = settings.AAT_DEFAULT_CATEGORY
        for cat_name, cat_value in settings.AAT_CATEGORIES.items():
            if search.get(cat_name, False):
                category = cat_name
                break
        return settings.AAT_CATEGORIES[category]

    def format_match_internal(self, match):
        primary = "Clinic Name"
        additional = ["Street Address", "Primary Contact Number"]
        add_output = ', '.join(
            match.data[key] for key in additional
            if key in match.data and match.data[key] != "")
        return "%s (%s)" % (match.data[primary], add_output)

    def search_internal(self, lookuppoi):
        ringfence = Distance(km=settings.LOCATION_SEARCH_RADIUS)
        locations = Location.objects.filter(
            point__distance_lte=(
                lookuppoi.location.point, ringfence)).filter(
            location__data__contains=lookuppoi.search).distance(
            lookuppoi.location.point).order_by('distance')
        matches = []
        for result in locations:
            for poi in result.location.all():
                matches.append(poi)
        return [self.format_match_internal(match) for match in matches]


location_finder = Location_Finder()


class PointOfInterest_Importer(Task):

    """
    Task to take dict import the data
    """
    name = "clinicfinder.tasks.pointofinterest_importer"

    class FailedEventRequest(Exception):

        """
        The attempted task failed because of a non-200 HTTP return
        code.
        """

    def run(self, poidata, **kwargs):
        """
        Returns count of imported records
        """
        l = self.get_logger(**kwargs)

        l.info("Processing new point of interest import data")
        imported = 0
        row = 0
        try:
            for line in poidata:
                row += 1
                if "Latitude" in line and "Longitude" in line:
                    if line["Longitude"] != "" and line["Latitude"] != "":
                        poi_point = Point(float(line["Longitude"]),
                                          float(line["Latitude"]))
                        # check if point exists
                        locations = Location.objects.filter(point=poi_point)
                        if locations.count() == 0:
                            # make a Location
                            location = Location()
                            location.point = poi_point
                            location.save()
                        else:
                            # Grab the top of the stack
                            location = locations[0]
                        # Create new point of interest with location
                        poi = PointOfInterest()
                        poi.location = location
                        poi.data = line
                        poi.save()
                        imported += 1
                        l.info("Imported: %s" % line["Clinic Name"])
                    else:
                        l.info(
                            "Row <%s> has corrupted point data, "
                            "not imported" % row)
                else:
                    l.info("Row <%s> missing point data, not imported" % row)
            l.info("Imported <%s> locations" % str(imported))
            return imported
        except SoftTimeLimitExceeded:
            logger.error(
                'Soft time limit exceed processing location import \
                 via Celery.',
                exc_info=True)

pointofinterest_importer = PointOfInterest_Importer()
