from django.contrib import admin

from .models import Case, CaseDocument, FlightSegment


class FlightSegmentInline(admin.TabularInline):
    model = FlightSegment
    extra = 0


class CaseDocumentInline(admin.TabularInline):
    model = CaseDocument
    extra = 0
    readonly_fields = ("file", "original_filename", "content_type",
                       "size_bytes", "uploaded_at")


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
