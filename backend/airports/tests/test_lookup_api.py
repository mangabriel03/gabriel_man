from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from airports.models import Airport


@pytest.fixture
def airports(db):
    Airport.objects.create(iata="CDG", icao="LFPG", name="Charles de Gaulle",
                           city="Paris", country="France",
                           latitude="49.0097", longitude="2.5479")
    Airport.objects.create(iata="OTP", icao="LROP", name="Henri Coanda",
                           city="Bucharest", country="Romania",
                           latitude="44.5711", longitude="26.0850")
    Airport.objects.create(iata="FRA", icao="EDDF", name="Frankfurt Airport",
                           city="Frankfurt", country="Germany",
                           latitude="50.0379", longitude="8.5622")


def test_empty_q_returns_empty_list(airports):
    resp = APIClient().get("/api/airports/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_iata_exact_match_first(airports):
    resp = APIClient().get("/api/airports/?q=CDG")
    body = resp.json()
    assert body[0]["iata"] == "CDG"


def test_city_icontains(airports):
    resp = APIClient().get("/api/airports/?q=Paris")
    iatas = [row["iata"] for row in resp.json()]
    assert "CDG" in iatas


def test_limit_is_capped(airports):
    resp = APIClient().get("/api/airports/?q=a&limit=999")
    assert resp.status_code == 200
    assert len(resp.json()) <= 50
