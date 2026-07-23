from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
import responses
from django.conf import settings

from cases.compensation.distance import (
    _AirportGapError,
    _airportgap_km,
    _haversine_km,
    compute_leg_km,
)
from cases.compensation.exceptions import DistanceUnavailable


def _airport(iata: str, lat: str | None, lon: str | None):
    a = MagicMock()
    a.iata = iata
    a.latitude = None if lat is None else Decimal(lat)
    a.longitude = None if lon is None else Decimal(lon)
    return a


# ------------------------- Haversine -------------------------

@pytest.mark.parametrize(
    "a_lat,a_lon,b_lat,b_lon,expected_km,tolerance",
    [
        # JFK (40.6413,-73.7781) <-> LHR (51.4700,-0.4543) ~ 5540 km
        ("40.6413", "-73.7781", "51.4700", "-0.4543", 5540, 5),
        # OTP (44.5711,26.0850) <-> CDG (49.0097,2.5479) ~ 1850 km
        ("44.5711", "26.0850", "49.0097", "2.5479", 1850, 5),
        # Same point -> 0
        ("48.0", "16.0", "48.0", "16.0", 0, Decimal("0.01")),
        # Antipodal-ish: (0,0) <-> (0,180) is exactly π·R km ≈ 20015.09 km
        ("0.0", "0.0", "0.0", "180.0", 20015, 5),
    ],
)
def test_haversine_km_matches_known_distances(a_lat, a_lon, b_lat, b_lon, expected_km, tolerance):
    d = _haversine_km(Decimal(a_lat), Decimal(a_lon), Decimal(b_lat), Decimal(b_lon))
    assert abs(d - Decimal(expected_km)) <= Decimal(str(tolerance))


# ------------------------- Airport Gap client -------------------------

@responses.activate
def test_airportgap_km_happy_path():
    responses.add(
        responses.POST,
        f"{settings.AIRPORTGAP_BASE_URL.rstrip('/')}/airports/distance",
        json={"data": {"attributes": {"kilometers": 5540.12}}},
        status=200,
    )
    assert _airportgap_km("JFK", "LHR") == Decimal("5540.12")


@responses.activate
def test_airportgap_km_http_error_raises_internal():
    responses.add(
        responses.POST,
        f"{settings.AIRPORTGAP_BASE_URL.rstrip('/')}/airports/distance",
        status=500,
    )
    with pytest.raises(_AirportGapError):
        _airportgap_km("JFK", "LHR")


@responses.activate
def test_airportgap_km_malformed_body_raises_internal():
    responses.add(
        responses.POST,
        f"{settings.AIRPORTGAP_BASE_URL.rstrip('/')}/airports/distance",
        json={"data": {"attributes": {}}},
        status=200,
    )
    with pytest.raises(_AirportGapError):
        _airportgap_km("JFK", "LHR")


@responses.activate
def test_airportgap_km_non_numeric_kilometers_raises_internal():
    responses.add(
        responses.POST,
        f"{settings.AIRPORTGAP_BASE_URL.rstrip('/')}/airports/distance",
        json={"data": {"attributes": {"kilometers": "banana"}}},
        status=200,
    )
    with pytest.raises(_AirportGapError):
        _airportgap_km("JFK", "LHR")


@responses.activate
def test_airportgap_km_retries_once_on_connection_error():
    import requests
    call_count = {"n": 0}

    def _callback(request):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise requests.ConnectionError("simulated flake")
        return (200, {}, '{"data":{"attributes":{"kilometers":123.4}}}')

    responses.add_callback(
        responses.POST,
        f"{settings.AIRPORTGAP_BASE_URL.rstrip('/')}/airports/distance",
        callback=_callback,
    )
    assert _airportgap_km("JFK", "LHR") == Decimal("123.4")
    assert call_count["n"] == 2


# ------------------------- compute_leg_km -------------------------

@responses.activate
def test_compute_leg_km_uses_airportgap_when_available():
    responses.add(
        responses.POST,
        f"{settings.AIRPORTGAP_BASE_URL.rstrip('/')}/airports/distance",
        json={"data": {"attributes": {"kilometers": 5540.12}}},
        status=200,
    )
    km, source = compute_leg_km(
        "JFK", "LHR",
        airport_lookup=lambda i: None,   # not called
    )
    assert source == "airportgap"
    assert km == Decimal("5540.120000")


def test_compute_leg_km_falls_back_to_haversine(monkeypatch):
    from cases.compensation import distance as dmod
    monkeypatch.setattr(dmod, "_airportgap_km",
                        lambda *_a, **_k: (_ for _ in ()).throw(dmod._AirportGapError("boom")))
    lookup = {
        "JFK": _airport("JFK", "40.6413", "-73.7781"),
        "LHR": _airport("LHR", "51.4700", "-0.4543"),
    }
    km, source = compute_leg_km("jfk", "lhr", airport_lookup=lookup.get)
    assert source == "haversine"
    assert abs(km - Decimal("5540")) <= Decimal("5")


def test_compute_leg_km_raises_when_iata_unknown(monkeypatch):
    from cases.compensation import distance as dmod
    monkeypatch.setattr(dmod, "_airportgap_km",
                        lambda *_a, **_k: (_ for _ in ()).throw(dmod._AirportGapError("boom")))
    with pytest.raises(DistanceUnavailable, match="Unknown airport code: JFK"):
        compute_leg_km("JFK", "LHR", airport_lookup=lambda _i: None)


def test_compute_leg_km_raises_when_coordinates_missing(monkeypatch):
    from cases.compensation import distance as dmod
    monkeypatch.setattr(dmod, "_airportgap_km",
                        lambda *_a, **_k: (_ for _ in ()).throw(dmod._AirportGapError("boom")))
    lookup = {
        "JFK": _airport("JFK", None, None),
        "LHR": _airport("LHR", "51.4700", "-0.4543"),
    }
    with pytest.raises(DistanceUnavailable, match="Missing coordinates for JFK"):
        compute_leg_km("JFK", "LHR", airport_lookup=lookup.get)
