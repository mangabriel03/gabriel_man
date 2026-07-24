from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from cases.compensation.exceptions import DistanceUnavailable


PREVIEW_URL = "/api/compensation/preview/"


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_preview_happy_path(two_airports):
    with patch("cases.views.preview_from_legs") as m:
        m.return_value = {
            "distance_km": Decimal("1874.00"),
            "compensation_amount_eur": 400,
            "legs": [
                {"from": "OTP", "to": "CDG",
                 "distance_km": Decimal("1874.00"),
                 "source": "airportgap", "error": None},
            ],
        }
        resp = APIClient().post(PREVIEW_URL,
                                {"legs": [{"from": "otp", "to": "cdg"}]},
                                format="json")
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert body["compensation_amount_eur"] == 400
    assert body["distance_km"] == "1874.00"
    assert body["legs"][0]["source"] == "airportgap"


@pytest.mark.parametrize(
    "payload,error_key",
    [
        ({"legs": []}, "legs"),
        ({"legs": [{"from": "AB", "to": "CDG"}]}, "legs"),
        ({"legs": [{"from": "abcd", "to": "CDG"}]}, "legs"),
        ({"legs": [{"from": "OTP", "to": "OTP"}]}, "legs"),
        ({}, "legs"),
        ({"legs": [{"from": "OTP", "to": "CDG"}] * 6}, "legs"),
    ],
)
@pytest.mark.django_db
def test_preview_rejects_malformed_input(payload, error_key):
    resp = APIClient().post(PREVIEW_URL, payload, format="json")
    assert resp.status_code == 400
    assert error_key in resp.json()


@pytest.mark.django_db
def test_preview_returns_422_when_service_raises(two_airports):
    err = DistanceUnavailable(
        "boom",
        payload={
            "detail": "Distance could not be calculated for one or more legs.",
            "legs": [{"from": "XXX", "to": "CDG", "distance_km": None,
                      "source": None, "error": "Unknown airport code: XXX"}],
        },
    )
    with patch("cases.views.preview_from_legs", side_effect=err):
        resp = APIClient().post(PREVIEW_URL,
                                {"legs": [{"from": "XXX", "to": "CDG"}]},
                                format="json")
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"].startswith("Distance could not be calculated")
    assert body["legs"][0]["error"] == "Unknown airport code: XXX"


@pytest.mark.django_db
def test_preview_throttles_after_60_requests(two_airports, settings):
    # Sanity: the throttle rate is exactly what we advertise. Read-only check
    # to avoid mutating the nested dict (pytest-django's `settings` fixture
    # only snapshots top-level attributes, so nested mutations would leak).
    assert (
        settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["compensation_preview"]
        == "60/min"
    )

    client = APIClient()
    with patch("cases.views.preview_from_legs") as m:
        m.return_value = {
            "distance_km": Decimal("1.00"),
            "compensation_amount_eur": 250,
            "legs": [{"from": "OTP", "to": "CDG",
                      "distance_km": Decimal("1.00"),
                      "source": "airportgap", "error": None}],
        }
        for _ in range(60):
            resp = client.post(PREVIEW_URL,
                               {"legs": [{"from": "OTP", "to": "CDG"}]},
                               format="json")
            assert resp.status_code == 200
        # 61st -> throttled
        resp = client.post(PREVIEW_URL,
                           {"legs": [{"from": "OTP", "to": "CDG"}]},
                           format="json")
    assert resp.status_code == 429
