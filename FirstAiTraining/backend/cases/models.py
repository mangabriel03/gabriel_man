from __future__ import annotations

import uuid
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


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
    phone = models.CharField(
        max_length=30, validators=[RegexValidator(regex=PHONE_REGEX)]
    )
    address = models.CharField(max_length=200)
    postal_code = models.CharField(max_length=20)

    reservation_number = models.CharField(max_length=30)

    gdpr_consent = models.BooleanField(default=False)
    gdpr_consent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self) -> None:
        if self.date_of_birth and self.date_of_birth >= timezone.now().date():
            raise ValidationError({"date_of_birth": "Date of birth must be before today."})
        if not self.gdpr_consent:
            raise ValidationError({"gdpr_consent": "GDPR consent is required."})

    def __str__(self) -> str:
        return f"Case {self.id} ({self.status})"


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
