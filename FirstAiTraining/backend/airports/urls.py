from django.urls import path

from .views import AirportSearchView

urlpatterns = [
    path("airports/", AirportSearchView.as_view(), name="airport-search"),
]
