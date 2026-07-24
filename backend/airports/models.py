from __future__ import annotations

from django.db import models


class Airport(models.Model):
    iata = models.CharField(max_length=3, unique=True, db_index=True)
    icao = models.CharField(max_length=4, unique=True, null=True, blank=True)
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=120)
    country = models.CharField(max_length=120)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["iata"]

    def __str__(self) -> str:
        return f"{self.iata} — {self.name} ({self.city}, {self.country})"
