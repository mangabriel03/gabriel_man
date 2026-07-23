from __future__ import annotations

from typing import Iterable

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .models import Case, CaseDocument, DocumentKind
from .serializers import CaseCreateSerializer, parse_payload_field
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
        try:
            with transaction.atomic():
                case: Case = payload_ser.save()
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
