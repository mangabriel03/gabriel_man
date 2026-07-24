from __future__ import annotations

import uuid
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models.signals import post_delete
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.dispatch import receiver
from django.utils import timezone

from .disruption.choices import (
    AirlineMotive,
    CancellationNotice,
    DelayDuration,
    DeniedBoardingReason,
    DISRUPTION_TYPE_DB_VALUES,
    DisruptionType,
    MotiveMentioned,
)


PHONE_REGEX = r"^\+?[0-9\s\-()]{7,30}$"


def case_document_upload_to(instance: "CaseDocument", filename: str) -> str:
    ext = Path(filename).suffix.lower().lstrip(".") or "bin"
    return f"cases/{instance.case_id}/{instance.kind}_{uuid.uuid4().hex}.{ext}"


class CaseStatus(models.TextChoices):
    NEW = "NEW", "New"
    VALID = "VALID", "Valid"
    ASSIGNED = "ASSIGNED", "Assigned"
    INVALID = "INVALID", "Invalid"


class Case(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=10, choices=CaseStatus.choices,
                              default=CaseStatus.NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    date_of_birth = models.DateField()
    email = models.EmailField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="cases",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    phone = models.CharField(
        max_length=30, validators=[RegexValidator(regex=PHONE_REGEX)]
    )
    address = models.CharField(max_length=200)
    postal_code = models.CharField(max_length=20)

    reservation_number = models.CharField(max_length=30)

    gdpr_consent = models.BooleanField(default=False)
    gdpr_consent_at = models.DateTimeField(null=True, blank=True)

    # --- CASE_02 compensation ---
    distance_km = models.DecimalField(
        max_digits=9, decimal_places=2, null=True, blank=True,
    )
    compensation_amount_eur = models.PositiveSmallIntegerField(
        null=True, blank=True,
    )
    compensation_calculated_at = models.DateTimeField(null=True, blank=True)

    # --- CASE_03 disruption ---
    disruption_type = models.CharField(
        max_length=20, choices=DisruptionType.choices,
    )
    cancellation_notice = models.CharField(
        max_length=20, choices=CancellationNotice.choices, null=True, blank=True,
    )
    delay_duration = models.CharField(
        max_length=20, choices=DelayDuration.choices, null=True, blank=True,
    )
    denied_boarding_voluntary = models.BooleanField(null=True, blank=True)
    denied_boarding_reason = models.CharField(
        max_length=30, choices=DeniedBoardingReason.choices, null=True, blank=True,
    )
    airline_motive_mentioned = models.CharField(
        max_length=10, choices=MotiveMentioned.choices, null=True, blank=True,
    )
    airline_motive = models.CharField(
        max_length=20, choices=AirlineMotive.choices, null=True, blank=True,
    )
    incident_description = models.TextField(max_length=2000)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(compensation_amount_eur__isnull=True)
                    | Q(compensation_amount_eur__in=[250, 400, 600])
                ),
                name="compensation_amount_eur_valid",
            ),
            models.CheckConstraint(
                check=Q(disruption_type__in=DISRUPTION_TYPE_DB_VALUES),
                name="disruption_type_valid",
            ),
        ]

    def clean(self) -> None:
        if self.date_of_birth and self.date_of_birth >= timezone.now().date():
            raise ValidationError({"date_of_birth": "Date of birth must be before today."})
        if not self.gdpr_consent:
            raise ValidationError({"gdpr_consent": "GDPR consent is required."})

    def __str__(self) -> str:
        return f"Case {self.id} ({self.status})"


class PassengerAccount(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="passenger_account",
        on_delete=models.CASCADE,
    )
    must_change_password = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"PassengerAccount for {self.user_id}"


class AccountRole(models.TextChoices):
    SYSTEM_ADMIN = "SYSTEM_ADMIN", "System Admin"
    COLLEAGUE = "COLLEAGUE", "Colleague"
    PASSENGER = "PASSENGER", "Passenger"


class UserAccountProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="account_profile",
        on_delete=models.CASCADE,
    )
    assigned_role = models.CharField(max_length=20, choices=AccountRole.choices)
    must_change_password = models.BooleanField(default=False)
    password_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"UserAccountProfile for {self.user_id} ({self.assigned_role})"


class FlightSegment(models.Model):
    case = models.ForeignKey(Case, related_name="segments", on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField()
    flight_date = models.DateField()
    flight_number = models.CharField(max_length=10)
    airline = models.CharField(max_length=80)
    departure_airport = models.ForeignKey(
        "airports.Airport", related_name="+", on_delete=models.PROTECT
    )
    arrival_airport = models.ForeignKey(
        "airports.Airport", related_name="+", on_delete=models.PROTECT
    )
    planned_departure_time = models.DateTimeField()
    planned_arrival_time = models.DateTimeField()
    is_problem_flight = models.BooleanField(default=False)

    class Meta:
        ordering = ["case", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["case", "order"], name="uniq_case_segment_order"
            ),
            models.CheckConstraint(
                check=Q(order__lte=4), name="segment_order_max_4"
            ),
            # Partial unique constraint added by a data-migration in Task 6b/inside
            # the initial migration for Postgres only. Kept out of Meta.constraints
            # so SQLite tests do not blow up.
        ]

    def clean(self) -> None:
        if (
            self.planned_departure_time
            and self.planned_arrival_time
            and self.planned_arrival_time <= self.planned_departure_time
        ):
            raise ValidationError(
                {"planned_arrival_time": "Arrival time must be after departure time."}
            )

    def __str__(self) -> str:
        return f"Segment {self.order} of {self.case_id} — {self.flight_number}"


class DocumentKind(models.TextChoices):
    BOARDING_PASS = "BOARDING_PASS", "Boarding pass"
    ID_DOCUMENT = "ID_DOCUMENT", "ID / Passport"


class CaseDocument(models.Model):
    case = models.ForeignKey(Case, related_name="documents", on_delete=models.CASCADE)
    kind = models.CharField(max_length=20, choices=DocumentKind.choices)
    file = models.FileField(upload_to=case_document_upload_to)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=80)
    size_bytes = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["case", "kind"], name="uniq_case_document_kind"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.kind} for {self.case_id}"


@receiver(post_delete, sender=CaseDocument)
def delete_case_document_file(sender, instance: CaseDocument, **kwargs) -> None:
    if instance.file:
        instance.file.delete(save=False)
