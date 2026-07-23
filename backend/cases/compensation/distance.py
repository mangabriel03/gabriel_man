"""Great-circle distance calculation.

Primary source: Airport Gap POST /airports/distance.
Fallback: local Haversine using seeded Airport lat/lon.
"""
from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation
from typing import Callable

import requests
from django.conf import settings

from airports.models import Airport

from .exceptions import DistanceUnavailable

EARTH_RADIUS_KM = Decimal("6371.0088")


class _AirportGapError(Exception):
    """Internal: any failure inside the Airport Gap client."""


def compute_leg_km(
    from_iata: str,
    to_iata: str,
    *,
    airport_lookup: Callable[[str], Airport | None],
) -> tuple[Decimal, str]:
    from_iata = from_iata.upper()
    to_iata = to_iata.upper()

    try:
        km = _airportgap_km(from_iata, to_iata)
        return _round_km(km), "airportgap"
    except _AirportGapError:
        pass

    a = airport_lookup(from_iata)
    b = airport_lookup(to_iata)
    if a is None:
        raise DistanceUnavailable(f"Unknown airport code: {from_iata}")
    if b is None:
        raise DistanceUnavailable(f"Unknown airport code: {to_iata}")
    if a.latitude is None or a.longitude is None:
        raise DistanceUnavailable(f"Missing coordinates for {from_iata}")
    if b.latitude is None or b.longitude is None:
        raise DistanceUnavailable(f"Missing coordinates for {to_iata}")

    km = _haversine_km(a.latitude, a.longitude, b.latitude, b.longitude)
    return _round_km(km), "haversine"


def _round_km(value: Decimal) -> Decimal:
    # 6dp internal precision; service layer rounds totals to 2dp for the API.
    return value.quantize(Decimal("0.000001"))


def _airportgap_km(from_iata: str, to_iata: str) -> Decimal:
    url = f"{settings.AIRPORTGAP_BASE_URL.rstrip('/')}/airports/distance"
    timeout = float(getattr(settings, "COMPENSATION_HTTP_TIMEOUT_S", 3.0))
    headers: dict[str, str] = {}
    token = getattr(settings, "AIRPORTGAP_TOKEN", "") or ""
    if token:
        headers["Authorization"] = f"Bearer token={token}"

    payload = {"from": from_iata, "to": to_iata}

    last_exc: Exception | None = None
    for attempt in range(2):  # one retry
        try:
            resp = requests.post(url, data=payload, headers=headers, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_exc = exc
            continue

        if resp.status_code >= 400:
            raise _AirportGapError(
                f"Airport Gap responded {resp.status_code} for {from_iata}->{to_iata}"
            )
        try:
            body = resp.json()
            km_raw = body["data"]["attributes"]["kilometers"]
            return Decimal(str(km_raw))
        except (ValueError, KeyError, TypeError, InvalidOperation) as exc:
            raise _AirportGapError(f"Malformed Airport Gap response: {exc}") from exc

    raise _AirportGapError(f"Airport Gap unreachable: {last_exc}")


def _haversine_km(lat1: Decimal, lon1: Decimal, lat2: Decimal, lon2: Decimal) -> Decimal:
    # Convert Decimal (or DB DecimalField) inputs to float ONLY for math.sin/cos,
    # then re-quantise the result. This keeps the returned value deterministic.
    la1 = math.radians(float(lat1))
    lo1 = math.radians(float(lon1))
    la2 = math.radians(float(lat2))
    lo2 = math.radians(float(lon2))
    dlat = la2 - la1
    dlon = lo2 - lo1
    a = math.sin(dlat / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))
    return EARTH_RADIUS_KM * Decimal(str(c))
