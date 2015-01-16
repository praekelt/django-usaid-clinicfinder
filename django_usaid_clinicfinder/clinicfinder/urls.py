from django.conf.urls import url, include
from rest_framework import routers
import views

router = routers.DefaultRouter()
router.register(r'pointofinterest', views.PointofInterestViewSet)
router.register(r'location', views.LocationViewSet)
router.register(r'requestlookup', views.LookupPointofInterestViewSet)
router.register(r'requestlocation', views.LookupLocationViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browseable API.
urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^api-auth/',
        include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api-token-auth/',
        'rest_framework.authtoken.views.obtain_auth_token')
]
