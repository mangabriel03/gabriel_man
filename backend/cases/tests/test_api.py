from __future__ import annotations

import base64
import json
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework.test import APIClient

from cases.compensation.exceptions import DistanceUnavailable
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
    # Force the Airport Gap primary source to fail so the deterministic
    # Haversine fallback runs against the seeded lat/lon in ``two_airports``.
    # This keeps the test hermetic (no network) while still exercising the
    # real compensation pipeline end-to-end.
    from cases.compensation.distance import _AirportGapError
    with patch(
        "cases.compensation.distance._airportgap_km",
        side_effect=_AirportGapError("forced fallback in test"),
    ):
        resp = client.post("/api/cases/", _make_multipart(valid_payload), format="multipart")
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert "id" in body and body["status"] == "NEW"
    assert body["compensation_error"] is None
    assert body["compensation_amount_eur"] in {250, 400, 600}
    assert body["distance_km"] is not None

    case = Case.objects.get(id=body["id"])
    assert case.segments.count() == 1
    assert case.documents.count() == 2
    assert case.compensation_amount_eur == body["compensation_amount_eur"]
    assert case.compensation_calculated_at is not None
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


@pytest.mark.django_db
def test_case_created_even_when_compensation_fails(
    two_airports, valid_payload, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()
    with patch(
        "cases.views.compute_for_case",
        side_effect=DistanceUnavailable("simulated failure"),
    ):
        resp = client.post(
            "/api/cases/", _make_multipart(valid_payload), format="multipart",
        )
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["compensation_amount_eur"] is None
    assert body["distance_km"] is None
    assert body["compensation_error"] == (
        "Distance could not be calculated; you can review this case later."
    )

    case = Case.objects.get(id=body["id"])
    assert case.distance_km is None
    assert case.compensation_amount_eur is None
    assert case.compensation_calculated_at is None
    assert case.documents.count() == 2


@pytest.mark.django_db
def test_case_response_carries_compensation_on_success(
    two_airports, valid_payload, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()

    def _fake(case):
        case.distance_km = Decimal("1874.00")
        case.compensation_amount_eur = 400
        case.compensation_calculated_at = timezone.now()

    with patch("cases.views.compute_for_case", side_effect=_fake):
        resp = client.post(
            "/api/cases/", _make_multipart(valid_payload), format="multipart",
        )
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["compensation_amount_eur"] == 400
    assert body["distance_km"] == "1874.00"
    assert body["compensation_error"] is None
