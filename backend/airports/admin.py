from django.contrib import admin

from .models import Airport


@admin.register(Airport)
class AirportAdmin(admin.ModelAdmin):
    list_display = ("iata", "icao", "name", "city", "country")
    search_fields = ("iata", "icao", "name", "city", "country")
    ordering = ("iata",)
