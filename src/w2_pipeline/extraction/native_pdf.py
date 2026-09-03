"""PyMuPDF native text acquisition for Pipeline A."""

from __future__ import annotations

from pathlib import Path

import pymupdf

from w2_pipeline.extraction.models import BoundingBox, ObservationSource, TextObservation


def extract_native_pdf_observations(
    pdf_path: str | Path,
    *,
    page_numbers: set[int] | None = None,
) -> list[TextObservation]:
    """Extract line-level native PDF text observations with coordinates."""

    observations: list[TextObservation] = []
    with pymupdf.open(Path(pdf_path)) as document:
        for page_index, page in enumerate(document, start=1):
            if page_numbers is not None and page_index not in page_numbers:
                continue
            page_dict = page.get_text("dict")
            for block in page_dict.get("blocks", []):
                for line in block.get("lines", []):
                    text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
                    if not text:
                        continue
                    x0, y0, x1, y1 = line["bbox"]
                    observations.append(
                        TextObservation(
                            text=text,
                            page=page_index,
                            bbox=BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1),
                            source=ObservationSource.NATIVE_PDF,
                        )
                    )
    return sorted(observations, key=lambda observation: (observation.page, observation.bbox.y0, observation.bbox.x0))
