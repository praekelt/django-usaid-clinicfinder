import json
import mock
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from go_http.send import LoggingSender


from .models import (Location, PointOfInterest,
                     LookupLocation, LookupPointOfInterest,
                     LBSRequest)

from .tasks import Location_Sender, LBS_Lookup


class APITestCase(TestCase):

    def setUp(self):
        self.client = APIClient()


class AuthenticatedAPITestCase(APITestCase):

    def setUp(self):
        super(AuthenticatedAPITestCase, self).setUp()
        self.username = 'testuser'
        self.password = 'testpass'
        self.user = User.objects.create_user(self.username,
                                             'testuser@example.com',
                                             self.password)
        token = Token.objects.create(user=self.user)
        self.token = token.key
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token)


class TestClinicFinderDataStorage(AuthenticatedAPITestCase):

    fixtures = ["test_data.json"]

    def create_location(self, x, y):
        point_data = {
                "point": {
                "type": "Point",
                "coordinates": [
                    x,
                    y
                ]
            }
        }
        return point_data

    def create_poi_lookup(self, endpoint, search):
        poi_data = {
            "search": search,
            "response": {
                "type": "SMS",
                "to_addr": "+27123",
                "template": "Your nearest x is: {{ results }}"
            },
            "location": None
        }
        return poi_data


    def stub_add_allowed_msisdn(self, msisdn):
        response = {
            "_code": 101,
            "_message": "Success Allowed Message"
        }
        return response

    def stub_get_location_get_result(self, msisdn):
        response = {
            "_code": 101,
            "_message": "Success Get Location Message",
            "x": 17.9145812988280005,
            "y": -32.7461242675779979
        }
        return response


    def stub_get_location_no_result(self, msisdn):
        response = {
            "_code": 201,
            "_message": "The username or password is invalid",
        }
        return response


    def test_login(self):
        request = self.client.post(
            '/clinicfinder/api-token-auth/',
            {"username": "testuser", "password": "testpass"})
        token = request.data.get('token', None)
        self.assertIsNotNone(
            token, "Could not receive authentication token on login post.")
        self.assertEqual(request.status_code, 200,
                         "Status code on /auth/login was %s (should be 200)."
                         % request.status_code)

    def test_create_location_model_data(self):
        point_data = {
            "type": "Point",
            "coordinates": [
                18.0000000,
                -33.0000000
            ]
        }
        point = Point(18.0000000, -33.0000000)
        post_data = {
            "point": point_data
        }
        response = self.client.post('/clinicfinder/location/',
                                    json.dumps(post_data),
                                    content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Location.objects.last()
        self.assertEqual(d.point, point)

    def test_create_pointofinterest_model_data(self):
        post_data = {
            "data": {
                "mmc": "true",
                "hiv": "false"
            },
            "location": self.create_location(18.0000000, -33.0000000)
        }
        response = self.client.post('/clinicfinder/pointofinterest/',
                                    json.dumps(post_data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = PointOfInterest.objects.last()
        self.assertEqual(d.data["mmc"], "true")
        self.assertEqual(d.data["hiv"], "false")
        point = Point(18.0000000, -33.0000000)
        self.assertEqual(d.location.point, point)

    def test_create_lookuplocation_model_data(self):
        point_data = {
            "type": "Point",
            "coordinates": [
                18.0000000,
                -33.0000000
            ]
        }
        point = Point(18.0000000, -33.0000000)
        post_data = {
            "point": point_data
        }
        response = self.client.post('/clinicfinder/requestlocation/',
                                    json.dumps(post_data),
                                    content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = LookupLocation.objects.last()
        self.assertEqual(d.point, point)

    def test_create_lookuppointofinterest_model_data(self):
        Location_Sender.vumi_client = lambda x: LoggingSender('go_http.test')

        post_data = {
            "search": {
                "mmc": "true",
                "hiv": "false"
            },
            "response": {
                "type": "SMS",
                "to_addr": "+27123",
                "template": "Your nearest x is: {{ results }}"
            },
            "location": self.create_location(18.0000000, -33.0000000)
        }
        response = self.client.post('/clinicfinder/requestlookup/',
                                    json.dumps(post_data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = LookupPointOfInterest.objects.last()
        self.assertEqual(d.search["mmc"], "true")
        self.assertEqual(d.search["hiv"], "false")
        point = Point(18.0000000, -33.0000000)
        self.assertEqual(d.location.point, point)

    def test_create_lbsrequest_model_data(self):
        Location_Sender.vumi_client = lambda x: LoggingSender('go_http.test')
        LBS_Lookup.add_allowed_msisdn = self.stub_add_allowed_msisdn
        LBS_Lookup.get_location = self.stub_get_location_get_result

        post_data = {
            "search": {
                "msisdn": "27123"
            },
            "pointofinterest": self.create_poi_lookup('requestlookup', {"mmc": "true"})
        }
        response = self.client.post('/clinicfinder/lbsrequest/',
                                    json.dumps(post_data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        lbs = LBSRequest.objects.last()
        # Search for MMC saved
        self.assertEqual(lbs.pointofinterest.search["mmc"], "true")
        self.assertEqual(lbs.search["msisdn"], "27123")
        # LBS Call worked
        self.assertEqual(lbs.response["lookup_code"], "101")
        # LBS Call Result created new point
        lpoi = LookupPointOfInterest.objects.last()
        point = Point(17.9145812988280005, -32.7461242675779979)
        self.assertEqual(lpoi.location.point, point)
        self.assertEqual(lpoi.response["results"], "Seapoint Clinic (Seapoint)\n")

    def test_create_lbsrequest_model_data_no_result(self):
        Location_Sender.vumi_client = lambda x: LoggingSender('go_http.test')
        LBS_Lookup.add_allowed_msisdn = self.stub_add_allowed_msisdn
        LBS_Lookup.get_location = self.stub_get_location_no_result

        post_data = {
            "search": {
                "msisdn": "27123"
            },
            "pointofinterest": self.create_poi_lookup('requestlookup', {"mmc": "true"})
        }
        response = self.client.post('/clinicfinder/lbsrequest/',
                                    json.dumps(post_data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        lbs = LBSRequest.objects.last()
        # Search for MMC saved
        self.assertEqual(lbs.pointofinterest.search["mmc"], "true")
        self.assertEqual(lbs.search["msisdn"], "27123")
        # LBS Call denied
        self.assertEqual(lbs.response["lookup_code"], "201")
        # LBS Call Result did not create new point
        lpoi = LookupPointOfInterest.objects.last()
        self.assertEqual(lpoi.location, None)

    def test_create_lookuppointofinterest_model_data_no_result(self):
        # no valid clinic
        Location_Sender.vumi_client = lambda x: LoggingSender('go_http.test')

        post_data = {
            "search": {
                "mmc": "true",
                "hiv": "false"
            },
            "response": {
                "type": "SMS",
                "to_addr": "+27123",
                "template": "Your nearest x is: {{ results }}"
            },
            "location": self.create_location(29.0000000, -33.0000000)
        }
        response = self.client.post('/clinicfinder/requestlookup/',
                                    json.dumps(post_data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = LookupPointOfInterest.objects.last()
        self.assertEqual(d.search["mmc"], "true")
        self.assertEqual(d.search["hiv"], "false")
        point = Point(29.0000000, -33.0000000)
        self.assertEqual(d.location.point, point)
        self.assertEqual(d.response["results"], "")

        
