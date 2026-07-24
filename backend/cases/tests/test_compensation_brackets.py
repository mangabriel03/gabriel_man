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
