from __future__ import annotations

import json
from datetime import date

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from airports.models import Airport

from .account_service import provision_colleague_account, provision_passenger_account
from .disruption import (
    AirlineMotive,
    CancellationNotice,
    DelayDuration,
    DeniedBoardingReason,
    DISRUPTION_TYPE_API_VALUES,
    DisruptionType,
    MotiveMentioned,
)
from .models import Case, CaseDocument, DocumentKind, FlightSegment


PHONE_REGEX = r"^\+?[0-9\s\-()]{7,30}$"


class AdminUserCreateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, trim_whitespace=True)
    last_name = serializers.CharField(max_length=150, trim_whitespace=True)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=12, max_length=128, trim_whitespace=False)

    def validate_first_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("First name is required.")
        return value

    def validate_last_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Last name is required.")
        return value

    def validate_email(self, value: str) -> str:
        normalized_email = value.strip().lower()
        if not normalized_email:
            raise serializers.ValidationError("Email is required.")

        user_model = get_user_model()
        existing_user = user_model.objects.filter(username__iexact=normalized_email).first()
        if existing_user is not None and (existing_user.is_staff or existing_user.is_superuser):
            raise serializers.ValidationError("A staff account already exists for this email address.")
        return normalized_email

    def create(self, validated_data: dict):
        return provision_colleague_account(
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            email=validated_data["email"],
            password=validated_data["password"],
        )


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


_VOLUNTARY_TO_BOOL = {"YES": True, "NO": False}


class DisruptionSerializer(serializers.Serializer):
    """Nested serializer for the `disruption` block on POST /api/cases/.

    Conditional-required rules live here (not on the model). Fields that do
    not belong to the chosen `disruption_type` MUST be absent or null; sending
    a non-null value for an inapplicable field is a 400 error.
    """

    disruption_type = serializers.ChoiceField(choices=DISRUPTION_TYPE_API_VALUES)
    cancellation_notice = serializers.ChoiceField(
        choices=CancellationNotice.values, required=False, allow_null=True,
    )
    delay_duration = serializers.ChoiceField(
        choices=DelayDuration.values, required=False, allow_null=True,
    )
    denied_boarding_voluntary = serializers.ChoiceField(
        choices=["YES", "NO"], required=False, allow_null=True,
    )
    denied_boarding_reason = serializers.ChoiceField(
        choices=DeniedBoardingReason.values, required=False, allow_null=True,
    )
    airline_motive_mentioned = serializers.ChoiceField(
        choices=MotiveMentioned.values, required=False, allow_null=True,
    )
    airline_motive = serializers.ChoiceField(
        choices=AirlineMotive.values, required=False, allow_null=True,
    )
    incident_description = serializers.CharField(
        max_length=2000, allow_blank=False, trim_whitespace=True,
    )

    # Fields that are allowed to be non-null per disruption_type. All other
    # optional fields must be null or absent for that type.
    _ALLOWED: dict[str, set[str]] = {
        DisruptionType.CANCELLATION.value: {
            "cancellation_notice", "airline_motive_mentioned", "airline_motive",
        },
        DisruptionType.DELAY.value: {
            "delay_duration", "airline_motive_mentioned", "airline_motive",
        },
        DisruptionType.DENIED_BOARDING.value: {
            "denied_boarding_voluntary", "denied_boarding_reason",
        },
    }
    # Subset of _ALLOWED[type] that must be non-null (unconditionally required
    # for the branch). Airline motive rules are handled separately below.
    _REQUIRED: dict[str, set[str]] = {
        DisruptionType.CANCELLATION.value: {
            "cancellation_notice", "airline_motive_mentioned",
        },
        DisruptionType.DELAY.value: {
            "delay_duration", "airline_motive_mentioned",
        },
        DisruptionType.DENIED_BOARDING.value: {"denied_boarding_voluntary"},
    }
    _ALL_OPTIONAL = {
        "cancellation_notice", "delay_duration",
        "denied_boarding_voluntary", "denied_boarding_reason",
        "airline_motive_mentioned", "airline_motive",
    }

    def validate(self, attrs: dict) -> dict:
        d_type = attrs["disruption_type"]
        allowed = self._ALLOWED[d_type]
        errors: dict[str, list[str]] = {}

        # 1. Reject inapplicable non-null fields.
        for name in self._ALL_OPTIONAL - allowed:
            if attrs.get(name) is not None:
                errors[name] = [
                    f"Not applicable for disruption_type '{d_type}'."
                ]

        # 2. Enforce unconditional required fields per branch.
        for name in self._REQUIRED[d_type]:
            if attrs.get(name) is None:
                errors[name] = ["This field is required."]

        # 3. Conditional airline motive rule (CANCELLATION / DELAY only).
        if d_type in {DisruptionType.CANCELLATION.value, DisruptionType.DELAY.value}:
            mentioned = attrs.get("airline_motive_mentioned")
            motive = attrs.get("airline_motive")
            if mentioned == MotiveMentioned.YES.value and motive is None:
                errors["airline_motive"] = ["This field is required."]
            if mentioned != MotiveMentioned.YES.value and motive is not None:
                errors["airline_motive"] = [
                    "Only allowed when airline_motive_mentioned == 'YES'."
                ]

        # 4. Conditional denied-boarding-reason rule.
        if d_type == DisruptionType.DENIED_BOARDING.value:
            voluntary = attrs.get("denied_boarding_voluntary")
            reason = attrs.get("denied_boarding_reason")
            if voluntary == "NO" and reason is None:
                errors["denied_boarding_reason"] = ["This field is required."]
            if voluntary == "YES" and reason is not None:
                errors["denied_boarding_reason"] = [
                    "Only allowed when denied_boarding_voluntary == 'NO'."
                ]

        if errors:
            raise serializers.ValidationError(errors)

        # Convert the voluntary string to bool for storage; other fields
        # already match storage types. Strip inapplicable keys so `create()`
        # can splat the dict onto the model without writing stray values.
        cleaned: dict = {
            "disruption_type": d_type,
            "incident_description": attrs["incident_description"],
        }
        for name in allowed:
            value = attrs.get(name)
            if name == "denied_boarding_voluntary" and value is not None:
                cleaned[name] = _VOLUNTARY_TO_BOOL[value]
            else:
                cleaned[name] = value
        # Ensure every disruption column has an explicit key (None where absent).
        for name in self._ALL_OPTIONAL:
            cleaned.setdefault(name, None)
        return cleaned


class CaseCreateSerializer(serializers.Serializer):
    passenger = PassengerSerializer()
    reservation_number = serializers.CharField(max_length=30)
    segments = FlightSegmentSerializer(many=True)
    disruption = DisruptionSerializer()
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
        disruption = validated_data["disruption"]
        passenger_user = provision_passenger_account(
            first_name=passenger["first_name"],
            last_name=passenger["last_name"],
            email=passenger["email"],
        )

        case = Case.objects.create(
            first_name=passenger["first_name"],
            last_name=passenger["last_name"],
            date_of_birth=passenger["date_of_birth"],
            email=passenger["email"],
            user=passenger_user,
            phone=passenger["phone"],
            address=passenger["address"],
            postal_code=passenger["postal_code"],
            reservation_number=validated_data["reservation_number"],
            gdpr_consent=True,
            gdpr_consent_at=timezone.now(),
            disruption_type=disruption["disruption_type"],
            cancellation_notice=disruption["cancellation_notice"],
            delay_duration=disruption["delay_duration"],
            denied_boarding_voluntary=disruption["denied_boarding_voluntary"],
            denied_boarding_reason=disruption["denied_boarding_reason"],
            airline_motive_mentioned=disruption["airline_motive_mentioned"],
            airline_motive=disruption["airline_motive"],
            incident_description=disruption["incident_description"],
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


class PreviewLegSerializer(serializers.Serializer):
    from_ = serializers.CharField(max_length=3, min_length=3)
    to = serializers.CharField(max_length=3, min_length=3)

    # `from` is a Python keyword; declare the field as `from_` and rebind it to
    # the JSON key "from" after construction. DRF's auto-assigned source stays
    # as "from_" (differs from the rebound field name, so no assertion), which
    # is why validate() reads attrs["from_"] but returns the JSON-shaped dict.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["from"] = self.fields.pop("from_")

    def validate(self, attrs):
        f = attrs["from_"].upper()
        t = attrs["to"].upper()
        if not f.isalpha() or not t.isalpha():
            raise serializers.ValidationError("IATA codes must be letters only.")
        if f == t:
            raise serializers.ValidationError("A leg's departure and arrival must differ.")
        return {"from": f, "to": t}


class PreviewRequestSerializer(serializers.Serializer):
    legs = PreviewLegSerializer(many=True, min_length=1, max_length=5)
