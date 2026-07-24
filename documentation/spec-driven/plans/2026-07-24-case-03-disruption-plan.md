# CASE_03 — Disruption Info: Implementation Plan

> **Execution:** Use subagent-driven development to implement this plan task-by-task.

**Goal:** Add a required Disruption block to case creation — the passenger picks a disruption type (Cancellation / Delay / Denied Boarding), answers the type-specific sub-questions, optionally records the airline's stated motive, and writes a free-text incident description. Values persist on `Case` inside the existing atomic create transaction; the case cannot be submitted without them.

**Architecture:** Additive changes only. Eight new nullable/required columns on `cases.Case` (migration `0003`); one nested `DisruptionSerializer` with a conditional-required matrix; new `DisruptionSection` on the frontend with RHF + Zod `discriminatedUnion` and dropdown-driven conditional field rendering. Compensation (CASE_02) is untouched — disruption never affects the amount at this stage.

**Tech Stack:** Django 5 + DRF (`TextChoices`, `CheckConstraint`), pytest-django, React 18 + TypeScript, React Hook Form + Zod, Vitest + React Testing Library.

**Design Spec:** [documentation/spec-driven/specs/2026-07-24-case-03-disruption-design.md](../specs/2026-07-24-case-03-disruption-design.md)

---

## File Structure

**Backend (created):**
- `backend/cases/disruption/__init__.py` — re-exports choices + `DisruptionSerializer`.
- `backend/cases/disruption/choices.py` — 6 `TextChoices` classes (source of truth for enum strings).
- `backend/cases/migrations/0003_disruption_fields.py` — 8 columns + `CheckConstraint` + backfill defaults.
- `backend/cases/tests/test_disruption_serializer.py` — conditional-required matrix.

**Backend (modified):**
- `backend/cases/models.py` — add 8 fields + `disruption_type_valid` constraint.
- `backend/cases/serializers.py` — add `DisruptionSerializer`, wire into `CaseCreateSerializer`.
- `backend/cases/views.py` — extend the 201 response with a nested `disruption` block.
- `backend/cases/admin.py` — expose 8 fields read-only in a "Disruption" fieldset.
- `backend/cases/tests/factories.py` — `CaseFactory` gains disruption defaults.
- `backend/cases/tests/conftest.py` — `valid_payload` gains a `disruption` block.
- `backend/cases/tests/test_api.py` — new coverage for the disruption block.

**Frontend (created):**
- `frontend/src/features/case-entry/disruption.ts` — enum literal constants + label maps.
- `frontend/src/features/case-entry/sections/DisruptionSection.tsx` — the new form section.
- `frontend/tests/DisruptionSection.test.tsx` — component tests.

**Frontend (modified):**
- `frontend/src/features/case-entry/types.ts` — `DisruptionInput` + `CasePayload.disruption` + `CaseCreateResponse.disruption`.
- `frontend/src/features/case-entry/schema.ts` — `disruptionSchema` (discriminated union) + merge into `caseFormSchema`.
- `frontend/src/features/case-entry/CaseEntryForm.tsx` — mount `<DisruptionSection/>` after `<ConnectingFlightsSection/>`; add disruption defaults to `emptyValues`.
- `frontend/tests/CaseEntryForm.test.tsx` — fill disruption in the happy-path test.

---

## Task Sequencing

Tasks 1 → 4 are the backend + database (do these first, in order). Tasks 5 → 8 are the frontend (any order after 4 is done, but the numeric order is recommended).

---

### Task 1: Choices, model fields, and migration 0003

**Files:**
- Create: `backend/cases/disruption/__init__.py`
- Create: `backend/cases/disruption/choices.py`
- Create: `backend/cases/migrations/0003_disruption_fields.py`
- Modify: `backend/cases/models.py`

**Requirements:**
- 6 `TextChoices` classes as specified in the spec §3, plus a `DisruptionType.UNSPECIFIED` DB-only sentinel.
- 8 new columns on `cases.Case`. `disruption_type` and `incident_description` are `NOT NULL`; the other 6 are `null=True, blank=True`.
- One `CheckConstraint` named `disruption_type_valid` that allows `CANCELLATION`, `DELAY`, `DENIED_BOARDING`, and `UNSPECIFIED` (the last only so backfilled rows validate).
- Migration adds columns with `default=` for the two `NOT NULL` fields, then `AlterField` drops those defaults. All other columns are added `null=True`.
- Sentinel backfill values: `disruption_type="UNSPECIFIED"`, `incident_description="(migrated from CASE_01/CASE_02; no disruption info collected)"`.

**Implementation:**

`backend/cases/disruption/choices.py`:

```python
from __future__ import annotations

from django.db import models


class DisruptionType(models.TextChoices):
    CANCELLATION = "CANCELLATION", "Cancellation"
    DELAY = "DELAY", "Delay"
    DENIED_BOARDING = "DENIED_BOARDING", "Denied boarding"
    # DB-only sentinel for pre-CASE_03 rows backfilled by migration 0003.
    # The DisruptionSerializer's `choices=` list excludes this value, so it
    # can never enter the DB via the API.
    UNSPECIFIED = "UNSPECIFIED", "Unspecified (legacy)"


class CancellationNotice(models.TextChoices):
    MORE_THAN_14_DAYS = "MORE_THAN_14_DAYS", "More than 14 days before"
    LESS_THAN_14_DAYS = "LESS_THAN_14_DAYS", "Less than 14 days before"
    ON_FLIGHT_DAY = "ON_FLIGHT_DAY", "On the flight day"


class DelayDuration(models.TextChoices):
    LESS_THAN_3H = "LESS_THAN_3H", "Less than 3 hours"
    MORE_THAN_3H = "MORE_THAN_3H", "More than 3 hours"
    CONNECTION_LOST = "CONNECTION_LOST", "Connection flight lost"


class DeniedBoardingReason(models.TextChoices):
    OVERBOOKED = "OVERBOOKED", "Flight overbooked"
    AGGRESSIVE_BEHAVIOR = "AGGRESSIVE_BEHAVIOR", "Aggressive behaviour with staff"
    INTOXICATION = "INTOXICATION", "Intoxication"
    UNSPECIFIED = "UNSPECIFIED", "Unspecified reason"


class MotiveMentioned(models.TextChoices):
    YES = "YES", "Yes"
    NO = "NO", "No"
    DONT_KNOW = "DONT_KNOW", "I don't know"


class AirlineMotive(models.TextChoices):
    TECHNICAL = "TECHNICAL", "Technical problem"
    WEATHER = "WEATHER", "Meteorological conditions"
    STRIKE = "STRIKE", "Strike"
    AIRPORT_ISSUE = "AIRPORT_ISSUE", "Problems with airport"
    CREW = "CREW", "Crew problems"
    OTHER = "OTHER", "Other motives"


DISRUPTION_TYPE_DB_VALUES = [c.value for c in DisruptionType]
"""All values accepted at the DB level (includes UNSPECIFIED for backfill)."""

DISRUPTION_TYPE_API_VALUES = [
    DisruptionType.CANCELLATION.value,
    DisruptionType.DELAY.value,
    DisruptionType.DENIED_BOARDING.value,
]
"""Values accepted by the API — UNSPECIFIED is deliberately excluded."""
```

`backend/cases/disruption/__init__.py`:

```python
from .choices import (
    AirlineMotive,
    CancellationNotice,
    DelayDuration,
    DeniedBoardingReason,
    DISRUPTION_TYPE_API_VALUES,
    DISRUPTION_TYPE_DB_VALUES,
    DisruptionType,
    MotiveMentioned,
)

__all__ = [
    "AirlineMotive",
    "CancellationNotice",
    "DelayDuration",
    "DeniedBoardingReason",
    "DISRUPTION_TYPE_API_VALUES",
    "DISRUPTION_TYPE_DB_VALUES",
    "DisruptionType",
    "MotiveMentioned",
]
```

`backend/cases/models.py` — add these imports at the top:

```python
from .disruption.choices import (
    AirlineMotive,
    CancellationNotice,
    DelayDuration,
    DeniedBoardingReason,
    DISRUPTION_TYPE_DB_VALUES,
    DisruptionType,
    MotiveMentioned,
)
```

Inside `class Case(models.Model):`, add these fields immediately after the existing `compensation_calculated_at` field:

```python
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
```

Extend the existing `Meta.constraints` list on `Case` to add:

```python
            models.CheckConstraint(
                check=Q(disruption_type__in=DISRUPTION_TYPE_DB_VALUES),
                name="disruption_type_valid",
            ),
```

`backend/cases/migrations/0003_disruption_fields.py`:

```python
# Generated by Django 5.x for CASE_03 disruption fields.
from django.db import migrations, models


BACKFILL_DESCRIPTION = (
    "(migrated from CASE_01/CASE_02; no disruption info collected)"
)

DISRUPTION_TYPE_CHOICES = [
    ("CANCELLATION", "Cancellation"),
    ("DELAY", "Delay"),
    ("DENIED_BOARDING", "Denied boarding"),
    ("UNSPECIFIED", "Unspecified (legacy)"),
]

CANCELLATION_NOTICE_CHOICES = [
    ("MORE_THAN_14_DAYS", "More than 14 days before"),
    ("LESS_THAN_14_DAYS", "Less than 14 days before"),
    ("ON_FLIGHT_DAY", "On the flight day"),
]

DELAY_DURATION_CHOICES = [
    ("LESS_THAN_3H", "Less than 3 hours"),
    ("MORE_THAN_3H", "More than 3 hours"),
    ("CONNECTION_LOST", "Connection flight lost"),
]

DENIED_BOARDING_REASON_CHOICES = [
    ("OVERBOOKED", "Flight overbooked"),
    ("AGGRESSIVE_BEHAVIOR", "Aggressive behaviour with staff"),
    ("INTOXICATION", "Intoxication"),
    ("UNSPECIFIED", "Unspecified reason"),
]

MOTIVE_MENTIONED_CHOICES = [
    ("YES", "Yes"),
    ("NO", "No"),
    ("DONT_KNOW", "I don't know"),
]

AIRLINE_MOTIVE_CHOICES = [
    ("TECHNICAL", "Technical problem"),
    ("WEATHER", "Meteorological conditions"),
    ("STRIKE", "Strike"),
    ("AIRPORT_ISSUE", "Problems with airport"),
    ("CREW", "Crew problems"),
    ("OTHER", "Other motives"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0002_case_compensation_fields"),
    ]

    operations = [
        # 1. Two NOT NULL columns with a temporary default to backfill existing rows.
        migrations.AddField(
            model_name="case",
            name="disruption_type",
            field=models.CharField(
                max_length=20,
                choices=DISRUPTION_TYPE_CHOICES,
                default="UNSPECIFIED",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="case",
            name="incident_description",
            field=models.TextField(
                max_length=2000,
                default=BACKFILL_DESCRIPTION,
            ),
            preserve_default=False,
        ),
        # 2. Six nullable columns — no backfill needed.
        migrations.AddField(
            model_name="case",
            name="cancellation_notice",
            field=models.CharField(
                max_length=20, choices=CANCELLATION_NOTICE_CHOICES,
                null=True, blank=True,
            ),
        ),
        migrations.AddField(
            model_name="case",
            name="delay_duration",
            field=models.CharField(
                max_length=20, choices=DELAY_DURATION_CHOICES,
                null=True, blank=True,
            ),
        ),
        migrations.AddField(
            model_name="case",
            name="denied_boarding_voluntary",
            field=models.BooleanField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="case",
            name="denied_boarding_reason",
            field=models.CharField(
                max_length=30, choices=DENIED_BOARDING_REASON_CHOICES,
                null=True, blank=True,
            ),
        ),
        migrations.AddField(
            model_name="case",
            name="airline_motive_mentioned",
            field=models.CharField(
                max_length=10, choices=MOTIVE_MENTIONED_CHOICES,
                null=True, blank=True,
            ),
        ),
        migrations.AddField(
            model_name="case",
            name="airline_motive",
            field=models.CharField(
                max_length=20, choices=AIRLINE_MOTIVE_CHOICES,
                null=True, blank=True,
            ),
        ),
        # 3. Add the check constraint (allows the UNSPECIFIED sentinel too).
        migrations.AddConstraint(
            model_name="case",
            constraint=models.CheckConstraint(
                check=models.Q(disruption_type__in=[
                    "CANCELLATION", "DELAY", "DENIED_BOARDING", "UNSPECIFIED",
                ]),
                name="disruption_type_valid",
            ),
        ),
    ]
```

**Testing:** No new test file for this task — the migration is exercised implicitly by every pytest run (the test DB is created from scratch and every migration must apply cleanly). Coverage of the model fields comes in Task 4.

**Verification:**

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py makemigrations --check --dry-run cases   # must print "No changes detected"
python manage.py migrate cases                            # applies 0003
python -c "from cases.models import Case; f = {f.name for f in Case._meta.get_fields()}; print(sorted(f & {'disruption_type', 'cancellation_notice', 'delay_duration', 'denied_boarding_voluntary', 'denied_boarding_reason', 'airline_motive_mentioned', 'airline_motive', 'incident_description'}))"
# Expect: all 8 field names printed.
```

---

### Task 2: `DisruptionSerializer` with conditional-required matrix

**Files:**
- Modify: `backend/cases/serializers.py` (add class near the bottom, before `PreviewLegSerializer`)

**Requirements:**
- New `DisruptionSerializer` (a plain `serializers.Serializer`, not a `ModelSerializer`).
- Accepts the request shape from spec §4; produces a `validated_data` dict with **only the fields relevant to the chosen `disruption_type`**, converted to storage types (`denied_boarding_voluntary`: `"YES"|"NO"` → `bool`).
- Enforces the invariants listed in spec §3:
  1. Required sub-field per type.
  2. Cross-branch contamination → 400.
  3. `airline_motive_mentioned == "YES"` ⇒ `airline_motive` required.
  4. `denied_boarding_voluntary == False` ⇒ `denied_boarding_reason` required.
  5. `incident_description` non-empty (after strip), 1–2000 chars.
- Error messages match spec §4 wording where quoted; otherwise DRF defaults are fine.

**Implementation:**

Add to `backend/cases/serializers.py` (top-of-file imports first):

```python
from .disruption import (
    AirlineMotive,
    CancellationNotice,
    DelayDuration,
    DeniedBoardingReason,
    DISRUPTION_TYPE_API_VALUES,
    DisruptionType,
    MotiveMentioned,
)
```

Then add the serializer (place it above `PreviewLegSerializer`):

```python
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
```

**Testing:** unit tests for this serializer are in Task 4.

**Verification:**

```powershell
cd backend
python -c "from cases.serializers import DisruptionSerializer; s = DisruptionSerializer(data={'disruption_type': 'DELAY', 'delay_duration': 'MORE_THAN_3H', 'airline_motive_mentioned': 'DONT_KNOW', 'incident_description': 'x'}); print(s.is_valid(), s.errors, s.validated_data if s.is_valid() else '')"
# Expect: True {} {'disruption_type': 'DELAY', 'incident_description': 'x', 'delay_duration': 'MORE_THAN_3H', 'airline_motive_mentioned': 'DONT_KNOW', 'airline_motive': None, 'cancellation_notice': None, 'denied_boarding_voluntary': None, 'denied_boarding_reason': None}
```

---

### Task 3: Wire disruption into `CaseCreateSerializer`, view response, and admin

**Files:**
- Modify: `backend/cases/serializers.py` (add `disruption` field to `CaseCreateSerializer`; extend `create()`)
- Modify: `backend/cases/views.py` (extend 201 response body)
- Modify: `backend/cases/admin.py` (read-only fields + fieldset)

**Requirements:**
- `CaseCreateSerializer` gains a required `disruption` field bound to `DisruptionSerializer`.
- `CaseCreateSerializer.create()` writes the 8 disruption columns onto the new `Case` row inside the existing `@transaction.atomic` block. Uses the cleaned dict from Task 2 — `denied_boarding_voluntary` is already a `bool` or `None`.
- `CaseCreateView.post()` returns a new `disruption` key in the 201 response body. `denied_boarding_voluntary` is serialised back as `"YES"` / `"NO"` / `null`.
- Admin: all 8 fields appear in `readonly_fields` and inside a new `"Disruption"` fieldset (grouped for readability alongside the existing compensation fields).

**Implementation:**

In `backend/cases/serializers.py`, add the field on `CaseCreateSerializer`:

```python
class CaseCreateSerializer(serializers.Serializer):
    passenger = PassengerSerializer()
    reservation_number = serializers.CharField(max_length=30)
    segments = FlightSegmentSerializer(many=True)
    disruption = DisruptionSerializer()
    gdpr_consent = serializers.BooleanField()
```

Extend `CaseCreateSerializer.create()` — inside the existing `Case.objects.create(...)` call, add the 8 disruption kwargs pulled from the cleaned dict:

```python
    @transaction.atomic
    def create(self, validated_data: dict) -> Case:
        passenger = validated_data["passenger"]
        segments = validated_data["segments"]
        disruption = validated_data["disruption"]

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
            disruption_type=disruption["disruption_type"],
            cancellation_notice=disruption["cancellation_notice"],
            delay_duration=disruption["delay_duration"],
            denied_boarding_voluntary=disruption["denied_boarding_voluntary"],
            denied_boarding_reason=disruption["denied_boarding_reason"],
            airline_motive_mentioned=disruption["airline_motive_mentioned"],
            airline_motive=disruption["airline_motive"],
            incident_description=disruption["incident_description"],
        )
        # (rest of the method unchanged — airport lookup + FlightSegment loop)
```

In `backend/cases/views.py`, add a helper module-level function and extend the 201 response body:

```python
def _serialize_disruption(case: Case) -> dict:
    return {
        "disruption_type": case.disruption_type,
        "cancellation_notice": case.cancellation_notice,
        "delay_duration": case.delay_duration,
        "denied_boarding_voluntary": (
            None if case.denied_boarding_voluntary is None
            else ("YES" if case.denied_boarding_voluntary else "NO")
        ),
        "denied_boarding_reason": case.denied_boarding_reason,
        "airline_motive_mentioned": case.airline_motive_mentioned,
        "airline_motive": case.airline_motive,
        "incident_description": case.incident_description,
    }
```

And extend the `return Response({...})` inside `CaseCreateView.post()`:

```python
        return Response(
            {
                "id": str(case.id),
                "status": case.status,
                "created_at": case.created_at.isoformat(),
                "distance_km": (
                    str(case.distance_km) if case.distance_km is not None else None
                ),
                "compensation_amount_eur": case.compensation_amount_eur,
                "compensation_error": compensation_error,
                "disruption": _serialize_disruption(case),
            },
            status=status.HTTP_201_CREATED,
        )
```

In `backend/cases/admin.py`, replace the entire `CaseAdmin` class with:

```python
@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "last_name", "email",
                    "compensation_amount_eur", "disruption_type", "created_at")
    list_filter = ("status", "compensation_amount_eur", "disruption_type")
    search_fields = ("last_name", "email", "reservation_number")
    inlines = [FlightSegmentInline, CaseDocumentInline]
    readonly_fields = (
        "id", "created_at", "updated_at",
        "distance_km", "compensation_amount_eur", "compensation_calculated_at",
        "disruption_type", "cancellation_notice", "delay_duration",
        "denied_boarding_voluntary", "denied_boarding_reason",
        "airline_motive_mentioned", "airline_motive", "incident_description",
    )
    fieldsets = (
        (None, {"fields": ("id", "status", "created_at", "updated_at")}),
        ("Passenger", {"fields": (
            "first_name", "last_name", "date_of_birth", "email", "phone",
            "address", "postal_code",
        )}),
        ("Reservation & consent", {"fields": (
            "reservation_number", "gdpr_consent", "gdpr_consent_at",
        )}),
        ("Compensation", {"fields": (
            "distance_km", "compensation_amount_eur", "compensation_calculated_at",
        )}),
        ("Disruption", {"fields": (
            "disruption_type", "cancellation_notice", "delay_duration",
            "denied_boarding_voluntary", "denied_boarding_reason",
            "airline_motive_mentioned", "airline_motive", "incident_description",
        )}),
    )
```

**Testing:** end-to-end coverage lives in Task 4.

**Verification:**

```powershell
cd backend
python manage.py check                 # no admin/serializer errors
python -c "from cases.admin import CaseAdmin; from cases.models import Case; assert set(CaseAdmin.readonly_fields) >= {'disruption_type', 'incident_description'}; print('ok')"
```

---

### Task 4: Backend tests — serializer matrix, API round-trip, factory + conftest updates

**Files:**
- Create: `backend/cases/tests/test_disruption_serializer.py`
- Modify: `backend/cases/tests/factories.py` (`CaseFactory` gains disruption defaults)
- Modify: `backend/cases/tests/conftest.py` (`valid_payload` gains a `disruption` block)
- Modify: `backend/cases/tests/test_api.py` (three new tests + update the existing happy-path assertion)

**Requirements:**
- Every invariant from spec §3 has at least one positive and one negative test at the serializer level.
- `test_api.py` gets: (a) a 201 test per disruption type verifying the round-trip response shape; (b) a 400 test when `disruption` is missing entirely; (c) an assertion that persisted columns match the request.
- Every pre-existing CASE_01/CASE_02 test must keep passing after `conftest.valid_payload` + `factories.CaseFactory` are updated.

**Implementation:**

Update `backend/cases/tests/factories.py` — extend `CaseFactory`:

```python
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
```

Update `backend/cases/tests/conftest.py` — append a `disruption` block to the returned dict inside `valid_payload`:

```python
@pytest.fixture
def valid_payload():
    return {
        "passenger": { ... },              # unchanged
        "reservation_number": "ABC123",
        "segments": [ ... ],               # unchanged
        "disruption": {
            "disruption_type": "DELAY",
            "delay_duration": "MORE_THAN_3H",
            "airline_motive_mentioned": "DONT_KNOW",
            "incident_description": "Flight was delayed by five hours; missed connection.",
        },
        "gdpr_consent": True,
    }
```

Create `backend/cases/tests/test_disruption_serializer.py`:

```python
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
```

Add three tests to `backend/cases/tests/test_api.py` (append after the existing tests):

```python
import copy


@pytest.mark.django_db
def test_missing_disruption_block_rejected(two_airports, valid_payload):
    payload = copy.deepcopy(valid_payload)
    del payload["disruption"]
    client = APIClient()
    resp = client.post("/api/cases/", _make_multipart(payload), format="multipart")
    assert resp.status_code == 400
    assert "disruption" in resp.json()["payload"]
    assert Case.objects.count() == 0


@pytest.mark.django_db
def test_disruption_round_trip_cancellation(
    two_airports, valid_payload, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    payload = copy.deepcopy(valid_payload)
    payload["disruption"] = {
        "disruption_type": "CANCELLATION",
        "cancellation_notice": "LESS_THAN_14_DAYS",
        "airline_motive_mentioned": "YES",
        "airline_motive": "WEATHER",
        "incident_description": "Cancelled the morning of.",
    }
    client = APIClient()
    from cases.compensation.distance import _AirportGapError
    with patch(
        "cases.compensation.distance._airportgap_km",
        side_effect=_AirportGapError("forced fallback in test"),
    ):
        resp = client.post("/api/cases/", _make_multipart(payload), format="multipart")
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["disruption"] == {
        "disruption_type": "CANCELLATION",
        "cancellation_notice": "LESS_THAN_14_DAYS",
        "delay_duration": None,
        "denied_boarding_voluntary": None,
        "denied_boarding_reason": None,
        "airline_motive_mentioned": "YES",
        "airline_motive": "WEATHER",
        "incident_description": "Cancelled the morning of.",
    }
    case = Case.objects.get(id=body["id"])
    assert case.disruption_type == "CANCELLATION"
    assert case.cancellation_notice == "LESS_THAN_14_DAYS"
    assert case.airline_motive == "WEATHER"
    assert case.delay_duration is None
    assert case.denied_boarding_voluntary is None


@pytest.mark.django_db
def test_disruption_round_trip_denied_boarding_involuntary(
    two_airports, valid_payload, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    payload = copy.deepcopy(valid_payload)
    payload["disruption"] = {
        "disruption_type": "DENIED_BOARDING",
        "denied_boarding_voluntary": "NO",
        "denied_boarding_reason": "OVERBOOKED",
        "incident_description": "Denied at the gate — overbooking.",
    }
    client = APIClient()
    from cases.compensation.distance import _AirportGapError
    with patch(
        "cases.compensation.distance._airportgap_km",
        side_effect=_AirportGapError("forced fallback in test"),
    ):
        resp = client.post("/api/cases/", _make_multipart(payload), format="multipart")
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["disruption"]["denied_boarding_voluntary"] == "NO"
    assert body["disruption"]["denied_boarding_reason"] == "OVERBOOKED"
    assert body["disruption"]["airline_motive_mentioned"] is None
    case = Case.objects.get(id=body["id"])
    assert case.denied_boarding_voluntary is False
    assert case.denied_boarding_reason == "OVERBOOKED"


@pytest.mark.django_db
def test_existing_happy_path_now_persists_disruption(
    two_airports, valid_payload, settings, tmp_path,
):
    """Sanity-check that the shared happy-path fixture writes disruption too."""
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()
    from cases.compensation.distance import _AirportGapError
    with patch(
        "cases.compensation.distance._airportgap_km",
        side_effect=_AirportGapError("forced fallback in test"),
    ):
        resp = client.post("/api/cases/", _make_multipart(valid_payload), format="multipart")
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["disruption"]["disruption_type"] == "DELAY"
    assert body["disruption"]["delay_duration"] == "MORE_THAN_3H"
```

**Verification:**

```powershell
cd backend
pytest -x                 # every existing test + the new ones must pass
pytest -q cases/tests/test_disruption_serializer.py   # 15+ tests, all green
```

---

### Task 5: Frontend enum constants + type extensions

**Files:**
- Create: `frontend/src/features/case-entry/disruption.ts`
- Modify: `frontend/src/features/case-entry/types.ts`

**Requirements:**
- One module holds the canonical enum literals **as `const` tuples** so both Zod (`z.enum([...])`) and the section component consume them.
- Label maps (English) keyed by the enum literal — one per field.
- `DESCRIPTION_MAX_LENGTH = 2000`.
- `CasePayload` gains `disruption: DisruptionInput`.
- `CaseCreateResponse` gains `disruption: DisruptionResponse` (mirror shape from spec §4, with `denied_boarding_voluntary: "YES" | "NO" | null`).

**Implementation:**

`frontend/src/features/case-entry/disruption.ts`:

```typescript
export const DISRUPTION_TYPES = ["CANCELLATION", "DELAY", "DENIED_BOARDING"] as const;
export type DisruptionType = typeof DISRUPTION_TYPES[number];

export const CANCELLATION_NOTICES = [
  "MORE_THAN_14_DAYS", "LESS_THAN_14_DAYS", "ON_FLIGHT_DAY",
] as const;
export type CancellationNotice = typeof CANCELLATION_NOTICES[number];

export const DELAY_DURATIONS = [
  "LESS_THAN_3H", "MORE_THAN_3H", "CONNECTION_LOST",
] as const;
export type DelayDuration = typeof DELAY_DURATIONS[number];

export const DENIED_BOARDING_REASONS = [
  "OVERBOOKED", "AGGRESSIVE_BEHAVIOR", "INTOXICATION", "UNSPECIFIED",
] as const;
export type DeniedBoardingReason = typeof DENIED_BOARDING_REASONS[number];

export const MOTIVE_MENTIONED = ["YES", "NO", "DONT_KNOW"] as const;
export type MotiveMentioned = typeof MOTIVE_MENTIONED[number];

export const AIRLINE_MOTIVES = [
  "TECHNICAL", "WEATHER", "STRIKE", "AIRPORT_ISSUE", "CREW", "OTHER",
] as const;
export type AirlineMotive = typeof AIRLINE_MOTIVES[number];

export const VOLUNTARY_CHOICES = ["YES", "NO"] as const;
export type VoluntaryChoice = typeof VOLUNTARY_CHOICES[number];

export const DESCRIPTION_MAX_LENGTH = 2000;

export const LABELS = {
  disruption_type: {
    CANCELLATION: "Cancellation",
    DELAY: "Delay",
    DENIED_BOARDING: "Denied boarding",
  },
  cancellation_notice: {
    MORE_THAN_14_DAYS: "More than 14 days before",
    LESS_THAN_14_DAYS: "Less than 14 days before",
    ON_FLIGHT_DAY: "On the flight day",
  },
  delay_duration: {
    LESS_THAN_3H: "Less than 3 hours",
    MORE_THAN_3H: "More than 3 hours",
    CONNECTION_LOST: "Connection flight lost",
  },
  denied_boarding_reason: {
    OVERBOOKED: "Flight overbooked",
    AGGRESSIVE_BEHAVIOR: "Aggressive behaviour with staff",
    INTOXICATION: "Intoxication",
    UNSPECIFIED: "Unspecified reason",
  },
  motive_mentioned: {
    YES: "Yes",
    NO: "No",
    DONT_KNOW: "I don't know",
  },
  airline_motive: {
    TECHNICAL: "Technical problem",
    WEATHER: "Meteorological conditions",
    STRIKE: "Strike",
    AIRPORT_ISSUE: "Problems with airport",
    CREW: "Crew problems",
    OTHER: "Other motives",
  },
  voluntary: {
    YES: "Yes",
    NO: "No",
  },
} as const;
```

Extend `frontend/src/features/case-entry/types.ts`:

```typescript
import type {
  AirlineMotive,
  CancellationNotice,
  DelayDuration,
  DeniedBoardingReason,
  DisruptionType,
  MotiveMentioned,
  VoluntaryChoice,
} from "./disruption";

// ... existing PassengerInput, FlightSegmentInput unchanged ...

export type DisruptionInput =
  | {
      disruption_type: "CANCELLATION";
      cancellation_notice: CancellationNotice;
      airline_motive_mentioned: MotiveMentioned;
      airline_motive: AirlineMotive | null;
      incident_description: string;
    }
  | {
      disruption_type: "DELAY";
      delay_duration: DelayDuration;
      airline_motive_mentioned: MotiveMentioned;
      airline_motive: AirlineMotive | null;
      incident_description: string;
    }
  | {
      disruption_type: "DENIED_BOARDING";
      denied_boarding_voluntary: VoluntaryChoice;
      denied_boarding_reason: DeniedBoardingReason | null;
      incident_description: string;
    };

export interface CasePayload {
  passenger: PassengerInput;
  reservation_number: string;
  segments: FlightSegmentInput[];
  disruption: DisruptionInput;
  gdpr_consent: boolean;
}

export interface DisruptionResponse {
  disruption_type: DisruptionType;
  cancellation_notice: CancellationNotice | null;
  delay_duration: DelayDuration | null;
  denied_boarding_voluntary: "YES" | "NO" | null;
  denied_boarding_reason: DeniedBoardingReason | null;
  airline_motive_mentioned: MotiveMentioned | null;
  airline_motive: AirlineMotive | null;
  incident_description: string;
}

export interface CaseCreateResponse {
  id: string;
  status: "NEW" | "VALID" | "ASSIGNED" | "INVALID";
  created_at: string;
  distance_km: string | number | null;
  compensation_amount_eur: 250 | 400 | 600 | null;
  compensation_error: string | null;
  disruption: DisruptionResponse;
}

// AirportOption unchanged.
```

**Testing:** covered by Tasks 6 + 8.

**Verification:**

```powershell
cd frontend
npx tsc --noEmit
# Expect: no errors from disruption.ts or types.ts.
```

---

### Task 6: Zod schema — `disruptionSchema` discriminated union + merge into `caseFormSchema`

**Files:**
- Modify: `frontend/src/features/case-entry/schema.ts`

**Requirements:**
- New `disruptionSchema` as a `z.discriminatedUnion("disruption_type", [...])` with one branch per type.
- Each branch enforces its required sub-fields; conditional fields (`airline_motive`, `denied_boarding_reason`) use a `.superRefine`/`.refine` to require them when the trigger value is set.
- `incident_description` reused across all branches: trimmed, 1–2000 chars.
- The empty initial discriminator (form starts before the user picks a type) makes Zod fail — this is the intended blocker on submit.
- `caseFormSchema` gains a top-level `disruption: disruptionSchema` field.

**Implementation:**

Add to `frontend/src/features/case-entry/schema.ts`:

```typescript
import {
  AIRLINE_MOTIVES,
  CANCELLATION_NOTICES,
  DELAY_DURATIONS,
  DENIED_BOARDING_REASONS,
  DESCRIPTION_MAX_LENGTH,
  MOTIVE_MENTIONED,
  VOLUNTARY_CHOICES,
} from "./disruption";

const descriptionField = z
  .string()
  .transform((v) => v.trim())
  .pipe(
    z
      .string()
      .min(1, "Required.")
      .max(
        DESCRIPTION_MAX_LENGTH,
        `Description must be ${DESCRIPTION_MAX_LENGTH} characters or fewer.`,
      ),
  );

const cancellationBranch = z
  .object({
    disruption_type: z.literal("CANCELLATION"),
    cancellation_notice: z.enum(CANCELLATION_NOTICES, { message: "Required." }),
    airline_motive_mentioned: z.enum(MOTIVE_MENTIONED, { message: "Required." }),
    airline_motive: z.enum(AIRLINE_MOTIVES).nullable(),
    incident_description: descriptionField,
  })
  .superRefine((v, ctx) => {
    if (v.airline_motive_mentioned === "YES" && v.airline_motive === null) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["airline_motive"],
        message: "Required.",
      });
    }
  });

const delayBranch = z
  .object({
    disruption_type: z.literal("DELAY"),
    delay_duration: z.enum(DELAY_DURATIONS, { message: "Required." }),
    airline_motive_mentioned: z.enum(MOTIVE_MENTIONED, { message: "Required." }),
    airline_motive: z.enum(AIRLINE_MOTIVES).nullable(),
    incident_description: descriptionField,
  })
  .superRefine((v, ctx) => {
    if (v.airline_motive_mentioned === "YES" && v.airline_motive === null) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["airline_motive"],
        message: "Required.",
      });
    }
  });

const deniedBoardingBranch = z
  .object({
    disruption_type: z.literal("DENIED_BOARDING"),
    denied_boarding_voluntary: z.enum(VOLUNTARY_CHOICES, { message: "Required." }),
    denied_boarding_reason: z.enum(DENIED_BOARDING_REASONS).nullable(),
    incident_description: descriptionField,
  })
  .superRefine((v, ctx) => {
    if (v.denied_boarding_voluntary === "NO" && v.denied_boarding_reason === null) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["denied_boarding_reason"],
        message: "Required.",
      });
    }
  });

export const disruptionSchema = z.discriminatedUnion("disruption_type", [
  cancellationBranch, delayBranch, deniedBoardingBranch,
]);

export const caseFormSchema = z
  .object({
    passenger: passengerSchema,
    reservation_number: z.string().min(1, "Required.").max(30),
    segments: z.array(segmentSchema).min(1).max(5),
    disruption: disruptionSchema,
    gdpr_consent: z
      .boolean()
      .refine((v) => v === true, {
        message: "You must accept the GDPR policy to submit.",
      }),
    boarding_pass: fileValidator(),
    id_document: fileValidator(),
  })
  .refine(
    (v) => v.segments.filter((s) => s.is_problem_flight).length === 1,
    {
      path: ["segments"],
      message: "Exactly one segment must be marked as the problem flight.",
    },
  );

export type CaseFormValues = z.infer<typeof caseFormSchema>;
```

Note: the schema now type-safely widens to a discriminated union. Because `emptyValues.disruption` in `CaseEntryForm.tsx` starts with an empty `disruption_type: ""`, we deliberately cast in Task 7 (see below) — same pattern the existing form uses for `File` defaults.

**Verification:**

```powershell
cd frontend
npx tsc --noEmit
# Expect: no schema errors; CaseFormValues now includes `disruption` as a discriminated union.
```

---

### Task 7: `DisruptionSection` component + form wiring

**Files:**
- Create: `frontend/src/features/case-entry/sections/DisruptionSection.tsx`
- Modify: `frontend/src/features/case-entry/CaseEntryForm.tsx` (import + render + update `emptyValues`)

**Requirements:**
- The section shows only the `disruption_type` dropdown initially.
- Picking a type reveals only that branch's fields; switching type resets the disruption sub-tree so no stale values leak.
- Description textarea shows a live `n / 2000` counter.
- Uses the existing `sections.module.css` classes for layout consistency.
- Field labels/options come from `disruption.ts` `LABELS`.
- Error messages come from RHF's `errors` tree at `errors.disruption.<field>?.message`.

**Implementation:**

`frontend/src/features/case-entry/sections/DisruptionSection.tsx`:

```tsx
import { useEffect } from "react";
import { useFormContext, useWatch } from "react-hook-form";

import type { CaseFormValues } from "../schema";
import {
  AIRLINE_MOTIVES,
  CANCELLATION_NOTICES,
  DELAY_DURATIONS,
  DENIED_BOARDING_REASONS,
  DESCRIPTION_MAX_LENGTH,
  DISRUPTION_TYPES,
  LABELS,
  MOTIVE_MENTIONED,
  VOLUNTARY_CHOICES,
} from "../disruption";
import styles from "./sections.module.css";


type DisruptionErrors = {
  disruption_type?: { message?: string };
  cancellation_notice?: { message?: string };
  delay_duration?: { message?: string };
  denied_boarding_voluntary?: { message?: string };
  denied_boarding_reason?: { message?: string };
  airline_motive_mentioned?: { message?: string };
  airline_motive?: { message?: string };
  incident_description?: { message?: string };
};


export function DisruptionSection() {
  const { register, control, resetField, formState: { errors } } =
    useFormContext<CaseFormValues>();
  const d = (errors.disruption ?? {}) as DisruptionErrors;

  const type = useWatch({ control, name: "disruption.disruption_type" }) as
    | "" | "CANCELLATION" | "DELAY" | "DENIED_BOARDING" | undefined;
  const mentioned = useWatch({ control, name: "disruption.airline_motive_mentioned" as never });
  const voluntary = useWatch({ control, name: "disruption.denied_boarding_voluntary" as never });
  const description = useWatch({ control, name: "disruption.incident_description" as never }) ?? "";

  // Clear stale branch fields whenever the discriminator changes. RHF's
  // resetField with a keepDirty:false wipes descendants; we then re-seed the
  // discriminator to the newly-picked value so the union re-validates.
  useEffect(() => {
    if (!type) return;
    resetField("disruption", {
      defaultValue: {
        disruption_type: type,
        incident_description: "",
        // Explicit nulls for all optional fields so RHF doesn't retain values
        // from the previously-selected branch.
        cancellation_notice: null as never,
        delay_duration: null as never,
        denied_boarding_voluntary: null as never,
        denied_boarding_reason: null as never,
        airline_motive_mentioned: null as never,
        airline_motive: null as never,
      },
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type]);

  const charCount = typeof description === "string" ? description.length : 0;

  return (
    <section className={styles.section} aria-labelledby="disruption-heading">
      <h2 id="disruption-heading">Disruption information</h2>

      <div className={styles.field}>
        <label htmlFor="disruption-type">Disruption type</label>
        <select
          id="disruption-type"
          {...register("disruption.disruption_type" as never)}
          defaultValue=""
        >
          <option value="" disabled>Select a disruption type…</option>
          {DISRUPTION_TYPES.map((t) => (
            <option key={t} value={t}>{LABELS.disruption_type[t]}</option>
          ))}
        </select>
        {d.disruption_type?.message && (
          <p className={styles.error}>{d.disruption_type.message}</p>
        )}
      </div>

      {type === "CANCELLATION" && (
        <div className={styles.field}>
          <label htmlFor="cancellation-notice">
            How many days before cancellation did the airline inform you?
          </label>
          <select
            id="cancellation-notice"
            {...register("disruption.cancellation_notice" as never)}
            defaultValue=""
          >
            <option value="" disabled>Select…</option>
            {CANCELLATION_NOTICES.map((v) => (
              <option key={v} value={v}>{LABELS.cancellation_notice[v]}</option>
            ))}
          </select>
          {d.cancellation_notice?.message && (
            <p className={styles.error}>{d.cancellation_notice.message}</p>
          )}
        </div>
      )}

      {type === "DELAY" && (
        <div className={styles.field}>
          <label htmlFor="delay-duration">
            How late did you arrive at your final destination?
          </label>
          <select
            id="delay-duration"
            {...register("disruption.delay_duration" as never)}
            defaultValue=""
          >
            <option value="" disabled>Select…</option>
            {DELAY_DURATIONS.map((v) => (
              <option key={v} value={v}>{LABELS.delay_duration[v]}</option>
            ))}
          </select>
          {d.delay_duration?.message && (
            <p className={styles.error}>{d.delay_duration.message}</p>
          )}
        </div>
      )}

      {type === "DENIED_BOARDING" && (
        <>
          <div className={styles.field}>
            <label htmlFor="voluntary">Did you give up your seat voluntarily?</label>
            <select
              id="voluntary"
              {...register("disruption.denied_boarding_voluntary" as never)}
              defaultValue=""
            >
              <option value="" disabled>Select…</option>
              {VOLUNTARY_CHOICES.map((v) => (
                <option key={v} value={v}>{LABELS.voluntary[v]}</option>
              ))}
            </select>
            {d.denied_boarding_voluntary?.message && (
              <p className={styles.error}>{d.denied_boarding_voluntary.message}</p>
            )}
          </div>
          {voluntary === "NO" && (
            <div className={styles.field}>
              <label htmlFor="denied-reason">Reason behind denial of boarding</label>
              <select
                id="denied-reason"
                {...register("disruption.denied_boarding_reason" as never)}
                defaultValue=""
              >
                <option value="" disabled>Select…</option>
                {DENIED_BOARDING_REASONS.map((v) => (
                  <option key={v} value={v}>{LABELS.denied_boarding_reason[v]}</option>
                ))}
              </select>
              {d.denied_boarding_reason?.message && (
                <p className={styles.error}>{d.denied_boarding_reason.message}</p>
              )}
            </div>
          )}
        </>
      )}

      {(type === "CANCELLATION" || type === "DELAY") && (
        <>
          <div className={styles.field}>
            <label htmlFor="motive-mentioned">
              Did the airline mention a disruption motive?
            </label>
            <select
              id="motive-mentioned"
              {...register("disruption.airline_motive_mentioned" as never)}
              defaultValue=""
            >
              <option value="" disabled>Select…</option>
              {MOTIVE_MENTIONED.map((v) => (
                <option key={v} value={v}>{LABELS.motive_mentioned[v]}</option>
              ))}
            </select>
            {d.airline_motive_mentioned?.message && (
              <p className={styles.error}>{d.airline_motive_mentioned.message}</p>
            )}
          </div>
          {mentioned === "YES" && (
            <div className={styles.field}>
              <label htmlFor="airline-motive">
                What was the motive communicated by the airline?
              </label>
              <select
                id="airline-motive"
                {...register("disruption.airline_motive" as never)}
                defaultValue=""
              >
                <option value="" disabled>Select…</option>
                {AIRLINE_MOTIVES.map((v) => (
                  <option key={v} value={v}>{LABELS.airline_motive[v]}</option>
                ))}
              </select>
              {d.airline_motive?.message && (
                <p className={styles.error}>{d.airline_motive.message}</p>
              )}
            </div>
          )}
        </>
      )}

      {type && (
        <div className={styles.field}>
          <label htmlFor="incident-description">
            Describe briefly what happened
          </label>
          <textarea
            id="incident-description"
            rows={5}
            maxLength={DESCRIPTION_MAX_LENGTH}
            {...register("disruption.incident_description" as never)}
          />
          <small>{charCount} / {DESCRIPTION_MAX_LENGTH}</small>
          {d.incident_description?.message && (
            <p className={styles.error}>{d.incident_description.message}</p>
          )}
        </div>
      )}
    </section>
  );
}
```

Modify `frontend/src/features/case-entry/CaseEntryForm.tsx` — add the import:

```typescript
import { DisruptionSection } from "./sections/DisruptionSection";
```

Update `emptyValues` (only the disruption block is new — everything else is unchanged):

```typescript
const emptyValues: CaseFormValues = {
  passenger: {
    first_name: "",
    last_name: "",
    date_of_birth: "",
    email: "",
    phone: "",
    address: "",
    postal_code: "",
  },
  reservation_number: "",
  segments: [
    {
      order: 0,
      flight_date: "",
      flight_number: "",
      airline: "",
      departure_airport_iata: "",
      arrival_airport_iata: "",
      planned_departure_time: "",
      planned_arrival_time: "",
      is_problem_flight: true,
    },
  ],
  // Disruption starts with an empty discriminator so Zod blocks submission
  // until the user picks a type — same pattern the file fields use.
  disruption: {
    disruption_type: "" as unknown as "DELAY",
    incident_description: "",
  } as unknown as CaseFormValues["disruption"],
  gdpr_consent: false,
  boarding_pass: undefined as unknown as File,
  id_document: undefined as unknown as File,
};
```

Insert `<DisruptionSection/>` in the form JSX **after `<ConnectingFlightsSection/>` and before `<PassengerDetailsSection/>`**:

```tsx
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <FlightItinerarySection />
          <ConnectingFlightsSection />
          <DisruptionSection />
          <PassengerDetailsSection />
          <DocumentsSection />
          <GdprSection />
          <CompensationSummary />
          <button ...>
```

**Verification:**

```powershell
cd frontend
npx tsc --noEmit
npm run dev   # optional smoke: pick each disruption type in the browser
```

---

### Task 8: Frontend tests — `DisruptionSection.test.tsx` + extend `CaseEntryForm.test.tsx`

**Files:**
- Create: `frontend/tests/DisruptionSection.test.tsx`
- Modify: `frontend/tests/CaseEntryForm.test.tsx` (extend the happy-path test to fill the disruption block)

**Requirements:**
- Component tests use a small harness that wraps `DisruptionSection` in `FormProvider` with `caseFormSchema` and the same `emptyValues.disruption` as the real form.
- Cover: initial render (only type dropdown visible); each type reveals the correct fields; switching type clears the previous branch; `airline_motive` shows only when `mentioned == "YES"`; `denied_boarding_reason` shows only when `voluntary == "NO"`; description counter updates.
- The existing happy-path test in `CaseEntryForm.test.tsx` gains steps that pick `DELAY` + `MORE_THAN_3H` + `DONT_KNOW` + type a description, before submitting.
- Add one new integration test: the existing "renders all five sections" is updated to "renders all six sections" including `disruption information`.

**Implementation:**

Create `frontend/tests/DisruptionSection.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { zodResolver } from "@hookform/resolvers/zod";
import { FormProvider, useForm } from "react-hook-form";

import { DisruptionSection } from "../src/features/case-entry/sections/DisruptionSection";
import { caseFormSchema, type CaseFormValues } from "../src/features/case-entry/schema";


function Harness() {
  const methods = useForm<CaseFormValues>({
    resolver: zodResolver(caseFormSchema),
    defaultValues: {
      // Only the disruption defaults matter for these tests; other fields are
      // required by the type but not rendered here.
      disruption: {
        disruption_type: "" as unknown as "DELAY",
        incident_description: "",
      } as unknown as CaseFormValues["disruption"],
    } as CaseFormValues,
    mode: "onTouched",
  });
  return (
    <FormProvider {...methods}>
      <form>
        <DisruptionSection />
      </form>
    </FormProvider>
  );
}


describe("DisruptionSection", () => {
  it("renders only the type dropdown initially", () => {
    render(<Harness />);
    expect(screen.getByLabelText(/disruption type/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/how many days before/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/how late did you arrive/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/voluntarily/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/describe briefly/i)).not.toBeInTheDocument();
  });

  it("reveals cancellation fields when CANCELLATION picked", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.selectOptions(screen.getByLabelText(/disruption type/i), "CANCELLATION");
    expect(await screen.findByLabelText(/how many days before/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/did the airline mention/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/describe briefly/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/how late did you arrive/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/voluntarily/i)).not.toBeInTheDocument();
  });

  it("reveals delay fields when DELAY picked", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.selectOptions(screen.getByLabelText(/disruption type/i), "DELAY");
    expect(await screen.findByLabelText(/how late did you arrive/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/did the airline mention/i)).toBeInTheDocument();
  });

  it("reveals denied-boarding fields when DENIED_BOARDING picked; reason appears on NO", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.selectOptions(screen.getByLabelText(/disruption type/i), "DENIED_BOARDING");
    const vol = await screen.findByLabelText(/voluntarily/i);
    expect(vol).toBeInTheDocument();
    expect(screen.queryByLabelText(/reason behind denial/i)).not.toBeInTheDocument();
    await user.selectOptions(vol, "NO");
    expect(await screen.findByLabelText(/reason behind denial/i)).toBeInTheDocument();
    // Motive-mentioned dropdown does NOT appear for denied boarding.
    expect(screen.queryByLabelText(/did the airline mention/i)).not.toBeInTheDocument();
  });

  it("reveals airline_motive only when airline_motive_mentioned == YES", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.selectOptions(screen.getByLabelText(/disruption type/i), "DELAY");
    const mentioned = await screen.findByLabelText(/did the airline mention/i);
    await user.selectOptions(mentioned, "NO");
    expect(screen.queryByLabelText(/what was the motive/i)).not.toBeInTheDocument();
    await user.selectOptions(mentioned, "YES");
    expect(await screen.findByLabelText(/what was the motive/i)).toBeInTheDocument();
  });

  it("clears delay_duration when switching from DELAY to CANCELLATION", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.selectOptions(screen.getByLabelText(/disruption type/i), "DELAY");
    const dur = await screen.findByLabelText(/how late did you arrive/i);
    await user.selectOptions(dur, "MORE_THAN_3H");
    expect((dur as HTMLSelectElement).value).toBe("MORE_THAN_3H");
    await user.selectOptions(screen.getByLabelText(/disruption type/i), "CANCELLATION");
    // DELAY-only field disappears; if the user switches back it must be blank.
    await waitFor(() =>
      expect(screen.queryByLabelText(/how late did you arrive/i)).not.toBeInTheDocument(),
    );
    await user.selectOptions(screen.getByLabelText(/disruption type/i), "DELAY");
    const durAgain = await screen.findByLabelText(/how late did you arrive/i);
    expect((durAgain as HTMLSelectElement).value).toBe("");
  });

  it("shows a live n / 2000 character counter for the description", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.selectOptions(screen.getByLabelText(/disruption type/i), "DELAY");
    const desc = await screen.findByLabelText(/describe briefly/i);
    expect(screen.getByText(/^0 \/ 2000$/)).toBeInTheDocument();
    await user.type(desc, "hello");
    await waitFor(() =>
      expect(screen.getByText(/^5 \/ 2000$/)).toBeInTheDocument(),
    );
  });
});
```

Modify `frontend/tests/CaseEntryForm.test.tsx`:

- Update the "renders all five sections" test:

```tsx
  it("renders all six sections including disruption", () => {
    render(<CaseEntryForm />);
    expect(screen.getByRole("heading", { name: /primary flight itinerary/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /connecting flights/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /disruption information/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /passenger details/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /documents/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /gdpr/i })).toBeInTheDocument();
  });
```

- Extend the "maps server 400 field errors" test — insert the disruption steps **after** the segment inputs are filled and **before** the file uploads:

```tsx
    // --- CASE_03 disruption ---
    await user.selectOptions(screen.getByLabelText(/disruption type/i), "DELAY");
    await user.selectOptions(
      await screen.findByLabelText(/how late did you arrive/i),
      "MORE_THAN_3H",
    );
    await user.selectOptions(
      screen.getByLabelText(/did the airline mention/i),
      "DONT_KNOW",
    );
    await user.type(
      screen.getByLabelText(/describe briefly/i),
      "Flight was delayed five hours; missed connection.",
    );
```

- Update the "shows the compensation amount on the success view" test the same way (add the same 4 disruption steps before the file uploads).

**Verification:**

```powershell
cd frontend
npm test -- --run
# Expect: DisruptionSection.test.tsx passes (7 tests); CaseEntryForm.test.tsx still green.
```

---

## Self-Review Summary

**Spec coverage:**
- §3 data model (8 fields, CheckConstraint, backfill) → Task 1 ✅
- §3 invariants (conditional-required matrix) → Task 2 (implementation) + Task 4 (tests) ✅
- §4 API request shape (nested disruption, choice enforcement, cross-branch rejection) → Task 2 ✅
- §4 API response shape (mirror + voluntary↔string conversion) → Task 3 ✅
- §3 admin visibility → Task 3 ✅
- §5 frontend constants + label maps → Task 5 ✅
- §5 Zod discriminated union → Task 6 ✅
- §5 DisruptionSection with conditional rendering + field reset → Task 7 ✅
- §5 form wiring (placement after Connecting flights) → Task 7 ✅
- §7 backend tests coverage matrix → Task 4 ✅
- §7 frontend tests coverage → Task 8 ✅
- §8 migration rollback path — implicit (a single `AddField/AddConstraint`-only migration is reversible via `migrate cases 0002`); no explicit reverse code needed ✅

**Placeholder scan:** no TBD/TODO/placeholder text; every task shows the actual code to write and the exact verification command.

**Type consistency:**
- Enum string literals identical between backend `TextChoices`, frontend `disruption.ts` constants, Zod `z.enum`, and TypeScript unions.
- `denied_boarding_voluntary` API shape (`"YES" | "NO" | null`) matches on both request (Task 2), response (Task 3), and frontend type (Task 5).
- Serializer helper function `_serialize_disruption` (Task 3) returns exactly the keys defined by `DisruptionResponse` (Task 5).
- Field paths in DisruptionSection (`"disruption.<field>"`) match RHF's schema paths from Task 6.
