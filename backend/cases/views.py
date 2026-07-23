from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .compensation import DistanceUnavailable, compute_for_case, preview_from_legs
from .models import Case, CaseDocument, DocumentKind
from .serializers import CaseCreateSerializer, PreviewRequestSerializer, parse_payload_field
from .validators import validate_upload


class CaseCreateThrottle(AnonRateThrottle):
    scope = "case_create"


DOC_FIELDS = (("boarding_pass", DocumentKind.BOARDING_PASS),
              ("id_document",   DocumentKind.ID_DOCUMENT))


class CaseCreateView(APIView):
    parser_classes = [MultiPartParser]
    throttle_classes = [CaseCreateThrottle]

    def post(self, request, *args, **kwargs):
        # --- Phase A: validate everything, write nothing ---
        raw_payload = request.data.get("payload")
        if raw_payload is None:
            raise DRFValidationError({"payload": ["This field is required."]})
        payload_data = parse_payload_field(raw_payload)

        payload_ser = CaseCreateSerializer(data=payload_data)
        payload_valid = payload_ser.is_valid()

        file_errors: dict[str, list[str]] = {}
        detected_mime: dict[str, str] = {}
        for field, _ in DOC_FIELDS:
            file_obj = request.FILES.get(field)
            if file_obj is None:
                file_errors[field] = ["This file is required."]
                continue
            try:
                detected_mime[field] = validate_upload(file_obj)
            except DjangoValidationError as exc:
                file_errors[field] = list(exc.messages)

        if not payload_valid or file_errors:
            errors: dict = {}
            if not payload_valid:
                errors["payload"] = payload_ser.errors
            errors.update(file_errors)
            raise DRFValidationError(errors)

        # --- Phase B: persist inside a transaction with file-rollback ---
        written_paths: list[str] = []
        compensation_error: str | None = None
        try:
            with transaction.atomic():
                case: Case = payload_ser.save()

                # Compensation calc: never blocks case creation. A
                # DistanceUnavailable leaves the three fields NULL and surfaces
                # a soft error on the response; any other exception uses the
                # existing rollback path below.
                try:
                    compute_for_case(case)
                    case.save(update_fields=[
                        "distance_km",
                        "compensation_amount_eur",
                        "compensation_calculated_at",
                    ])
                except DistanceUnavailable:
                    compensation_error = (
                        "Distance could not be calculated; "
                        "you can review this case later."
                    )

                for field, kind in DOC_FIELDS:
                    file_obj = request.FILES[field]
                    doc = CaseDocument(
                        case=case,
                        kind=kind,
                        original_filename=file_obj.name,
                        content_type=detected_mime[field],
                        size_bytes=file_obj.size,
                    )
                    # Save file first (records path on the instance), then row.
                    doc.file.save(file_obj.name, file_obj, save=False)
                    written_paths.append(doc.file.name)
                    doc.save()
        except Exception:
            _cleanup_files(written_paths)
            raise

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
            },
            status=status.HTTP_201_CREATED,
        )


def _cleanup_files(paths: Iterable[str]) -> None:
    from django.core.files.storage import default_storage
    for p in paths:
        try:
            if default_storage.exists(p):
                default_storage.delete(p)
        except Exception:  # pragma: no cover
            pass


class CompensationPreviewThrottle(AnonRateThrottle):
    scope = "compensation_preview"


def _decimals_to_str(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _decimals_to_str(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_decimals_to_str(v) for v in value]
    return value


class CompensationPreviewView(APIView):
    parser_classes = [JSONParser]
    throttle_classes = [CompensationPreviewThrottle]

    def post(self, request, *args, **kwargs):
        serializer = PreviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            body = preview_from_legs(serializer.validated_data["legs"])
        except DistanceUnavailable as exc:
            payload = exc.payload if exc.payload is not None else {
                "detail": str(exc),
                "legs": [],
            }
            return Response(
                _decimals_to_str(payload),
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(_decimals_to_str(body), status=status.HTTP_200_OK)
