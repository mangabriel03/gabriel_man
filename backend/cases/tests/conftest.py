from __future__ import annotations

from datetime import date, datetime, timedelta, timezone as tz

import pytest

from airports.models import Airport


@pytest.fixture
def two_airports(db):
    otp = Airport.objects.create(
        iata="OTP", icao="LROP", name="Henri Coanda", city="Bucharest",
        country="Romania", latitude="44.5711", longitude="26.0850",
    )
    cdg = Airport.objects.create(
        iata="CDG", icao="LFPG", name="Charles de Gaulle", city="Paris",
        country="France", latitude="49.0097", longitude="2.5479",
    )
    return otp, cdg


@pytest.fixture
def valid_payload():
    return {
        "passenger": {
            "first_name": "Ana",
            "last_name": "Popescu",
            "date_of_birth": (date.today() - timedelta(days=365 * 30)).isoformat(),
            "email": "ana@example.com",
            "phone": "+40 712 345 678",
            "address": "Str. Exemplu 1",
            "postal_code": "010101",
        },
        "reservation_number": "ABC123",
        "segments": [
            {
                "order": 0,
                "flight_date": (date.today() + timedelta(days=7)).isoformat(),
                "flight_number": "AF1234",
                "airline": "Air France",
                "departure_airport_iata": "OTP",
                "arrival_airport_iata": "CDG",
                "planned_departure_time": datetime.now(tz.utc).replace(microsecond=0).isoformat(),
                "planned_arrival_time":   (datetime.now(tz.utc).replace(microsecond=0) + timedelta(hours=3)).isoformat(),
                "is_problem_flight": True,
            }
        ],
        "disruption": {
            "disruption_type": "DELAY",
            "delay_duration": "MORE_THAN_3H",
            "airline_motive_mentioned": "DONT_KNOW",
            "incident_description": "Flight was delayed by five hours; missed connection.",
        },
        "gdpr_consent": True,
    }
