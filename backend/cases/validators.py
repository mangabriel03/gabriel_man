from __future__ import annotations

from django.core.exceptions import ValidationError

try:
    import magic  # python-magic or python-magic-bin
except ImportError:  # pragma: no cover
    magic = None


MAX_FILE_BYTES = 5 * 1024 * 1024

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}


def _detect_mime_from_magic(chunk: bytes) -> str | None:
    if magic is None:
        return None
    try:
        return magic.from_buffer(chunk, mime=True)
    except Exception:  # pragma: no cover
        return None


def validate_upload(file_obj) -> str:
    """Validate an in-memory or streamed upload; return the detected MIME type.

    Raises DRF-compatible ValidationError on failure.
    """
    if file_obj is None:
        raise ValidationError("File is required.")

    size = getattr(file_obj, "size", None)
    if size is None:
        # Fall back to seek/tell for streams
        pos = file_obj.tell()
        file_obj.seek(0, 2)
        size = file_obj.tell()
        file_obj.seek(pos)

    if size > MAX_FILE_BYTES:
        raise ValidationError("File exceeds 5 MB.")

    name = getattr(file_obj, "name", "") or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError("Unsupported file type; allowed: PDF, JPG, PNG.")

    file_obj.seek(0)
    head = file_obj.read(4096)
    file_obj.seek(0)

    declared = (getattr(file_obj, "content_type", "") or "").lower()
    detected = _detect_mime_from_magic(head)

    # Normalise jpg -> jpeg
    if ext == "jpg":
        ext_mime = "image/jpeg"
    elif ext == "jpeg":
        ext_mime = "image/jpeg"
    elif ext == "png":
        ext_mime = "image/png"
    else:
        ext_mime = "application/pdf"

    if detected and detected not in ALLOWED_MIME_TYPES:
        raise ValidationError("Unsupported file type; allowed: PDF, JPG, PNG.")
    if detected and detected != ext_mime:
        raise ValidationError("File contents do not match its extension.")

    if declared and declared not in ALLOWED_MIME_TYPES:
        raise ValidationError("Unsupported file type; allowed: PDF, JPG, PNG.")

    return detected or ext_mime
