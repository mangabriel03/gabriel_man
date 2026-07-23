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
    list_display = ("id", "status", "last_name", "email", "created_at")
    list_filter = ("status",)
    search_fields = ("last_name", "email", "reservation_number")
    inlines = [FlightSegmentInline, CaseDocumentInline]
    readonly_fields = ("id", "created_at", "updated_at")
