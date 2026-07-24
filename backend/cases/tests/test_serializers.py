from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta

import pytest

from cases.models import Case
from cases.serializers import CaseCreateSerializer


@pytest.mark.django_db
def test_happy_path_creates_case(two_airports, valid_payload):
    ser = CaseCreateSerializer(data=valid_payload)
    assert ser.is_valid(), ser.errors
    case = ser.save()
    assert Case.objects.count() == 1
    assert case.status == "NEW"
    assert case.segments.count() == 1


@pytest.mark.django_db
def test_dob_today_rejected(two_airports, valid_payload):
    valid_payload["passenger"]["date_of_birth"] = date.today().isoformat()
    ser = CaseCreateSerializer(data=valid_payload)
    assert not ser.is_valid()
    assert "date_of_birth" in ser.errors["passenger"]


@pytest.mark.django_db
def test_gdpr_false_rejected(two_airports, valid_payload):
    valid_payload["gdpr_consent"] = False
    ser = CaseCreateSerializer(data=valid_payload)
    assert not ser.is_valid()
    assert "gdpr_consent" in ser.errors


@pytest.mark.django_db
def test_zero_problem_flights_rejected(two_airports, valid_payload):
    valid_payload["segments"][0]["is_problem_flight"] = False
    ser = CaseCreateSerializer(data=valid_payload)
    assert not ser.is_valid()
    assert "segments" in ser.errors


@pytest.mark.django_db
def test_two_problem_flights_rejected(two_airports, valid_payload):
    extra = deepcopy(valid_payload["segments"][0])
    extra["order"] = 1
    valid_payload["segments"].append(extra)
    ser = CaseCreateSerializer(data=valid_payload)
    assert not ser.is_valid()
    assert "segments" in ser.errors


@pytest.mark.django_db
def test_unknown_iata_rejected(two_airports, valid_payload):
    valid_payload["segments"][0]["arrival_airport_iata"] = "XYZ"
    ser = CaseCreateSerializer(data=valid_payload)
    assert not ser.is_valid()
    assert "segments" in ser.errors


@pytest.mark.django_db
def test_bad_phone_rejected(two_airports, valid_payload):
    valid_payload["passenger"]["phone"] = "not-a-phone!"
    ser = CaseCreateSerializer(data=valid_payload)
    assert not ser.is_valid()
    assert "phone" in ser.errors["passenger"]


@pytest.mark.django_db
def test_arrival_not_after_departure_rejected(two_airports, valid_payload):
    seg = valid_payload["segments"][0]
    seg["planned_arrival_time"] = seg["planned_departure_time"]
    ser = CaseCreateSerializer(data=valid_payload)
    assert not ser.is_valid()


@pytest.mark.django_db
def test_six_segments_rejected(two_airports, valid_payload):
    base = valid_payload["segments"][0]
    valid_payload["segments"] = [
        {**deepcopy(base), "order": i, "is_problem_flight": (i == 0)}
        for i in range(6)
    ]
    ser = CaseCreateSerializer(data=valid_payload)
    assert not ser.is_valid()
    assert "segments" in ser.errors
