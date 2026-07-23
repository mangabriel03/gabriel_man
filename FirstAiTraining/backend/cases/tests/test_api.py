from __future__ import annotations

import base64
import json
from io import BytesIO
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from rest_framework.test import APIClient

from cases.models import Case, CaseDocument


# Minimal valid 1x1 PNG (with IHDR + IDAT + IEND chunks) — libmagic requires
# more than the 8-byte signature to reliably detect image/png.
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)
PDF_BYTES = b"%PDF-1.4\n" + b"\x00" * 32


def _make_multipart(payload: dict) -> dict:
    return {
        "payload": json.dumps(payload),
        "boarding_pass": SimpleUploadedFile(
            "bp.png", PNG_BYTES, content_type="image/png"
        ),
        "id_document": SimpleUploadedFile(
            "id.pdf", PDF_BYTES, content_type="application/pdf"
        ),
    }


@pytest.mark.django_db
def test_happy_path_creates_case_with_files(two_airports, valid_payload, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()
    resp = client.post("/api/cases/", _make_multipart(valid_payload), format="multipart")
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert "id" in body and body["status"] == "NEW"

    case = Case.objects.get(id=body["id"])
    assert case.segments.count() == 1
    assert case.documents.count() == 2
    for doc in case.documents.all():
        assert Path(default_storage.path(doc.file.name)).exists()


@pytest.mark.django_db
def test_missing_boarding_pass_rejected(two_airports, valid_payload):
    client = APIClient()
    data = _make_multipart(valid_payload)
    del data["boarding_pass"]
    resp = client.post("/api/cases/", data, format="multipart")
    assert resp.status_code == 400
    assert "boarding_pass" in resp.json()
    assert Case.objects.count() == 0


@pytest.mark.django_db
def test_bad_payload_returns_field_errors(two_airports, valid_payload):
    valid_payload["gdpr_consent"] = False
    client = APIClient()
    resp = client.post("/api/cases/", _make_multipart(valid_payload), format="multipart")
    assert resp.status_code == 400
    assert "gdpr_consent" in resp.json()["payload"]
    assert Case.objects.count() == 0


@pytest.mark.django_db
def test_oversized_file_causes_full_rollback(two_airports, valid_payload, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()
    data = _make_multipart(valid_payload)
    huge = SimpleUploadedFile(
        "bp.pdf", b"\x00" * (5 * 1024 * 1024 + 1), content_type="application/pdf"
    )
    data["boarding_pass"] = huge
    resp = client.post("/api/cases/", data, format="multipart")
    assert resp.status_code == 400
    assert Case.objects.count() == 0
    assert CaseDocument.objects.count() == 0
