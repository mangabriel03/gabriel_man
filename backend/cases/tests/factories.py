from __future__ import annotations

from datetime import date, timedelta

import factory
from django.utils import timezone

from airports.models import Airport

from cases.models import Case, CaseDocument, DocumentKind, FlightSegment


class AirportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Airport

    iata = factory.Sequence(lambda n: f"A{n:02d}")
    icao = None
    name = factory.Faker("city")
    city = factory.Faker("city")
    country = factory.Faker("country")
    latitude = "0.000000"
    longitude = "0.000000"


class CaseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Case

    first_name = "Ana"
    last_name = "Popescu"
    date_of_birth = date.today() - timedelta(days=365 * 25)
    email = "ana@example.com"
    phone = "+40 712 345 678"
    address = "Str. Exemplu 1"
    postal_code = "010101"
    reservation_number = "ABC123"
    gdpr_consent = True
    gdpr_consent_at = factory.LazyFunction(timezone.now)

    # --- CASE_03 disruption defaults (DELAY branch, no motive) ---
    disruption_type = "DELAY"
    delay_duration = "MORE_THAN_3H"
    airline_motive_mentioned = "DONT_KNOW"
    incident_description = "Flight was delayed by five hours."


class FlightSegmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FlightSegment

    case = factory.SubFactory(CaseFactory)
    order = 0
    flight_date = date.today() + timedelta(days=7)
    flight_number = "AF1234"
    airline = "Air France"
    departure_airport = factory.SubFactory(AirportFactory)
    arrival_airport = factory.SubFactory(AirportFactory)
    planned_departure_time = factory.LazyFunction(timezone.now)
    planned_arrival_time = factory.LazyAttribute(lambda o: o.planned_departure_time + timedelta(hours=3))
    is_problem_flight = True
