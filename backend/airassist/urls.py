from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns: list = [
    path("admin/", admin.site.urls),
    path("api/", include("airports.urls")),
    path("api/", include("cases.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
