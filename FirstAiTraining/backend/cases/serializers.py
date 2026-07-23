from __future__ import annotations

import json
from datetime import date

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from airports.models import Airport

from .models import Case, CaseDocument, DocumentKind, FlightSegment


PHONE_REGEX = r"^\+?[0-9\s\-()]{7,30}$"


class PassengerSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=80)
    last_name = serializers.CharField(max_length=80)
    date_of_birth = serializers.DateField()
    email = serializers.EmailField()
    phone = serializers.RegexField(regex=PHONE_REGEX, max_length=30)
    address = serializers.CharField(max_length=200)
    postal_code = serializers.CharField(max_length=20)

    def validate_date_of_birth(self, value: date) -> date:
        if value >= timezone.now().date():
            raise serializers.ValidationError("Date of birth must be before today.")
        return value


class FlightSegmentSerializer(serializers.Serializer):
    order = serializers.IntegerField(min_value=0, max_value=4)
    flight_date = serializers.DateField()
    flight_number = serializers.CharField(max_length=10)
    airline = serializers.CharField(max_length=80)
    departure_airport_iata = serializers.CharField(max_length=3, min_length=3)
    arrival_airport_iata = serializers.CharField(max_length=3, min_length=3)
    planned_departure_time = serializers.DateTimeField()
    planned_arrival_time = serializers.DateTimeField()
    is_problem_flight = serializers.BooleanField()

    def validate(self, attrs):
        if attrs["planned_arrival_time"] <= attrs["planned_departure_time"]:
            raise serializers.ValidationError(
                {"planned_arrival_time": "Arrival time must be after departure time."}
            )
        return attrs


class CaseCreateSerializer(serializers.Serializer):
    passenger = PassengerSerializer()
    reservation_number = serializers.CharField(max_length=30)
    segments = FlightSegmentSerializer(many=True)
    gdpr_consent = serializers.BooleanField()

    def validate_gdpr_consent(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError(
                "You must accept the GDPR policy to submit."
            )
        return value

    def validate_segments(self, value: list[dict]) -> list[dict]:
        if not (1 <= len(value) <= 5):
            raise serializers.ValidationError("Between 1 and 5 segments are required.")

        orders = [s["order"] for s in value]
        if len(set(orders)) != len(orders):
            raise serializers.ValidationError("Segment order values must be unique.")

        problems = [s for s in value if s["is_problem_flight"]]
        if len(problems) != 1:
            raise serializers.ValidationError(
                "Exactly one segment must be marked as the problem flight."
            )

        iatas = {s["departure_airport_iata"].upper() for s in value} | {
            s["arrival_airport_iata"].upper() for s in value
        }
        known = set(Airport.objects.filter(iata__in=iatas).values_list("iata", flat=True))
        unknown = iatas - known
        if unknown:
            raise serializers.ValidationError(
                f"Unknown airport code(s): {', '.join(sorted(unknown))}."
            )

        return value

    @transaction.atomic
    def create(self, validated_data: dict) -> Case:
        passenger = validated_data["passenger"]
        segments = validated_data["segments"]

        case = Case.objects.create(
            first_name=passenger["first_name"],
            last_name=passenger["last_name"],
            date_of_birth=passenger["date_of_birth"],
            email=passenger["email"],
            phone=passenger["phone"],
            address=passenger["address"],
            postal_code=passenger["postal_code"],
            reservation_number=validated_data["reservation_number"],
            gdpr_consent=True,
            gdpr_consent_at=timezone.now(),
        )

        airports_by_iata = {
            a.iata: a
            for a in Airport.objects.filter(
                iata__in={s["departure_airport_iata"].upper() for s in segments}
                | {s["arrival_airport_iata"].upper() for s in segments}
            )
        }
        for seg in segments:
            FlightSegment.objects.create(
                case=case,
                order=seg["order"],
                flight_date=seg["flight_date"],
                flight_number=seg["flight_number"],
                airline=seg["airline"],
                departure_airport=airports_by_iata[seg["departure_airport_iata"].upper()],
                arrival_airport=airports_by_iata[seg["arrival_airport_iata"].upper()],
                planned_departure_time=seg["planned_departure_time"],
                planned_arrival_time=seg["planned_arrival_time"],
                is_problem_flight=seg["is_problem_flight"],
            )
        return case


def parse_payload_field(raw: str) -> dict:
    """Parse the multipart 'payload' field, raising DRF ValidationError on bad JSON."""
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise serializers.ValidationError({"payload": f"Invalid JSON: {exc}"})
