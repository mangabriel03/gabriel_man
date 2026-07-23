"""Compensation-calculation exceptions."""
from __future__ import annotations


class DistanceUnavailable(Exception):
    """Raised when a leg's distance cannot be determined by any source.

    The service layer attaches a ``payload`` dict describing per-leg failures
    so the preview view can return a structured 422 body.
    """

    def __init__(self, message: str, payload: dict | None = None) -> None:
        super().__init__(message)
        self.payload = payload
