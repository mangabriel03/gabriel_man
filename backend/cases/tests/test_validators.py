from __future__ import annotations

import base64
from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from cases.validators import MAX_FILE_BYTES, validate_upload


# Minimal valid 1x1 PNG (with IHDR + IDAT + IEND chunks) — libmagic requires
# more than the 8-byte signature to reliably detect image/png.
PNG_MAGIC = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)
JPEG_MAGIC = b"\xff\xd8\xff\xe0" + b"\x00" * 32
PDF_MAGIC = b"%PDF-1.4\n" + b"\x00" * 32


def _uploaded(name: str, content: bytes, content_type: str) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type=content_type)


def test_accepts_valid_pdf():
    validate_upload(_uploaded("id.pdf", PDF_MAGIC, "application/pdf"))


def test_accepts_valid_png():
    validate_upload(_uploaded("bp.png", PNG_MAGIC, "image/png"))


def test_accepts_valid_jpeg():
    validate_upload(_uploaded("bp.jpg", JPEG_MAGIC, "image/jpeg"))


def test_rejects_oversized_file():
    big = b"\x00" * (MAX_FILE_BYTES + 1)
    with pytest.raises(ValidationError):
        validate_upload(_uploaded("id.pdf", big, "application/pdf"))


def test_rejects_bad_extension():
    with pytest.raises(ValidationError):
        validate_upload(_uploaded("id.exe", PDF_MAGIC, "application/pdf"))


def test_rejects_extension_content_mismatch():
    # Extension says PNG but magic bytes are PDF
    with pytest.raises(ValidationError):
        validate_upload(_uploaded("id.png", PDF_MAGIC, "image/png"))
