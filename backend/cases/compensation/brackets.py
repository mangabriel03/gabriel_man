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
