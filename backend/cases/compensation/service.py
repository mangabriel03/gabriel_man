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
    # Round each leg to 2dp before summing so that this path agrees exactly
    # with `preview_from_legs`, which exposes 2dp per-leg values to the client.
    totals: list[Decimal] = []
    for leg in legs:
        km, _source = compute_leg_km(
            leg["from"], leg["to"], airport_lookup=lookup.get,
        )
        totals.append(_round2(km))

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
    # Only called when every leg succeeded, so distance_km is always a Decimal.
    total = sum((leg["distance_km"] for leg in per_leg), Decimal("0"))
    return _round2(total)
