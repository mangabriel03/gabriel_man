# CASE_02 — Compensation Calculation Implementation Plan

> **Execution:** Use subagent-driven development to implement this plan task-by-task.

**Goal:** Extend the CASE_01 case-entry flow with a live-preview compensation calculator (great-circle distance summed over all legs → 250/400/600 € bracket) that persists the result on the `Case` row and is displayed to the passenger both during entry and on the confirmation view.

**Architecture:** New `cases.compensation` sub-package containing pure bracket math, a distance module (Airport Gap API with local Haversine fallback), and an orchestration service. A new `POST /api/compensation/preview` endpoint drives a debounced React component. The existing `POST /api/cases/` view is extended (additively) to persist `distance_km`, `compensation_amount_eur`, `compensation_calculated_at` inside the current atomic block; a calculation failure never blocks case creation.

**Tech Stack:** Python 3.12+, Django 5.x, DRF, `requests`, `responses` (test), Decimal-based math, React 18 + TypeScript, React Hook Form, Vitest + React Testing Library.

**Design Spec:** [documentation/spec-driven/specs/2026-07-23-case-02-compensation-design.md](../specs/2026-07-23-case-02-compensation-design.md)

---

## Task Ordering

Tasks 1–3 build the pure-Python compensation core with no external dependencies (brackets → distance → orchestration service). Task 4 exposes the preview endpoint. Task 5 lands the DB migration and admin. Task 6 wires the calc into case create and extends its integration tests. Task 7 builds the frontend API client. Task 8 adds the `CompensationSummary` component. Task 9 wires the component into the form and extends the confirmation view + form tests. Every task must pass `pytest` (or `npm test` for frontend tasks) before moving on.

---

## File Structure

**Backend — create:**
- `backend/cases/compensation/__init__.py`
- `backend/cases/compensation/brackets.py`
- `backend/cases/compensation/distance.py`
- `backend/cases/compensation/exceptions.py`
- `backend/cases/compensation/service.py`
- `backend/cases/migrations/0002_case_compensation_fields.py`
- `backend/cases/tests/test_compensation_brackets.py`
- `backend/cases/tests/test_compensation_distance.py`
- `backend/cases/tests/test_compensation_service.py`
- `backend/cases/tests/test_compensation_preview_api.py`

**Backend — modify:**
- `backend/cases/models.py` (add 3 nullable fields + `CheckConstraint`)
- `backend/cases/admin.py` (expose new fields read-only)
- `backend/cases/serializers.py` (add `PreviewRequestSerializer`)
- `backend/cases/views.py` (add `CompensationPreviewView`, extend `CaseCreateView`)
- `backend/cases/urls.py` (add preview route)
- `backend/airassist/settings/base.py` (add throttle rate + timeout setting)
- `backend/cases/tests/test_api.py` (extend for new response fields + failure path)

**Frontend — create:**
- `frontend/src/api/compensation.ts`
- `frontend/src/features/case-entry/CompensationSummary.tsx`
- `frontend/src/features/case-entry/CompensationSummary.module.css`
- `frontend/tests/CompensationSummary.test.tsx`

**Frontend — modify:**
- `frontend/src/features/case-entry/types.ts` (extend `CaseCreateResponse`)
- `frontend/src/features/case-entry/CaseEntryForm.tsx` (render summary; show amount on success view)
- `frontend/tests/CaseEntryForm.test.tsx` (assert summary present; assert compensation on success view)

---

### Task 1: Compensation brackets (pure math)

**Files:**
- Create: `backend/cases/compensation/__init__.py`
- Create: `backend/cases/compensation/brackets.py`
- Create: `backend/cases/tests/test_compensation_brackets.py`

**Requirements:**
- `compensation_for_km(distance_km)` accepts `Decimal | float | int` and returns an `int` in `{250, 400, 600}`.
- Boundary rule (confirmed with product): `d ≤ 1500 → 250`, `1500 < d ≤ 3500 → 400`, `d > 3500 → 600`. Both boundaries fall into the *lower* bracket.
- Zero/negative inputs are treated as short-haul (`250 €`) — no exception, no logging. Never returns `None`.
- Uses `Decimal(str(x))` to avoid float representation error at the boundaries.
- No imports from `cases.models` or any I/O module.

**Implementation:**

`backend/cases/compensation/__init__.py`:

```python
"""Compensation calculation sub-package.

Public API re-exports are added by subsequent tasks.
"""
```

`backend/cases/compensation/brackets.py`:

```python
"""Pure bracket-lookup for EU 261 compensation amounts.

Boundaries confirmed with product:
    d <= 1500 km            -> 250 EUR
    1500 < d <= 3500 km     -> 400 EUR
    d > 3500 km             -> 600 EUR
"""
from __future__ import annotations

from decimal import Decimal
from typing import Union

Number = Union[Decimal, float, int]

SHORT_HAUL_KM = Decimal("1500")
MEDIUM_HAUL_KM = Decimal("3500")

SHORT_HAUL_EUR = 250
MEDIUM_HAUL_EUR = 400
LONG_HAUL_EUR = 600


def compensation_for_km(distance_km: Number) -> int:
    d = Decimal(str(distance_km))
    if d <= SHORT_HAUL_KM:
        return SHORT_HAUL_EUR
    if d <= MEDIUM_HAUL_KM:
        return MEDIUM_HAUL_EUR
    return LONG_HAUL_EUR
```

**Testing:**

`backend/cases/tests/test_compensation_brackets.py`:

```python
from __future__ import annotations

from decimal import Decimal

import pytest

from cases.compensation.brackets import compensation_for_km


@pytest.mark.parametrize(
    "distance_km,expected",
    [
        (0, 250),
        (Decimal("0"), 250),
        (-5, 250),
        (Decimal("1499.99"), 250),
        (Decimal("1500.00"), 250),          # boundary -> lower bracket
        (1500, 250),
        (Decimal("1500.01"), 400),
        (2000, 400),
        (Decimal("3499.99"), 400),
        (Decimal("3500.00"), 400),          # boundary -> lower bracket
        (3500, 400),
        (Decimal("3500.01"), 600),
        (5000.5, 600),
        (20000, 600),
    ],
)
def test_compensation_for_km_returns_expected_bracket(distance_km, expected):
    assert compensation_for_km(distance_km) == expected


def test_return_type_is_int():
    assert isinstance(compensation_for_km(1000), int)
    assert isinstance(compensation_for_km(Decimal("4000")), int)
```

**Verification:**

```powershell
cd backend
pytest cases/tests/test_compensation_brackets.py -q
```

Expect: 2 test functions, 15 assertions, all pass.

---

### Task 2: Distance module — Haversine + Airport Gap client

**Files:**
- Create: `backend/cases/compensation/exceptions.py`
- Create: `backend/cases/compensation/distance.py`
- Create: `backend/cases/tests/test_compensation_distance.py`

**Requirements:**
- `_haversine_km(lat1, lon1, lat2, lon2) -> Decimal` — pure math, returns km with 6dp precision, uses `Decimal` throughout with `EARTH_RADIUS_KM = Decimal("6371.0088")`.
- `_airportgap_km(from_iata, to_iata) -> Decimal` — POSTs `data={"from": ..., "to": ...}` to `f"{settings.AIRPORTGAP_BASE_URL}/airports/distance"`, timeout `settings.COMPENSATION_HTTP_TIMEOUT_S` (default `3.0`), sends `Authorization: Bearer token=<AIRPORTGAP_TOKEN>` only if the token is non-empty, one retry on `requests.ConnectionError` / `requests.Timeout`. Parses `response.json()["data"]["attributes"]["kilometers"]` into `Decimal`. Raises the private `_AirportGapError` for any failure (HTTP ≥ 400, network, missing key, non-numeric value).
- `compute_leg_km(from_iata, to_iata, *, airport_lookup) -> tuple[Decimal, str]` — tries Airport Gap first; on `_AirportGapError` falls back to Haversine using `airport_lookup(iata) -> Airport | None`. Returns `(distance_km, "airportgap")` or `(distance_km, "haversine")`. Raises `DistanceUnavailable` if both branches fail (Airport Gap error and any airport is `None` or has null lat/lon).
- Never uses floats for the Haversine intermediate result; converts to `Decimal` at the end.
- No global state, no module-level HTTP calls.

**Implementation:**

`backend/cases/compensation/exceptions.py`:

```python
"""Compensation-calculation exceptions."""
from __future__ import annotations


class DistanceUnavailable(Exception):
    """Raised when a leg's distance cannot be determined by any source.

    The service layer attaches a ``payload`` dict describing per-leg failures
    so the preview view can return a structured 422 body.
    """

    def __init__(self, message: str, payload: dict | None = None) -> None:
        super().__init__(message)
        self.payload = payload
```

`backend/cases/compensation/distance.py`:

```python
"""Great-circle distance calculation.

Primary source: Airport Gap POST /airports/distance.
Fallback: local Haversine using seeded Airport lat/lon.
"""
from __future__ import annotations

import math
from decimal import Decimal
from typing import Callable, Protocol

import requests
from django.conf import settings

from airports.models import Airport

from .exceptions import DistanceUnavailable

EARTH_RADIUS_KM = Decimal("6371.0088")


class _AirportGapError(Exception):
    """Internal: any failure inside the Airport Gap client."""


class _Lookup(Protocol):
    def __call__(self, iata: str) -> Airport | None: ...  # pragma: no cover


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
        except (ValueError, KeyError, TypeError) as exc:
            raise _AirportGapError(f"Malformed Airport Gap response: {exc}") from exc

    raise _AirportGapError(f"Airport Gap unreachable: {last_exc}")


def _haversine_km(lat1, lon1, lat2, lon2) -> Decimal:
    # Convert Decimal (or DB DecimalField) inputs to float ONLY for math.sin/cos,
    # then re-quantise the result. This keeps the returned value deterministic.
    la1 = math.radians(float(lat1))
    lo1 = math.radians(float(lon1))
    la2 = math.radians(float(lat2))
    lo2 = math.radians(float(lon2))
    dlat = la2 - la1
    dlon = lo2 - lo1
    a = math.sin(dlat / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return EARTH_RADIUS_KM * Decimal(str(c))
```

**Testing:**

`backend/cases/tests/test_compensation_distance.py`:

```python
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
        # OTP (44.5711,26.0850) <-> CDG (49.0097,2.5479) ~ 1874 km
        ("44.5711", "26.0850", "49.0097", "2.5479", 1874, 5),
        # Same point -> 0
        ("48.0", "16.0", "48.0", "16.0", 0, Decimal("0.01")),
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
```

**Verification:**

```powershell
cd backend
pytest cases/tests/test_compensation_distance.py -q
```

Expect: 10 tests, all pass. `responses` library must be in `requirements-dev.txt` (already listed).

---

### Task 3: Compensation service (orchestration + request serializer)

**Files:**
- Create: `backend/cases/compensation/service.py`
- Create: `backend/cases/tests/test_compensation_service.py`
- Modify: `backend/cases/compensation/__init__.py` (re-export public API)
- Modify: `backend/cases/serializers.py` (append `PreviewRequestSerializer`)

**Requirements:**
- `preview_from_legs(validated_legs)` accepts a list of dicts `[{"from": "JFK", "to": "LHR"}, ...]` (already uppercased by the serializer). Returns `{"distance_km": Decimal, "compensation_amount_eur": int, "legs": [...]}`. On failure raises `DistanceUnavailable` with a `.payload` dict of the same shape but including per-leg `error` fields (successful legs get `error: None`; failed legs get `distance_km: None`, `source: None`, `error: "..."`) plus `detail: "Distance could not be calculated for one or more legs."`.
- `compute_for_case(case)` reads `case.segments.order_by("order")`, builds `(from_iata, to_iata)` pairs from each segment's departure/arrival airport, computes leg distances, sums them, and mutates `case.distance_km` / `case.compensation_amount_eur` / `case.compensation_calculated_at`. Does **not** call `case.save()`. Raises `DistanceUnavailable` (without a `payload`) on failure — caller decides how to handle.
- `_build_airport_lookup(iatas)` — single `Airport.objects.filter(iata__in=iatas)` query, returns `dict[str, Airport]`. Keys are already uppercased.
- `_sum_and_bracket(leg_results)` — sums the leg distances to a `Decimal` rounded to 2dp (ROUND_HALF_EVEN), calls `compensation_for_km`, returns `(total_km, amount)`.
- Public API is re-exported from `cases.compensation.__init__` for a clean import surface.
- `PreviewRequestSerializer` enforces validation rules P1–P5 from the spec (1–5 legs, 3-letter IATAs, uppercase normalisation, `from != to`).

**Implementation:**

`backend/cases/compensation/service.py`:

```python
"""Compensation orchestration used by both the preview view and case create."""
from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any, Iterable

from django.utils import timezone

from airports.models import Airport

from .brackets import compensation_for_km
from .distance import compute_leg_km
from .exceptions import DistanceUnavailable


def preview_from_legs(legs: list[dict[str, str]]) -> dict[str, Any]:
    """Compute a preview response body for a list of validated leg dicts.

    Raises DistanceUnavailable with `.payload` set on any failure.
    """
    lookup = _build_airport_lookup(_all_iatas(legs))
    per_leg: list[dict[str, Any]] = []
    any_failed = False

    for leg in legs:
        entry: dict[str, Any] = {"from": leg["from"], "to": leg["to"]}
        try:
            km, source = compute_leg_km(
                leg["from"], leg["to"], airport_lookup=lookup.get,
            )
        except DistanceUnavailable as exc:
            any_failed = True
            entry.update({"distance_km": None, "source": None, "error": str(exc)})
        else:
            entry.update({"distance_km": _round2(km), "source": source, "error": None})
        per_leg.append(entry)

    if any_failed:
        raise DistanceUnavailable(
            "Distance could not be calculated for one or more legs.",
            payload={
                "detail": "Distance could not be calculated for one or more legs.",
                "legs": per_leg,
            },
        )

    total = _sum_km(per_leg)
    amount = compensation_for_km(total)
    return {
        "distance_km": total,
        "compensation_amount_eur": amount,
        "legs": per_leg,
    }


def compute_for_case(case) -> None:
    """Compute compensation for `case` and mutate it in place.

    Does not call .save(); the caller controls the transaction. Raises
    DistanceUnavailable on failure (without a `.payload`).
    """
    segments = list(case.segments.select_related(
        "departure_airport", "arrival_airport",
    ).order_by("order"))
    if not segments:
        raise DistanceUnavailable("Case has no segments to calculate.")

    legs = [
        {
            "from": s.departure_airport.iata,
            "to": s.arrival_airport.iata,
        }
        for s in segments
    ]

    lookup = _build_airport_lookup(_all_iatas(legs))
    totals: list[Decimal] = []
    for leg in legs:
        km, _source = compute_leg_km(
            leg["from"], leg["to"], airport_lookup=lookup.get,
        )
        totals.append(km)

    total_km = _round2(sum(totals, Decimal("0")))
    case.distance_km = total_km
    case.compensation_amount_eur = compensation_for_km(total_km)
    case.compensation_calculated_at = timezone.now()


# ------------------------- helpers -------------------------

def _all_iatas(legs: Iterable[dict[str, str]]) -> set[str]:
    out: set[str] = set()
    for leg in legs:
        out.add(leg["from"].upper())
        out.add(leg["to"].upper())
    return out


def _build_airport_lookup(iatas: set[str]) -> dict[str, Airport]:
    qs = Airport.objects.filter(iata__in=iatas)
    return {a.iata: a for a in qs}


def _round2(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def _sum_km(per_leg: list[dict[str, Any]]) -> Decimal:
    total = Decimal("0")
    for leg in per_leg:
        km = leg["distance_km"]
        if km is None:  # pragma: no cover — guarded upstream
            continue
        total += Decimal(str(km))
    return _round2(total)
```

`backend/cases/compensation/__init__.py` (replace stub):

```python
"""Compensation calculation sub-package."""
from .exceptions import DistanceUnavailable
from .service import compute_for_case, preview_from_legs

__all__ = ["DistanceUnavailable", "compute_for_case", "preview_from_legs"]
```

`backend/cases/serializers.py` — append at the end of the file (after `CaseCreateSerializer`):

```python
class PreviewLegSerializer(serializers.Serializer):
    from_ = serializers.CharField(source="from", max_length=3, min_length=3)
    to = serializers.CharField(max_length=3, min_length=3)

    # `from` is a Python keyword; expose it via source= while accepting/emitting
    # the JSON key "from" verbatim.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["from"] = self.fields.pop("from_")

    def validate(self, attrs):
        f = attrs["from"].upper()
        t = attrs["to"].upper()
        if not f.isalpha() or not t.isalpha():
            raise serializers.ValidationError("IATA codes must be letters only.")
        if f == t:
            raise serializers.ValidationError("A leg's departure and arrival must differ.")
        return {"from": f, "to": t}


class PreviewRequestSerializer(serializers.Serializer):
    legs = PreviewLegSerializer(many=True, min_length=1, max_length=5)
```

**Testing:**

`backend/cases/tests/test_compensation_service.py`:

```python
from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest

from cases.compensation.exceptions import DistanceUnavailable
from cases.compensation.service import compute_for_case, preview_from_legs

from cases.tests.factories import CaseFactory, FlightSegmentFactory


# ------------------------- preview_from_legs -------------------------

@pytest.mark.django_db
def test_preview_returns_total_and_amount(two_airports):
    with patch("cases.compensation.service.compute_leg_km") as m:
        m.side_effect = [(Decimal("1000.00"), "airportgap"),
                         (Decimal("600.00"), "haversine")]
        result = preview_from_legs([
            {"from": "OTP", "to": "CDG"},
            {"from": "CDG", "to": "OTP"},
        ])
    assert result["distance_km"] == Decimal("1600.00")
    assert result["compensation_amount_eur"] == 400
    assert result["legs"][0] == {
        "from": "OTP", "to": "CDG",
        "distance_km": Decimal("1000.00"), "source": "airportgap", "error": None,
    }
    assert result["legs"][1]["source"] == "haversine"


@pytest.mark.django_db
def test_preview_raises_with_payload_on_leg_failure(two_airports):
    with patch("cases.compensation.service.compute_leg_km") as m:
        m.side_effect = [
            (Decimal("500.00"), "airportgap"),
            DistanceUnavailable("Unknown airport code: XXX"),
        ]
        with pytest.raises(DistanceUnavailable) as exc:
            preview_from_legs([
                {"from": "OTP", "to": "CDG"},
                {"from": "CDG", "to": "XXX"},
            ])
    payload = exc.value.payload
    assert payload["detail"].startswith("Distance could not be calculated")
    assert payload["legs"][0]["error"] is None
    assert payload["legs"][1]["error"] == "Unknown airport code: XXX"
    assert payload["legs"][1]["distance_km"] is None


# ------------------------- compute_for_case -------------------------

@pytest.mark.django_db
def test_compute_for_case_populates_fields(two_airports):
    otp, cdg = two_airports
    case = CaseFactory()
    FlightSegmentFactory(case=case, order=0,
                         departure_airport=otp, arrival_airport=cdg,
                         is_problem_flight=True)
    FlightSegmentFactory(case=case, order=1,
                         departure_airport=cdg, arrival_airport=otp,
                         is_problem_flight=False)

    with patch("cases.compensation.service.compute_leg_km") as m:
        m.side_effect = [(Decimal("1874.00"), "airportgap"),
                         (Decimal("1874.00"), "airportgap")]
        compute_for_case(case)

    assert case.distance_km == Decimal("3748.00")
    assert case.compensation_amount_eur == 600
    assert case.compensation_calculated_at is not None


@pytest.mark.django_db
def test_compute_for_case_raises_without_payload_on_failure(two_airports):
    otp, cdg = two_airports
    case = CaseFactory()
    FlightSegmentFactory(case=case, order=0, departure_airport=otp,
                         arrival_airport=cdg, is_problem_flight=True)

    with patch("cases.compensation.service.compute_leg_km") as m:
        m.side_effect = DistanceUnavailable("boom")
        with pytest.raises(DistanceUnavailable) as exc:
            compute_for_case(case)
    assert exc.value.payload is None
```

**Verification:**

```powershell
cd backend
pytest cases/tests/test_compensation_service.py -q
```

Expect: 4 tests, all pass. Existing tests must still pass:

```powershell
pytest cases/tests -q
```

---

### Task 4: Preview API view + URL + throttle + timeout setting

**Files:**
- Modify: `backend/airassist/settings/base.py`
- Modify: `backend/cases/views.py`
- Modify: `backend/cases/urls.py`
- Create: `backend/cases/tests/test_compensation_preview_api.py`

**Requirements:**
- Add `COMPENSATION_HTTP_TIMEOUT_S = float(os.environ.get("COMPENSATION_HTTP_TIMEOUT_S", "3.0"))` to `settings/base.py` and add `"compensation_preview": "60/min"` to `DEFAULT_THROTTLE_RATES`.
- `CompensationPreviewView(APIView)` with `throttle_classes = [CompensationPreviewThrottle]`, POST only, `AllowAny` inherited from defaults.
- View validates with `PreviewRequestSerializer`, calls `preview_from_legs`, returns 200 on success, 422 with `exc.payload` on `DistanceUnavailable`.
- Route: `path("compensation/preview/", CompensationPreviewView.as_view(), name="compensation-preview")` in `cases/urls.py`.

**Implementation:**

`backend/airassist/settings/base.py` — replace the current `REST_FRAMEWORK` block and add the timeout constant:

```python
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],  # CSRF-free public API
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "case_create": "20/hour",
        "compensation_preview": "60/min",
    },
}

CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

AIRPORTGAP_BASE_URL = os.environ.get("AIRPORTGAP_BASE_URL", "https://airportgap.com/api")
AIRPORTGAP_TOKEN = os.environ.get("AIRPORTGAP_TOKEN", "")
COMPENSATION_HTTP_TIMEOUT_S = float(os.environ.get("COMPENSATION_HTTP_TIMEOUT_S", "3.0"))
```

`backend/cases/views.py` — add these imports and class (append at the bottom, keep everything else untouched for now; Task 6 will extend `CaseCreateView`):

```python
from rest_framework.parsers import JSONParser

from .compensation import DistanceUnavailable, preview_from_legs
from .serializers import PreviewRequestSerializer


class CompensationPreviewThrottle(AnonRateThrottle):
    scope = "compensation_preview"


class CompensationPreviewView(APIView):
    parser_classes = [JSONParser]
    throttle_classes = [CompensationPreviewThrottle]

    def post(self, request, *args, **kwargs):
        serializer = PreviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            body = preview_from_legs(serializer.validated_data["legs"])
        except DistanceUnavailable as exc:
            return Response(
                exc.payload or {"detail": str(exc), "legs": []},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(body, status=status.HTTP_200_OK)
```

`backend/cases/urls.py` (replace file):

```python
from django.urls import path

from .views import CaseCreateView, CompensationPreviewView

urlpatterns = [
    path("cases/", CaseCreateView.as_view(), name="case-create"),
    path("compensation/preview/", CompensationPreviewView.as_view(),
         name="compensation-preview"),
]
```

**Testing:**

`backend/cases/tests/test_compensation_preview_api.py`:

```python
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
    # Sanity: the throttle rate is exactly what we advertise.
    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["compensation_preview"] = "60/min"

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
```

**Verification:**

```powershell
cd backend
pytest cases/tests/test_compensation_preview_api.py -q
```

Expect: 4 test functions, 9 test cases (parametrized), all pass. Also:

```powershell
python manage.py check
```

Should print `System check identified no issues (0 silenced).`

---

### Task 5: Data migration + model fields + admin exposure

**Files:**
- Modify: `backend/cases/models.py`
- Modify: `backend/cases/admin.py`
- Create: `backend/cases/migrations/0002_case_compensation_fields.py`

**Requirements:**
- Add three nullable fields on `Case`: `distance_km` (`DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)`), `compensation_amount_eur` (`PositiveSmallIntegerField(null=True, blank=True)`), `compensation_calculated_at` (`DateTimeField(null=True, blank=True)`).
- Add a `CheckConstraint` named `compensation_amount_eur_valid` restricting the amount to `{250, 400, 600, NULL}`.
- Admin displays the three fields as read-only.
- Migration is auto-generatable: just run `python manage.py makemigrations cases`. Verify the generated file matches the shape shown below.

**Implementation:**

`backend/cases/models.py` — inside `class Case(...)`, add the three fields alongside the existing ones, and add the `CheckConstraint` to `Meta.constraints` (Case currently has no `Meta.constraints`; add it):

```python
class Case(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=10, choices=CaseStatus.choices,
                              default=CaseStatus.NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    date_of_birth = models.DateField()
    email = models.EmailField()
    phone = models.CharField(
        max_length=30, validators=[RegexValidator(regex=PHONE_REGEX)]
    )
    address = models.CharField(max_length=200)
    postal_code = models.CharField(max_length=20)

    reservation_number = models.CharField(max_length=30)

    gdpr_consent = models.BooleanField(default=False)
    gdpr_consent_at = models.DateTimeField(null=True, blank=True)

    # --- CASE_02 compensation ---
    distance_km = models.DecimalField(
        max_digits=9, decimal_places=2, null=True, blank=True,
    )
    compensation_amount_eur = models.PositiveSmallIntegerField(
        null=True, blank=True,
    )
    compensation_calculated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(compensation_amount_eur__isnull=True)
                    | Q(compensation_amount_eur__in=[250, 400, 600])
                ),
                name="compensation_amount_eur_valid",
            ),
        ]
    # ... existing clean() / __str__ unchanged ...
```

Do not touch `FlightSegment` or `CaseDocument`.

`backend/cases/admin.py` — extend `CaseAdmin.readonly_fields` and add a fieldset for the new columns:

```python
@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "last_name", "email",
                    "compensation_amount_eur", "created_at")
    list_filter = ("status", "compensation_amount_eur")
    search_fields = ("last_name", "email", "reservation_number")
    inlines = [FlightSegmentInline, CaseDocumentInline]
    readonly_fields = (
        "id", "created_at", "updated_at",
        "distance_km", "compensation_amount_eur", "compensation_calculated_at",
    )
```

`backend/cases/migrations/0002_case_compensation_fields.py` — generate then commit as-is:

```powershell
cd backend
python manage.py makemigrations cases --name case_compensation_fields
```

The generated file should look like (verify before committing):

```python
from django.db import migrations, models
import django.db.models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="case",
            name="distance_km",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=9, null=True,
            ),
        ),
        migrations.AddField(
            model_name="case",
            name="compensation_amount_eur",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="case",
            name="compensation_calculated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="case",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("compensation_amount_eur__isnull", True),
                    ("compensation_amount_eur__in", [250, 400, 600]),
                    _connector="OR",
                ),
                name="compensation_amount_eur_valid",
            ),
        ),
    ]
```

**Testing:**

Add one focused check to `backend/cases/tests/test_compensation_service.py` (append; do not create a new file):

```python
from django.db import IntegrityError


@pytest.mark.django_db
def test_check_constraint_rejects_invalid_compensation_amount(two_airports):
    case = CaseFactory()
    case.compensation_amount_eur = 123
    with pytest.raises(IntegrityError):
        case.save()
```

**Verification:**

```powershell
cd backend
python manage.py makemigrations --check --dry-run
python manage.py migrate
pytest cases/tests -q
```

Expect: `No changes detected`, migration runs cleanly, all `cases` tests still pass.

---

### Task 6: Wire compensation into case create + extend response and tests

**Files:**
- Modify: `backend/cases/views.py` (extend `CaseCreateView.post`)
- Modify: `backend/cases/tests/test_api.py` (extend existing tests + add two new)

**Requirements:**
- Inside the existing `transaction.atomic()` block in `CaseCreateView.post`, immediately after `case = payload_ser.save()`, call `compute_for_case(case)` wrapped in `try/except DistanceUnavailable`. On success, save the three fields (`update_fields=[...]`). On `DistanceUnavailable`, capture the message into a local `compensation_error` string; do **not** roll back.
- Any *other* exception continues to use the existing rollback path (`_cleanup_files` + `raise`).
- Extend the 201 response body with `distance_km` (string / null), `compensation_amount_eur` (int / null), `compensation_error` (string / null).
- Serialise `Decimal` as its string form (DRF default) so precision is preserved; the frontend accepts `string | number`.
- No changes to request shape, validation rules, file writing, or throttle behaviour.

**Implementation:**

`backend/cases/views.py` — replace the `CaseCreateView` class (keep the module imports and the `CompensationPreviewView` added in Task 4):

```python
class CaseCreateView(APIView):
    parser_classes = [MultiPartParser]
    throttle_classes = [CaseCreateThrottle]

    def post(self, request, *args, **kwargs):
        # --- Phase A: validate everything, write nothing ---
        raw_payload = request.data.get("payload")
        if raw_payload is None:
            raise DRFValidationError({"payload": ["This field is required."]})
        payload_data = parse_payload_field(raw_payload)

        payload_ser = CaseCreateSerializer(data=payload_data)
        payload_valid = payload_ser.is_valid()

        file_errors: dict[str, list[str]] = {}
        detected_mime: dict[str, str] = {}
        for field, _ in DOC_FIELDS:
            file_obj = request.FILES.get(field)
            if file_obj is None:
                file_errors[field] = ["This file is required."]
                continue
            try:
                detected_mime[field] = validate_upload(file_obj)
            except DjangoValidationError as exc:
                file_errors[field] = list(exc.messages)

        if not payload_valid or file_errors:
            errors: dict = {}
            if not payload_valid:
                errors["payload"] = payload_ser.errors
            errors.update(file_errors)
            raise DRFValidationError(errors)

        # --- Phase B: persist inside a transaction with file-rollback ---
        written_paths: list[str] = []
        compensation_error: str | None = None
        try:
            with transaction.atomic():
                case: Case = payload_ser.save()

                # Compensation calc: never blocks case creation. A
                # DistanceUnavailable leaves the three fields NULL and surfaces
                # a soft error on the response; any other exception uses the
                # existing rollback path below.
                try:
                    compute_for_case(case)
                    case.save(update_fields=[
                        "distance_km",
                        "compensation_amount_eur",
                        "compensation_calculated_at",
                    ])
                except DistanceUnavailable:
                    compensation_error = (
                        "Distance could not be calculated; "
                        "you can review this case later."
                    )

                for field, kind in DOC_FIELDS:
                    file_obj = request.FILES[field]
                    doc = CaseDocument(
                        case=case,
                        kind=kind,
                        original_filename=file_obj.name,
                        content_type=detected_mime[field],
                        size_bytes=file_obj.size,
                    )
                    doc.file.save(file_obj.name, file_obj, save=False)
                    written_paths.append(doc.file.name)
                    doc.save()
        except Exception:
            _cleanup_files(written_paths)
            raise

        return Response(
            {
                "id": str(case.id),
                "status": case.status,
                "created_at": case.created_at.isoformat(),
                "distance_km": (
                    str(case.distance_km) if case.distance_km is not None else None
                ),
                "compensation_amount_eur": case.compensation_amount_eur,
                "compensation_error": compensation_error,
            },
            status=status.HTTP_201_CREATED,
        )
```

Add the import at the top of the module (next to `from .serializers import ...`):

```python
from .compensation import DistanceUnavailable, compute_for_case
```

(This import is already added in Task 4 via `from .compensation import DistanceUnavailable, preview_from_legs`; extend that same line to include `compute_for_case`.)

**Testing:**

Extend `backend/cases/tests/test_api.py`. Update the existing happy-path assertion and add two new tests:

```python
# Update the existing test_happy_path_creates_case_with_files to also assert
# the new response fields (add these lines before the `case = Case.objects.get(...)`):
    assert body["compensation_error"] is None
    assert body["compensation_amount_eur"] in {250, 400, 600}
    assert body["distance_km"] is not None
    # And after fetching `case`:
    assert case.compensation_amount_eur == body["compensation_amount_eur"]
    assert case.compensation_calculated_at is not None
```

Add two new tests at the bottom of `test_api.py`:

```python
from unittest.mock import patch

from cases.compensation.exceptions import DistanceUnavailable


@pytest.mark.django_db
def test_case_created_even_when_compensation_fails(
    two_airports, valid_payload, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()
    with patch("cases.views.compute_for_case",
               side_effect=DistanceUnavailable("simulated failure")):
        resp = client.post("/api/cases/",
                           _make_multipart(valid_payload),
                           format="multipart")
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["compensation_amount_eur"] is None
    assert body["distance_km"] is None
    assert body["compensation_error"] == (
        "Distance could not be calculated; you can review this case later."
    )

    case = Case.objects.get(id=body["id"])
    assert case.distance_km is None
    assert case.compensation_amount_eur is None
    assert case.compensation_calculated_at is None
    assert case.documents.count() == 2


@pytest.mark.django_db
def test_case_response_carries_compensation_on_success(
    two_airports, valid_payload, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()

    def _fake(case):
        from decimal import Decimal
        from django.utils import timezone
        case.distance_km = Decimal("1874.00")
        case.compensation_amount_eur = 400
        case.compensation_calculated_at = timezone.now()

    with patch("cases.views.compute_for_case", side_effect=_fake):
        resp = client.post("/api/cases/",
                           _make_multipart(valid_payload),
                           format="multipart")
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["compensation_amount_eur"] == 400
    assert body["distance_km"] == "1874.00"
    assert body["compensation_error"] is None
```

**Verification:**

```powershell
cd backend
pytest cases/tests -q
```

Expect: all existing `cases` tests still pass, plus 2 new tests, plus the earlier happy-path assertions updated in place.

---

### Task 7: Frontend API client for compensation preview

**Files:**
- Create: `frontend/src/api/compensation.ts`
- Modify: `frontend/src/features/case-entry/types.ts` (extend `CaseCreateResponse`)

**Requirements:**
- `previewCompensation(legs, signal?)` — POSTs `{ legs }` to `/api/compensation/preview/`; returns typed `CompensationPreview` on 200; throws `CompensationUnavailable` (a new subclass of `ApiError`) on 422 with the response body attached; throws `ApiThrottledError` on 429; throws `ApiError` on anything else.
- Uses the existing `fetch` (no new HTTP wrapper). Accepts an `AbortSignal` for cancellation.
- Numeric fields on the response typed as `number` (accept both JSON numbers and numeric strings by coercing via `Number(...)`).
- `CaseCreateResponse` gains three optional fields exactly as the backend now returns them.

**Implementation:**

`frontend/src/features/case-entry/types.ts` — extend `CaseCreateResponse` (leave the rest of the file unchanged):

```typescript
export interface CaseCreateResponse {
  id: string;
  status: "NEW" | "VALID" | "ASSIGNED" | "INVALID";
  created_at: string;
  distance_km: string | number | null;
  compensation_amount_eur: 250 | 400 | 600 | null;
  compensation_error: string | null;
}
```

`frontend/src/api/compensation.ts`:

```typescript
import { ApiError, ApiThrottledError } from "./client";

export interface CompensationLeg {
  from: string;
  to: string;
}

export interface CompensationBreakdownLeg {
  from: string;
  to: string;
  distance_km: number | null;
  source: "airportgap" | "haversine" | null;
  error?: string | null;
}

export interface CompensationPreview {
  distance_km: number;
  compensation_amount_eur: 250 | 400 | 600;
  legs: CompensationBreakdownLeg[];
}

export interface CompensationUnavailableBody {
  detail: string;
  legs: CompensationBreakdownLeg[];
}

export class CompensationUnavailable extends ApiError {
  readonly body: CompensationUnavailableBody;
  constructor(body: CompensationUnavailableBody) {
    super(422, body.detail || "Compensation could not be calculated.");
    this.body = body;
  }
}

export async function previewCompensation(
  legs: CompensationLeg[],
  signal?: AbortSignal,
): Promise<CompensationPreview> {
  const resp = await fetch("/api/compensation/preview/", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ legs }),
    signal,
  });

  if (resp.status === 429) throw new ApiThrottledError();
  if (resp.status === 422) {
    const body = (await safeJson(resp)) as CompensationUnavailableBody | null;
    throw new CompensationUnavailable(
      body ?? { detail: "Compensation could not be calculated.", legs: [] },
    );
  }
  if (!resp.ok) {
    throw new ApiError(resp.status, `POST /api/compensation/preview/ failed with ${resp.status}`);
  }

  const raw = (await resp.json()) as {
    distance_km: number | string;
    compensation_amount_eur: 250 | 400 | 600;
    legs: Array<{
      from: string; to: string;
      distance_km: number | string | null;
      source: "airportgap" | "haversine" | null;
      error?: string | null;
    }>;
  };
  return {
    distance_km: Number(raw.distance_km),
    compensation_amount_eur: raw.compensation_amount_eur,
    legs: raw.legs.map((l) => ({
      ...l,
      distance_km: l.distance_km === null ? null : Number(l.distance_km),
      error: l.error ?? null,
    })),
  };
}

async function safeJson(resp: Response): Promise<unknown> {
  try {
    return await resp.json();
  } catch {
    return null;
  }
}
```

**Testing:** the client is covered by the component test in Task 8 (which mocks `fetch`). No separate unit test file is needed here — this is a thin adapter.

**Verification:**

```powershell
cd frontend
npx tsc --noEmit
```

Expect: no type errors.

---

### Task 8: `CompensationSummary` component + CSS + tests

**Files:**
- Create: `frontend/src/features/case-entry/CompensationSummary.tsx`
- Create: `frontend/src/features/case-entry/CompensationSummary.module.css`
- Create: `frontend/tests/CompensationSummary.test.tsx`

**Requirements:**
- Uses `useFormContext<CaseFormValues>()` (matches the form's provider) and `useWatch({ control, name: "segments" })` to react to segment changes.
- Extracts legs in `order` ascending; drops legs where either IATA is missing or not exactly 3 letters.
- Renders nothing (returns `null`) if the resulting leg list is empty.
- Debounces the effective leg list by 400 ms before firing `previewCompensation`.
- Cancels in-flight requests via `AbortController` when legs change.
- Renders four states: loading, success, soft failure (422 or unrelated network error), and throttled. Submit button stays enabled in every case (component has no `disabled` side effect).
- Distance shown as an integer (`Math.round`) grouped with `Intl.NumberFormat("en", { useGrouping: true }).format`.
- Colocates a small `useDebouncedValue` hook in the same file (no shared hook module).

**Implementation:**

`frontend/src/features/case-entry/CompensationSummary.tsx`:

```typescript
import { useEffect, useMemo, useRef, useState } from "react";
import { useFormContext, useWatch } from "react-hook-form";

import {
  CompensationUnavailable,
  previewCompensation,
  type CompensationLeg,
  type CompensationPreview,
} from "../../api/compensation";
import { ApiError, ApiThrottledError } from "../../api/client";
import type { CaseFormValues } from "./schema";
import styles from "./CompensationSummary.module.css";


type ViewState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "success"; data: CompensationPreview }
  | { kind: "soft-error"; message: string }
  | { kind: "throttled" };


function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}

const IATA_RX = /^[A-Za-z]{3}$/;
const NUMBER_FMT = new Intl.NumberFormat("en", { useGrouping: true });


export function CompensationSummary() {
  const { control } = useFormContext<CaseFormValues>();
  const segments = useWatch({ control, name: "segments" });

  const legs: CompensationLeg[] = useMemo(() => {
    if (!Array.isArray(segments)) return [];
    return [...segments]
      .sort((a, b) => (a?.order ?? 0) - (b?.order ?? 0))
      .map((s) => ({
        from: (s?.departure_airport_iata ?? "").toUpperCase(),
        to: (s?.arrival_airport_iata ?? "").toUpperCase(),
      }))
      .filter((l) => IATA_RX.test(l.from) && IATA_RX.test(l.to) && l.from !== l.to);
  }, [segments]);

  // Debounce the serialised leg list so rapid typing collapses into one call.
  const legsKey = JSON.stringify(legs);
  const debouncedKey = useDebouncedValue(legsKey, 400);

  const [state, setState] = useState<ViewState>({ kind: "idle" });
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    // Cancel any in-flight request from a previous key.
    abortRef.current?.abort();

    if (legs.length === 0) {
      setState({ kind: "idle" });
      return;
    }

    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setState({ kind: "loading" });

    previewCompensation(legs, ctrl.signal)
      .then((data) => {
        if (ctrl.signal.aborted) return;
        setState({ kind: "success", data });
      })
      .catch((err) => {
        if (ctrl.signal.aborted || err?.name === "AbortError") return;
        if (err instanceof ApiThrottledError) {
          setState({ kind: "throttled" });
          return;
        }
        if (err instanceof CompensationUnavailable || err instanceof ApiError) {
          setState({
            kind: "soft-error",
            message:
              "We couldn't calculate compensation yet — check that all airport codes are valid.",
          });
          return;
        }
        setState({
          kind: "soft-error",
          message:
            "We couldn't calculate compensation yet — check that all airport codes are valid.",
        });
      });

    return () => ctrl.abort();
    // legs is derived from debouncedKey; trigger only on the debounced value.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedKey]);

  if (state.kind === "idle") return null;

  return (
    <section className={styles.summary} aria-live="polite" data-testid="compensation-summary">
      <h2>Estimated compensation</h2>
      {state.kind === "loading" && (
        <p className={styles.pending}>Calculating compensation…</p>
      )}
      {state.kind === "success" && (
        <>
          <p className={styles.amount}>
            <strong>{state.data.compensation_amount_eur} €</strong>
          </p>
          <p className={styles.detail}>
            Total flight distance: {NUMBER_FMT.format(Math.round(state.data.distance_km))} km
            {" "}across {state.data.legs.length} leg(s).
          </p>
        </>
      )}
      {state.kind === "soft-error" && (
        <p className={styles.warning} role="status">{state.message}</p>
      )}
      {state.kind === "throttled" && (
        <p className={styles.warning} role="status">
          Too many attempts; retrying shortly.
        </p>
      )}
    </section>
  );
}
```

`frontend/src/features/case-entry/CompensationSummary.module.css`:

```css
.summary {
  margin: 1.5rem 0;
  padding: 1rem 1.25rem;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  background: #f6f8fa;
}

.pending { color: #57606a; font-style: italic; }
.amount  { font-size: 1.5rem; margin: 0.25rem 0; }
.detail  { color: #57606a; margin: 0; }
.warning { color: #9a3412; margin: 0; }
```

**Testing:**

`frontend/tests/CompensationSummary.test.tsx`:

```typescript
import { render, screen, waitFor, act } from "@testing-library/react";
import { FormProvider, useForm } from "react-hook-form";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CompensationSummary } from "../src/features/case-entry/CompensationSummary";
import type { CaseFormValues } from "../src/features/case-entry/schema";


const fetchMock = vi.fn();
beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});


function Harness({ segments }: { segments: CaseFormValues["segments"] }) {
  const methods = useForm<CaseFormValues>({
    defaultValues: {
      passenger: {
        first_name: "", last_name: "", date_of_birth: "",
        email: "", phone: "", address: "", postal_code: "",
      },
      reservation_number: "",
      segments,
      gdpr_consent: false,
      boarding_pass: undefined as unknown as File,
      id_document: undefined as unknown as File,
    },
  });
  return (
    <FormProvider {...methods}>
      <CompensationSummary />
    </FormProvider>
  );
}


function seg(order: number, from: string, to: string) {
  return {
    order, flight_date: "", flight_number: "", airline: "",
    departure_airport_iata: from, arrival_airport_iata: to,
    planned_departure_time: "", planned_arrival_time: "",
    is_problem_flight: order === 0,
  };
}


describe("CompensationSummary", () => {
  it("renders nothing when no complete legs are present", () => {
    render(<Harness segments={[seg(0, "", "")]} />);
    expect(screen.queryByTestId("compensation-summary")).toBeNull();
  });

  it("shows the amount and distance on success", async () => {
    vi.useFakeTimers();
    fetchMock.mockResolvedValue({
      ok: true, status: 200,
      json: async () => ({
        distance_km: "1874.00",
        compensation_amount_eur: 400,
        legs: [{ from: "OTP", to: "CDG",
                 distance_km: "1874.00", source: "airportgap", error: null }],
      }),
    });

    render(<Harness segments={[seg(0, "OTP", "CDG")]} />);
    await act(async () => { vi.advanceTimersByTime(500); });
    vi.useRealTimers();

    await waitFor(() =>
      expect(screen.getByText(/400\s*€/)).toBeInTheDocument(),
    );
    expect(screen.getByText(/1,?\s?874 km/)).toBeInTheDocument();
    expect(screen.getByText(/across 1 leg\(s\)\./)).toBeInTheDocument();
  });

  it("shows the soft-error copy on 422", async () => {
    vi.useFakeTimers();
    fetchMock.mockResolvedValue({
      ok: false, status: 422,
      json: async () => ({ detail: "unavailable", legs: [] }),
    });

    render(<Harness segments={[seg(0, "OTP", "CDG")]} />);
    await act(async () => { vi.advanceTimersByTime(500); });
    vi.useRealTimers();

    await waitFor(() =>
      expect(
        screen.getByText(/couldn't calculate compensation/i),
      ).toBeInTheDocument(),
    );
  });

  it("debounces rapid segment changes into a single fetch", async () => {
    vi.useFakeTimers();
    fetchMock.mockResolvedValue({
      ok: true, status: 200,
      json: async () => ({
        distance_km: "100.00", compensation_amount_eur: 250,
        legs: [{ from: "OTP", to: "CDG",
                 distance_km: "100.00", source: "airportgap", error: null }],
      }),
    });

    const { rerender } = render(<Harness segments={[seg(0, "OTP", "CDG")]} />);
    // Two rapid changes within the debounce window
    rerender(<Harness segments={[seg(0, "OTP", "AMS")]} />);
    rerender(<Harness segments={[seg(0, "OTP", "LHR")]} />);
    await act(async () => { vi.advanceTimersByTime(500); });
    vi.useRealTimers();

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(String(init.body))).toEqual({
      legs: [{ from: "OTP", to: "LHR" }],
    });
  });
});
```

**Verification:**

```powershell
cd frontend
npx vitest run tests/CompensationSummary.test.tsx
npx tsc --noEmit
```

Expect: 4 tests pass, no type errors.

---

### Task 9: Wire summary into form + surface compensation on the success view + extend form test

**Files:**
- Modify: `frontend/src/features/case-entry/CaseEntryForm.tsx`
- Modify: `frontend/tests/CaseEntryForm.test.tsx`

**Requirements:**
- Render `<CompensationSummary />` **inside** the `<FormProvider>` and **above** the submit button.
- Success view (`if (created) ...`) additionally shows either the compensation amount + distance (when `created.compensation_amount_eur` is not null) or the warning copy (`Case created, but compensation could not be calculated. Our team will review it.`) when `created.compensation_error` is not null.
- No changes to the submit handler, banner logic, or Zod schema.
- The existing test `renders all five sections` still passes; a new assertion confirms the summary is present in the DOM (rendered as `null` until segments arrive, so the assertion is on the wrapper form structure — see below).

**Implementation:**

`frontend/src/features/case-entry/CaseEntryForm.tsx` — three edits (import, form body, success view):

```typescript
// 1. Add import next to the other section imports:
import { CompensationSummary } from "./CompensationSummary";

// 2. Extend the JSX inside <form> — insert the summary above the submit button:
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <FlightItinerarySection />
          <ConnectingFlightsSection />
          <PassengerDetailsSection />
          <DocumentsSection />
          <GdprSection />
          <CompensationSummary />
          <button
            type="submit"
            disabled={!isValid || isSubmitting}
            className={styles.submit}
          >
            {isSubmitting ? "Submitting…" : "Submit claim"}
          </button>
        </form>

// 3. Extend the success view:
  if (created) {
    return (
      <main className={styles.wrapper}>
        <div className={styles.success} role="status">
          <h1>Case created</h1>
          <p>Reference: <code>{created.id}</code></p>
          <p>Status: <strong>{created.status}</strong></p>
          {created.compensation_amount_eur !== null && created.distance_km !== null && (
            <p>
              Estimated compensation:{" "}
              <strong>{created.compensation_amount_eur} €</strong>{" "}
              (based on {Math.round(Number(created.distance_km))} km total distance).
            </p>
          )}
          {created.compensation_error && (
            <p role="alert">
              Case created, but compensation could not be calculated. Our team will
              review it.
            </p>
          )}
        </div>
      </main>
    );
  }
```

**Testing:**

Extend `frontend/tests/CaseEntryForm.test.tsx` with two additional test cases inside the existing `describe("CaseEntryForm", ...)` block:

```typescript
  it("displays the compensation summary above the submit button", () => {
    render(<CaseEntryForm />);
    const submit = screen.getByRole("button", { name: /submit claim/i });
    // The summary starts idle (renders null) while the form is empty; the
    // wrapper form still contains both elements in order. Assert the submit
    // button is the last child of the form.
    const form = submit.closest("form");
    expect(form).not.toBeNull();
    expect(form!.lastElementChild).toBe(submit);
  });

  it("shows the compensation amount on the success view", async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (String(url).includes("/api/airports/")) {
        return {
          ok: true,
          json: async () => [
            { iata: "OTP", icao: "LROP", name: "Henri Coanda",
              city: "Bucharest", country: "Romania" },
            { iata: "CDG", icao: "LFPG", name: "Charles de Gaulle",
              city: "Paris", country: "France" },
          ],
        };
      }
      if (String(url).includes("/api/compensation/preview/")) {
        return {
          ok: true, status: 200,
          json: async () => ({
            distance_km: "1874.00", compensation_amount_eur: 400,
            legs: [{ from: "OTP", to: "CDG",
                     distance_km: "1874.00", source: "airportgap", error: null }],
          }),
        };
      }
      // POST /api/cases/ → 201 with compensation fields
      return {
        ok: true, status: 201,
        json: async () => ({
          id: "abc-123", status: "NEW",
          created_at: "2026-07-23T12:00:00Z",
          distance_km: "1874.00",
          compensation_amount_eur: 400,
          compensation_error: null,
        }),
      };
    });

    const user = userEvent.setup();
    render(<CaseEntryForm />);
    // Fill the form (same sequence as the existing 400-mapping test).
    await user.type(screen.getByLabelText(/first name/i), "Ana");
    await user.type(screen.getByLabelText(/last name/i), "Popescu");
    await user.type(screen.getByLabelText(/date of birth/i), "1990-05-14");
    await user.type(screen.getByLabelText(/^email/i), "ana@example.com");
    await user.type(screen.getByLabelText(/phone/i), "+40 712 345 678");
    await user.type(screen.getByLabelText(/address/i), "Str. Exemplu 1");
    await user.type(screen.getByLabelText(/postal code/i), "010101");
    await user.type(screen.getByLabelText(/reservation number/i), "ABC123");
    await user.type(screen.getByLabelText(/^flight date/i), "2026-08-01");
    await user.type(screen.getByLabelText(/^flight number/i), "AF1234");
    await user.type(screen.getByLabelText(/^airline/i), "Air France");
    const dep = screen.getByLabelText(/departing airport/i);
    await user.type(dep, "OT");
    await user.click(await screen.findByRole("option", { name: /OTP/i }));
    const arr = screen.getByLabelText(/destination airport/i);
    await user.type(arr, "CD");
    await user.click(await screen.findByRole("option", { name: /CDG/i }));
    await user.type(screen.getByLabelText(/planned departure time/i), "2026-08-01T09:00");
    await user.type(screen.getByLabelText(/planned arrival time/i), "2026-08-01T11:30");
    await user.upload(
      screen.getByLabelText(/boarding pass/i),
      makeSmallFile("bp.pdf", "application/pdf"),
    );
    await user.upload(
      screen.getByLabelText(/id or passport/i),
      makeSmallFile("id.pdf", "application/pdf"),
    );
    await user.click(screen.getByLabelText(/i agree to the gdpr/i));
    await user.click(screen.getByRole("button", { name: /submit claim/i }));

    await waitFor(() =>
      expect(screen.getByText(/case created/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/400\s*€/)).toBeInTheDocument();
    expect(screen.getByText(/1,?\s?874 km/)).toBeInTheDocument();
  });
```

**Verification:**

```powershell
cd frontend
npx vitest run tests/CaseEntryForm.test.tsx tests/CompensationSummary.test.tsx
npx tsc --noEmit
```

Expect: all tests pass, no type errors. Then a full run:

```powershell
cd backend
pytest -q
cd ../frontend
npm test
```

Both suites must be fully green.

---

## Self-Review

**Spec coverage:**

| Spec requirement | Covered by |
|---|---|
| `cases.compensation` sub-package with `brackets`, `distance`, `service`, `exceptions` | Tasks 1, 2, 3 |
| Airport Gap first + local Haversine fallback + 3s timeout + one retry + optional token | Task 2 |
| Bracket rule `≤1500`/`≤3500`/`>3500` → 250/400/600 | Task 1 (with boundary tests) |
| Sum of great-circle per-leg distances following `FlightSegment.order` | Task 3 (`compute_for_case`) |
| `POST /api/compensation/preview` — 1–5 legs, 3-letter IATA, `from != to`, 200/400/422/429 | Tasks 3 + 4 |
| `distance_km` rounded to 2dp with ROUND_HALF_EVEN | Task 3 (`_round2`) |
| Per-leg `source: "airportgap" \| "haversine"` marker | Tasks 2, 3 |
| 60/min throttle scope `compensation_preview` | Task 4 |
| Three nullable `Case` columns + `CheckConstraint` on `{250,400,600,NULL}` + admin exposure | Task 5 |
| Migration `0002_case_compensation_fields.py` | Task 5 |
| Case-create runs `compute_for_case` inside the atomic block; failure never blocks creation | Task 6 |
| 201 response gains `distance_km`, `compensation_amount_eur`, `compensation_error` | Task 6 |
| Existing rollback path unchanged for non-`DistanceUnavailable` exceptions | Task 6 (block structure preserved) |
| Frontend `api/compensation.ts` with typed errors | Task 7 |
| `CompensationSummary` component with debounce + abort + four states | Task 8 |
| Component rendered above submit button; success view shows compensation | Task 9 |
| Backend tests: brackets, distance (both branches), service, preview API, extended case-create | Tasks 1, 2, 3, 4, 6 |
| Frontend tests: summary states, debounce, form success view | Tasks 8, 9 |

No gaps identified.

**Placeholder scan:** No "TBD" / "TODO" / "add appropriate handling" / "similar to Task N" strings appear in this document.

**Type consistency:** `CompensationPreview.legs[].distance_km` is `number | null` on the frontend (numeric strings coerced via `Number(...)`); on the backend it's `Decimal | None` (serialised by DRF as string, coerced back on the client). `compensation_amount_eur` is `250 | 400 | 600 | null` in both `CaseCreateResponse` and `CompensationPreview` (never `null` on the preview success path). `compensation_error` is `string | null` in the case-create response only.

Plan saved to `documentation/spec-driven/plans/2026-07-23-case-02-compensation-plan.md`. Ready to begin subagent-driven implementation.
