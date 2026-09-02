"""Lightweight PDF inspection with PyMuPDF.

The embedded-text heuristic is intentionally simple: a page has usable embedded
text when PyMuPDF extracts at least 40 alphanumeric characters from that page.
This avoids treating stray punctuation, tiny labels, or metadata-like fragments
as a native-text-capable document. It is a routing heuristic, not a guarantee
of OCR quality or W-2 field extractability.
"""

from __future__ import annotations

from pathlib import Path

import pymupdf

from w2_pipeline.ingestion.errors import CorruptPdfError
from w2_pipeline.ingestion.models import (
    PdfInspectionResult,
    PdfPageInspection,
    PdfTextMode,
)

USABLE_TEXT_CHARACTER_THRESHOLD = 40


def count_meaningful_text_characters(text: str) -> int:
    """Count alphanumeric characters for the usable embedded-text heuristic."""

    return sum(1 for character in text if character.isalnum())


def classify_pdf_text_mode(pages: list[PdfPageInspection]) -> PdfTextMode:
    """Classify aggregate PDF text mode from page-level inspection."""

    if not pages:
        return PdfTextMode.UNKNOWN

    usable_page_count = sum(page.has_usable_embedded_text for page in pages)
    if usable_page_count == len(pages):
        return PdfTextMode.EMBEDDED_TEXT
    if usable_page_count == 0:
        return PdfTextMode.IMAGE_ONLY
    return PdfTextMode.MIXED


def inspect_pdf(path: str | Path) -> PdfInspectionResult:
    """Open a PDF and return page count plus embedded-text routing metadata."""

    pdf_path = Path(path)

    try:
        with pymupdf.open(pdf_path) as document:
            pages: list[PdfPageInspection] = []
            for page_index, page in enumerate(document, start=1):
                text = page.get_text("text")
                character_count = count_meaningful_text_characters(text)
                pages.append(
                    PdfPageInspection(
                        page_number=page_index,
                        meaningful_text_character_count=character_count,
                        has_usable_embedded_text=(
                            character_count >= USABLE_TEXT_CHARACTER_THRESHOLD
                        ),
                    )
                )
    except Exception as exc:
        raise CorruptPdfError(f"Could not open or inspect PDF: {pdf_path.name}") from exc

    pdf_text_mode = classify_pdf_text_mode(pages)
    return PdfInspectionResult(
        page_count=len(pages),
        pdf_text_mode=pdf_text_mode,
        has_usable_embedded_text=any(page.has_usable_embedded_text for page in pages),
        pages=pages,
    )
