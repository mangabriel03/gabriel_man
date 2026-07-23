from django.urls import path

from .views import CaseCreateView

urlpatterns = [
    path("cases/", CaseCreateView.as_view(), name="case-create"),
]
