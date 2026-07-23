from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest
import responses
from django.conf import settings
from django.core.management import call_command

from airports.models import Airport


@pytest.fixture
def fixture_path(tmp_path) -> Path:
    data = [
        {"iata": "CDG", "icao": "LFPG", "name": "Charles de Gaulle",
         "city": "Paris", "country": "France",
         "latitude": "49.0097", "longitude": "2.5479"},
        {"iata": "OTP", "icao": "LROP", "name": "Henri Coanda",
         "city": "Bucharest", "country": "Romania",
         "latitude": "44.5711", "longitude": "26.0850"},
    ]
    path = tmp_path / "airports.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.mark.django_db
def test_sync_from_fixture_creates_rows(fixture_path: Path) -> None:
    call_command("sync_airports", "--from-fixture", str(fixture_path), stdout=StringIO())
    assert Airport.objects.count() == 2
    cdg = Airport.objects.get(iata="CDG")
    assert cdg.city == "Paris"


@pytest.mark.django_db
def test_sync_from_fixture_is_idempotent(fixture_path: Path) -> None:
    call_command("sync_airports", "--from-fixture", str(fixture_path), stdout=StringIO())
    call_command("sync_airports", "--from-fixture", str(fixture_path), stdout=StringIO())
    assert Airport.objects.count() == 2


@pytest.mark.django_db
@responses.activate
def test_sync_from_api_paginates_and_upserts() -> None:
    base = settings.AIRPORTGAP_BASE_URL.rstrip("/")
    responses.add(
        responses.GET,
        f"{base}/airports",
        json={
            "data": [
                {"id": "CDG", "type": "airport",
                 "attributes": {"iata": "CDG", "icao": "LFPG",
                                "name": "Charles de Gaulle", "city": "Paris",
                                "country": "France",
                                "latitude": "49.0097", "longitude": "2.5479"}}
            ],
            "links": {"next": f"{base}/airports?page=2"},
        },
        status=200,
    )
    responses.add(
        responses.GET,
        f"{base}/airports?page=2",
        json={
            "data": [
                {"id": "OTP", "type": "airport",
                 "attributes": {"iata": "OTP", "icao": "LROP",
                                "name": "Henri Coanda", "city": "Bucharest",
                                "country": "Romania",
                                "latitude": "44.5711", "longitude": "26.0850"}}
            ],
            "links": {"next": None},
        },
        status=200,
    )
    call_command("sync_airports", stdout=StringIO())
    assert Airport.objects.count() == 2
