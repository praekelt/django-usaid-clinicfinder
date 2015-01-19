import json
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token


from .models import (Location, PointOfInterest,
                     LookupLocation, LookupPointOfInterest,
                     LBSRequest)


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

    def create_location(self, endpoint, x, y):
        point_data = {
            "type": "Point",
            "coordinates": [
                x,
                y
            ]
        }
        post_data = {
            "point": point_data
        }
        response = self.client.post('/clinicfinder/' + endpoint + '/',
                                    json.dumps(post_data),
                                    content_type='application/json')
        return response.data

    def create_poi_lookup(self, endpoint, search):
        poi_data = {
            "search": search,
            "response": {
                "type": "SMS",
                "to_addr": "+27123",
                "template": "Your nearest x is result"
            },
            "location": None
        }
        response = self.client.post('/clinicfinder/' + endpoint + '/',
                                    json.dumps(poi_data),
                                    content_type='application/json')
        return response.data


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
            "location": self.create_location('location', 18.0000000, -33.0000000)
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
        post_data = {
            "search": {
                "mmc": "true",
                "hiv": "false"
            },
            "response": {
                "type": "SMS",
                "to_addr": "+27123",
                "template": "Your nearest x is result"
            },
            "location": self.create_location('requestlocation', 18.0000000, -33.0000000)
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
        # poi_lookup = self.create_poi_lookup('requestlookup', {"mmc": "true"})
        # print poi_lookup
        post_data = {
            "search": {
                "msisdn": "27123"
            },
            "pointofinterest": self.create_poi_lookup('requestlookup', {"mmc": "true"})
        }
        response = self.client.post('/clinicfinder/lbsrequest/',
                                    json.dumps(post_data),
                                    content_type='application/json')
        # print response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = LBSRequest.objects.last()
        self.assertEqual(d.pointofinterest.search["mmc"], "true")
        self.assertEqual(d.search["msisdn"], "27123")
