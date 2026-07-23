from django.urls import path

from .views import CaseCreateView, CompensationPreviewView

urlpatterns = [
    path("cases/", CaseCreateView.as_view(), name="case-create"),
    path("compensation/preview/", CompensationPreviewView.as_view(),
         name="compensation-preview"),
]
