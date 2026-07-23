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
    assert len(payload["legs"]) == 2
    assert payload["legs"][0]["error"] is None
    assert payload["legs"][1] == {
        "from": "CDG", "to": "XXX",
        "distance_km": None, "source": None,
        "error": "Unknown airport code: XXX",
    }


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


@pytest.mark.django_db
def test_compute_for_case_agrees_with_preview_on_total_km(two_airports):
    """The two entry points must produce identical distance_km for identical inputs.

    Both round each leg to 2dp before summing (see service._sum_km and
    compute_for_case). If either path is changed to sum-then-round, this test
    catches the regression.
    """
    otp, cdg = two_airports
    case = CaseFactory()
    FlightSegmentFactory(case=case, order=0,
                         departure_airport=otp, arrival_airport=cdg,
                         is_problem_flight=True)
    FlightSegmentFactory(case=case, order=1,
                         departure_airport=cdg, arrival_airport=otp,
                         is_problem_flight=False)

    raw_legs = [(Decimal("1000.125"), "haversine"),
                (Decimal("600.005"), "haversine")]

    with patch("cases.compensation.service.compute_leg_km") as m:
        m.side_effect = list(raw_legs)
        compute_for_case(case)

    with patch("cases.compensation.service.compute_leg_km") as m:
        m.side_effect = list(raw_legs)
        preview = preview_from_legs([
            {"from": "OTP", "to": "CDG"},
            {"from": "CDG", "to": "OTP"},
        ])

    assert case.distance_km == preview["distance_km"]
    assert case.compensation_amount_eur == preview["compensation_amount_eur"]



# ------------------------- CheckConstraint (Task 5) -------------------------

from django.db import IntegrityError


@pytest.mark.django_db
def test_check_constraint_rejects_invalid_compensation_amount(two_airports):
    case = CaseFactory()
    case.compensation_amount_eur = 123
    with pytest.raises(IntegrityError):
        case.save()
