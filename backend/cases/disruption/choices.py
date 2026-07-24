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
