"""Common OCR backend contract consumed by Pipeline A's observation acquirer."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from w2_pipeline.extraction.models import TextObservation


@runtime_checkable
class OcrAdapter(Protocol):
    """Structural contract every Pipeline A OCR backend must satisfy.

    The deterministic parser only ever consumes the common `TextObservation`
    representation, never a backend-specific object, so any adapter
    implementing this contract is interchangeable behind
    `ObservationAcquirer`.
    """

    def extract_image(
        self, image_path: str | Path, *, page_number: int = 1
    ) -> list[TextObservation]:
        """OCR one image file into text observations."""

    def extract_pdf_pages(
        self,
        pdf_path: str | Path,
        *,
        page_numbers: set[int] | None = None,
    ) -> list[TextObservation]:
        """Render and OCR selected PDF pages into text observations."""
