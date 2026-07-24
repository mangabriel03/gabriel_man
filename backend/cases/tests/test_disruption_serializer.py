from __future__ import annotations

import pytest

from cases.serializers import DisruptionSerializer


BASE_DESCRIPTION = "Something went wrong on the flight."


def _run(payload: dict) -> DisruptionSerializer:
    s = DisruptionSerializer(data=payload)
    s.is_valid()
    return s


# ---- Positive: one payload per branch + motive-variant coverage ----

@pytest.mark.parametrize("mentioned", ["YES", "NO", "DONT_KNOW"])
def test_cancellation_valid_all_motive_variants(mentioned):
    payload = {
        "disruption_type": "CANCELLATION",
        "cancellation_notice": "ON_FLIGHT_DAY",
        "airline_motive_mentioned": mentioned,
        "incident_description": BASE_DESCRIPTION,
    }
    if mentioned == "YES":
        payload["airline_motive"] = "TECHNICAL"
    s = _run(payload)
    assert s.errors == {}, s.errors
    assert s.validated_data["disruption_type"] == "CANCELLATION"
    assert s.validated_data["delay_duration"] is None
    assert s.validated_data["denied_boarding_voluntary"] is None
    if mentioned == "YES":
        assert s.validated_data["airline_motive"] == "TECHNICAL"
    else:
        assert s.validated_data["airline_motive"] is None


@pytest.mark.parametrize("duration", ["LESS_THAN_3H", "MORE_THAN_3H", "CONNECTION_LOST"])
def test_delay_valid(duration):
    s = _run({
        "disruption_type": "DELAY",
        "delay_duration": duration,
        "airline_motive_mentioned": "NO",
        "incident_description": BASE_DESCRIPTION,
    })
    assert s.errors == {}, s.errors
    assert s.validated_data["delay_duration"] == duration
    assert s.validated_data["cancellation_notice"] is None


def test_denied_boarding_voluntary_yes_no_reason():
    s = _run({
        "disruption_type": "DENIED_BOARDING",
        "denied_boarding_voluntary": "YES",
        "incident_description": BASE_DESCRIPTION,
    })
    assert s.errors == {}, s.errors
    assert s.validated_data["denied_boarding_voluntary"] is True
    assert s.validated_data["denied_boarding_reason"] is None
    assert s.validated_data["airline_motive_mentioned"] is None


@pytest.mark.parametrize("reason", ["OVERBOOKED", "AGGRESSIVE_BEHAVIOR", "INTOXICATION", "UNSPECIFIED"])
def test_denied_boarding_involuntary_requires_reason(reason):
    s = _run({
        "disruption_type": "DENIED_BOARDING",
        "denied_boarding_voluntary": "NO",
        "denied_boarding_reason": reason,
        "incident_description": BASE_DESCRIPTION,
    })
    assert s.errors == {}, s.errors
    assert s.validated_data["denied_boarding_voluntary"] is False
    assert s.validated_data["denied_boarding_reason"] == reason


# ---- Negative: missing required sub-fields ----

def test_cancellation_missing_notice_rejected():
    s = _run({
        "disruption_type": "CANCELLATION",
        "airline_motive_mentioned": "NO",
        "incident_description": BASE_DESCRIPTION,
    })
    assert "cancellation_notice" in s.errors


def test_delay_missing_duration_rejected():
    s = _run({
        "disruption_type": "DELAY",
        "airline_motive_mentioned": "NO",
        "incident_description": BASE_DESCRIPTION,
    })
    assert "delay_duration" in s.errors


def test_denied_boarding_missing_voluntary_rejected():
    s = _run({
        "disruption_type": "DENIED_BOARDING",
        "incident_description": BASE_DESCRIPTION,
    })
    assert "denied_boarding_voluntary" in s.errors


@pytest.mark.parametrize(
    "d_type,extra",
    [
        ("CANCELLATION", {"cancellation_notice": "ON_FLIGHT_DAY"}),
        ("DELAY", {"delay_duration": "MORE_THAN_3H"}),
    ],
)
def test_airline_motive_mentioned_missing_rejected(d_type, extra):
    payload = {
        "disruption_type": d_type,
        "incident_description": BASE_DESCRIPTION,
        **extra,
    }
    s = _run(payload)
    assert "airline_motive_mentioned" in s.errors


def test_airline_motive_required_when_mentioned_yes():
    s = _run({
        "disruption_type": "DELAY",
        "delay_duration": "MORE_THAN_3H",
        "airline_motive_mentioned": "YES",
        "incident_description": BASE_DESCRIPTION,
    })
    assert "airline_motive" in s.errors


def test_reason_required_when_voluntary_no():
    s = _run({
        "disruption_type": "DENIED_BOARDING",
        "denied_boarding_voluntary": "NO",
        "incident_description": BASE_DESCRIPTION,
    })
    assert "denied_boarding_reason" in s.errors


# ---- Negative: cross-branch contamination ----

def test_cancellation_rejects_delay_duration():
    s = _run({
        "disruption_type": "CANCELLATION",
        "cancellation_notice": "ON_FLIGHT_DAY",
        "airline_motive_mentioned": "NO",
        "delay_duration": "MORE_THAN_3H",
        "incident_description": BASE_DESCRIPTION,
    })
    assert "delay_duration" in s.errors
    assert "CANCELLATION" in s.errors["delay_duration"][0]


def test_delay_rejects_denied_boarding_voluntary():
    s = _run({
        "disruption_type": "DELAY",
        "delay_duration": "MORE_THAN_3H",
        "airline_motive_mentioned": "NO",
        "denied_boarding_voluntary": "YES",
        "incident_description": BASE_DESCRIPTION,
    })
    assert "denied_boarding_voluntary" in s.errors


def test_denied_boarding_rejects_airline_motive_mentioned():
    s = _run({
        "disruption_type": "DENIED_BOARDING",
        "denied_boarding_voluntary": "YES",
        "airline_motive_mentioned": "YES",
        "incident_description": BASE_DESCRIPTION,
    })
    assert "airline_motive_mentioned" in s.errors


def test_motive_rejected_when_mentioned_not_yes():
    s = _run({
        "disruption_type": "DELAY",
        "delay_duration": "MORE_THAN_3H",
        "airline_motive_mentioned": "NO",
        "airline_motive": "TECHNICAL",
        "incident_description": BASE_DESCRIPTION,
    })
    assert "airline_motive" in s.errors


def test_reason_rejected_when_voluntary_yes():
    s = _run({
        "disruption_type": "DENIED_BOARDING",
        "denied_boarding_voluntary": "YES",
        "denied_boarding_reason": "OVERBOOKED",
        "incident_description": BASE_DESCRIPTION,
    })
    assert "denied_boarding_reason" in s.errors


# ---- Negative: enum rejection ----

def test_unspecified_disruption_type_rejected():
    s = _run({
        "disruption_type": "UNSPECIFIED",
        "incident_description": BASE_DESCRIPTION,
    })
    assert "disruption_type" in s.errors


def test_unknown_disruption_type_rejected():
    s = _run({
        "disruption_type": "FOO",
        "incident_description": BASE_DESCRIPTION,
    })
    assert "disruption_type" in s.errors


# ---- Negative: description bounds ----

def test_description_blank_rejected():
    s = _run({
        "disruption_type": "DELAY",
        "delay_duration": "MORE_THAN_3H",
        "airline_motive_mentioned": "NO",
        "incident_description": "   ",
    })
    assert "incident_description" in s.errors


def test_description_too_long_rejected():
    s = _run({
        "disruption_type": "DELAY",
        "delay_duration": "MORE_THAN_3H",
        "airline_motive_mentioned": "NO",
        "incident_description": "x" * 2001,
    })
    assert "incident_description" in s.errors
