import json
import responses
from django.test import TestCase
from django.test.utils import override_settings
from django.conf import settings
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

from .tasks import (Location_Sender, LBS_Lookup,
                    PointOfInterest_Importer, Metric_Sender, metric_sender)


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

    fixtures = ["test_data.json", "test_multi_data.json"]

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
            "_code": "101",
            "_message": "Success Allowed Message"
        }
        return response

    def stub_get_location_get_result(self, msisdn):
        response = {
            "_code": "101",
            "_message": "Success Get Location Message",
            "x": 17.9145812988280005,
            "y": -32.7461242675779979
        }
        return response

    def stub_get_location_no_result(self, msisdn):
        response = {
            "_code": "201",
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
        Metric_Sender.vumi_client = lambda x: LoggingSender('go_http.test')

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
        Metric_Sender.vumi_client = lambda x: LoggingSender('go_http.test')
        LBS_Lookup.add_allowed_msisdn = self.stub_add_allowed_msisdn
        LBS_Lookup.get_location = self.stub_get_location_get_result

        post_data = {
            "search": {
                "msisdn": "27123"
            },
            "pointofinterest":
                self.create_poi_lookup('requestlookup', {"mmc": "true"})
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
        self.assertEqual(
            lpoi.response["results"], "Seapoint Clinic (Seapoint)")

    def test_create_lbsrequest_model_data_no_result(self):
        Location_Sender.vumi_client = lambda x: LoggingSender('go_http.test')
        Metric_Sender.vumi_client = lambda x: LoggingSender('go_http.test')
        LBS_Lookup.add_allowed_msisdn = self.stub_add_allowed_msisdn
        LBS_Lookup.get_location = self.stub_get_location_no_result

        post_data = {
            "search": {
                "msisdn": "27123"
            },
            "pointofinterest":
                self.create_poi_lookup('requestlookup', {"mmc": "true"})
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
        Metric_Sender.vumi_client = lambda x: LoggingSender('go_http.test')

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

    def test_create_lookuppointofinterest_model_data_2_result(self):
        # 4 valid clinics, shows two
        Location_Sender.vumi_client = lambda x: LoggingSender('go_http.test')
        Metric_Sender.vumi_client = lambda x: LoggingSender('go_http.test')

        post_data = {
            "search": {
                "hct": "true"
            },
            "response": {
                "type": "SMS",
                "to_addr": "+27123",
                "template": "Your nearest x is: {{ results }}"
            },
            "location": self.create_location(18.71208, -33.85105)
        }
        response = self.client.post('/clinicfinder/requestlookup/',
                                    json.dumps(post_data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = LookupPointOfInterest.objects.last()
        self.assertEqual(d.response["results"],
                         "Harmonie Clinic (0219806185/6205) "
                         "AND Hazendal Satellite Clinic (216969920)")

    def test_create_lookuppointofinterest_model_internal_result_hct(self):
        # 4 valid clinics, shows two
        Location_Sender.vumi_client = lambda x: LoggingSender('go_http.test')
        Metric_Sender.vumi_client = lambda x: LoggingSender('go_http.test')

        post_data = {
            "search": {
                "hct": "true",
                "source": "internal"
            },
            "response": {
                "type": "SMS",
                "to_addr": "+27123",
                "template": "Your nearest x is: {{ results }}"
            },
            "location": self.create_location(18.71208, -33.85105)
        }
        response = self.client.post('/clinicfinder/requestlookup/',
                                    json.dumps(post_data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = LookupPointOfInterest.objects.last()
        self.assertEqual(d.response["results"],
                         "Harmonie Clinic (0219806185/6205) "
                         "AND Hazendal Satellite Clinic (216969920)")

    @responses.activate
    def test_create_lookuppointofinterest_aat_result_hct(self):
        response_json = {
            "clinics": [{
                "OrganisationName": "A sample organsation name",
                "FullAddress": "This is the full address",
                "Y": -29.831989288330078,
                "X": 30.971157073974609,
                "Province": "KwaZulu-Natal",
                "Town": "Durban",
                "Suburb": "Sherwood",
                "Road": "Locksley Drive",
                "DistanceMeters": 13649.0},
                {
                "OrganisationName": "Another sample organsation",
                "FullAddress": "Room AC0202, 2nd Floor, Block AC",
                "Y": -29.837795257568359,
                "X": 30.988857269287109,
                "Province": "KwaZulu-Natal",
                "Town": "Durban",
                "Suburb": "",
                "Road": "Ward Road",
                "DistanceMeters": 15474.0
            }],
            "searchY": -29.7894726,
            "searchX": 30.83844}

        responses.add(
            responses.GET, settings.AAT_API_URL,
            body=json.dumps(response_json), status=200,
            content_type='application/json')

        # 4 valid clinics, shows two
        Location_Sender.vumi_client = lambda x: LoggingSender('go_http.test')
        Metric_Sender.vumi_client = lambda x: LoggingSender('go_http.test')

        post_data = {
            "search": {
                "hct": "true",
                "source": "aat"
            },
            "response": {
                "type": "SMS",
                "to_addr": "+27123",
                "template": "Your nearest x is: {{ results }}"
            },
            "location": self.create_location(30.83844, -29.7894726)
        }
        response = self.client.post('/clinicfinder/requestlookup/',
                                    json.dumps(post_data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = LookupPointOfInterest.objects.last()
        self.assertEqual(d.search["hct"], "true")
        self.assertEqual(d.search["source"], "aat")
        self.assertEqual(
            d.response["results"],
            "A sample organsation name (This is the full address) "
            "AND Another sample organsation (Room AC0202, 2nd Floor, "
            "Block AC)")

        request_url = responses.calls[0].request.url
        self.assertEqual(request_url, (
            "https://api-info4africa.aat.co.za/api/lookup/GetLocations?"
            "username=&password=&meters=50000&"
            "category=77&x=30.83844&y=-29.7894726"))

    @responses.activate
    def test_create_lookuppointofinterest_aat_result_mmc(self):
        response_json = {
            "clinics": [{
                "OrganisationName": "Sample organsation name",
                "FullAddress": "This is the full address",
                "Y": -29.831989288330078,
                "X": 30.971157073974609,
                "Province": "KwaZulu-Natal",
                "Town": "Durban",
                "Suburb": "Sherwood",
                "Road": "Locksley Drive",
                "DistanceMeters": 13649.0},
                {
                "OrganisationName": "Another sample organsation name",
                "FullAddress": "Room AC0202, 2nd Floor, Block AC",
                "Y": -29.837795257568359,
                "X": 30.988857269287109,
                "Province": "KwaZulu-Natal",
                "Town": "Durban",
                "Suburb": "",
                "Road": "Ward Road",
                "DistanceMeters": 15474.0
            }],
            "searchY": -29.7894726,
            "searchX": 30.83844}

        responses.add(
            responses.GET, settings.AAT_API_URL,
            body=json.dumps(response_json), status=200,
            content_type='application/json')

        # 4 valid clinics, shows two
        Location_Sender.vumi_client = lambda x: LoggingSender('go_http.test')
        Metric_Sender.vumi_client = lambda x: LoggingSender('go_http.test')

        post_data = {
            "search": {
                "mmc": "true",
                "source": "aat"
            },
            "response": {
                "type": "SMS",
                "to_addr": "+27123",
                "template": "Your nearest x is: {{ results }}"
            },
            "location": self.create_location(30.83844, -29.7894726)
        }
        response = self.client.post('/clinicfinder/requestlookup/',
                                    json.dumps(post_data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = LookupPointOfInterest.objects.last()
        self.assertEqual(
            d.response["results"],
            "Sample organsation name (This is the full address) "
            "AND Another sample organsation name (Room AC0202, 2nd Floor, "
            "Block AC)")

        request_url = responses.calls[0].request.url
        self.assertEqual(request_url, (
            "https://api-info4africa.aat.co.za/api/lookup/GetLocations?"
            "username=&password=&meters=50000&"
            "category=73&x=30.83844&y=-29.7894726"))

    def test_fire_metric(self):
        Metric_Sender.vumi_client = lambda x: LoggingSender('go_http.test')
        result = metric_sender.delay(
            metric="sms.noresults", value=1, agg="sum")
        self.assertTrue(result.successful())
        self.assertEquals(result.get()["reason"],
                          "Metrics published")


class TestUploadPoiCSV(TestCase):

    CSV_LINE_CLEAN_1 = {'Area 1': 'Pixley ka Seme',
                        'Area 2': '',
                        'Area 3': '',
                        'Clinic Name': 'All Services Clinic',
                        'HCT': 'true',
                        'ID': '5632',
                        'Latitude': '-29.66818',
                        'Longitude': '22.73732',
                        'MMC': 'true',
                        'Primary Contact Number': '533532037',
                        'Province': 'Northern Cape',
                        'Street Address': ''}
    CSV_LINE_CLEAN_2 = {'Area 1': 'Pixley ka Seme',
                        'Area 2': '',
                        'Area 3': '',
                        'Clinic Name': 'HCT Clinic',
                        'HCT': 'true',
                        'ID': '5633',
                        'Latitude': '-29.66648',
                        'Longitude': '22.73116',
                        'MMC': 'false',
                        'Primary Contact Number': '',
                        'Province': 'Northern Cape',
                        'Street Address': ''}
    CSV_LINE_DUP_LOC = {'Area 1': 'Pixley ka Seme',
                        'Area 2': '',
                        'Area 3': '',
                        'Clinic Name': 'MMC Clinic',
                        'HCT': 'false',
                        'ID': '5631',
                        'Latitude': '-29.66648',
                        'Longitude': '22.73116',
                        'MMC': 'true',
                        'Primary Contact Number': '538022222',
                        'Province': 'Northern Cape',
                        'Street Address': ''}

    CSV_LINE_NO_LAT = {'Area 1': 'Pixley ka Seme',
                       'Area 2': '',
                       'Area 3': '',
                       'Clinic Name': 'MMC Clinic',
                       'HCT': 'false',
                       'ID': '5631',
                       'Latitude': '',
                       'Longitude': '22.73116',
                       'MMC': 'true',
                       'Primary Contact Number': '538022222',
                       'Province': 'Northern Cape',
                       'Street Address': ''}

    @override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                       CELERY_ALWAYS_EAGER=True,
                       BROKER_BACKEND='memory',)
    def setUp(self):
        self.admin = User.objects.create_superuser(
            'test', 'test@example.com', "pass123")

    def test_upload_view_not_logged_in_blocked(self):
        response = self.client.get(reverse("locations_uploader"))
        # redirect
        self.assertEqual(response.status_code, 302)

    def test_upload_view_logged_in(self):
        self.client.login(username="test", password="pass123")

        response = self.client.get(reverse("locations_uploader"))
        self.assertIn("Upload Locations CSV", response.content)

    def test_upload_csv(self):
        clean_sample = list()
        clean_sample.append(self.CSV_LINE_CLEAN_1)
        clean_sample.append(self.CSV_LINE_CLEAN_2)
        results = PointOfInterest_Importer.delay(clean_sample)
        self.assertEqual(results.get(), 2)
        new_locations = Location.objects.all().count()
        self.assertEquals(new_locations, 2)
        new_pois = PointOfInterest.objects.all().count()
        self.assertEquals(new_pois, 2)

    def test_upload_csv_dupe_locations(self):
        dupe_sample = list()
        dupe_sample.append(self.CSV_LINE_CLEAN_1)
        dupe_sample.append(self.CSV_LINE_CLEAN_2)
        dupe_sample.append(self.CSV_LINE_DUP_LOC)
        results = PointOfInterest_Importer.delay(dupe_sample)
        self.assertEqual(results.get(), 3)
        new_locations = Location.objects.all().count()
        self.assertEquals(new_locations, 2)
        new_pois = PointOfInterest.objects.all().count()
        self.assertEquals(new_pois, 3)

    def test_upload_csv_no_lat(self):
        bad_sample = list()
        bad_sample.append(self.CSV_LINE_CLEAN_1)
        bad_sample.append(self.CSV_LINE_NO_LAT)
        results = PointOfInterest_Importer.delay(bad_sample)
        self.assertEqual(results.get(), 1)
        new_locations = Location.objects.all().count()
        self.assertEquals(new_locations, 1)
        new_pois = PointOfInterest.objects.all().count()
        self.assertEquals(new_pois, 1)


class TestClinicFinderDistanceSorting(AuthenticatedAPITestCase):

    fixtures = ["test_distance_data.json"]

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
            "_code": "101",
            "_message": "Success Allowed Message"
        }
        return response

    def stub_get_location_get_result(self, msisdn):
        response = {
            "_code": "101",
            "_message": "Success Get Location Message",
            "x": 17.9145812988280005,
            "y": -32.7461242675779979
        }
        return response

    def stub_get_location_no_result(self, msisdn):
        response = {
            "_code": "201",
            "_message": "The username or password is invalid",
        }
        return response

    def test_create_forward_result(self):
        # 4 valid clinics, shows two
        Location_Sender.vumi_client = lambda x: LoggingSender('go_http.test')

        post_data = {
            "search": {
                "hct": "true"
            },
            "response": {
                "type": "SMS",
                "to_addr": "+27123",
                "template": "Your nearest x is: {{ results }}"
            },
            "location": self.create_location(18.458404541015, -33.92578125)
        }
        response = self.client.post('/clinicfinder/requestlookup/',
                                    json.dumps(post_data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = LookupPointOfInterest.objects.last()
        self.assertEqual(d.response["results"],
                         "Clinic One (Tel One) "
                         "AND Clinic Two (Tel Two)")

    def test_create_reverse_result(self):
        # 4 valid clinics, shows two
        Location_Sender.vumi_client = lambda x: LoggingSender('go_http.test')

        post_data = {
            "search": {
                "hct": "true"
            },
            "response": {
                "type": "SMS",
                "to_addr": "+27123",
                "template": "Your nearest x is: {{ results }}"
            },
            "location": self.create_location(18.904724121094993, -33.92578125)
        }
        response = self.client.post('/clinicfinder/requestlookup/',
                                    json.dumps(post_data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = LookupPointOfInterest.objects.last()
        self.assertEqual(d.response["results"],
                         "Clinic Four (Tel Four) "
                         "AND Clinic Three (Tel Three)")
