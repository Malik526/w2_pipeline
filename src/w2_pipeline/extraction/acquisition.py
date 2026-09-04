"""Route ingested documents into native text or OCR acquisition."""

from __future__ import annotations

from pathlib import Path

from w2_pipeline.extraction.checkbox_vision import detect_box_13_retirement_plan_mark
from w2_pipeline.extraction.models import AcquisitionRoute, ObservationSet
from w2_pipeline.extraction.native_pdf import extract_native_pdf_observations
from w2_pipeline.extraction.ocr import TesseractOcrAdapter
from w2_pipeline.extraction.ocr_backend import OcrAdapter
from w2_pipeline.extraction.pdf_rendering import rendered_pdf_pages
from w2_pipeline.ingestion.models import IngestedDocument, PdfTextMode, SourceDocumentType
from w2_pipeline.ingestion.pdf_inspector import inspect_pdf


class ObservationAcquirer:
    """Build common observations from an already-ingested source document.

    `ocr_adapter` accepts any backend implementing the `OcrAdapter` contract
    (Tesseract by default, or PaddleOCR); the routing and parsing logic below
    is backend-agnostic. OCR-routed acquisition also runs a backend-neutral
    pixel-based Box 13 checkbox detector (`checkbox_vision`) directly on the
    page image, independent of whichever OCR backend produced the text
    observations.
    """

    def __init__(self, ocr_adapter: OcrAdapter | None = None) -> None:
        self.ocr_adapter = ocr_adapter or TesseractOcrAdapter()

    def acquire(self, ingested_document: IngestedDocument) -> ObservationSet:
        """Acquire text observations using native PDF text or OCR."""

        path = Path(ingested_document.source_path)
        if ingested_document.source_type == SourceDocumentType.PDF:
            return self._acquire_pdf(path, ingested_document)

        observations = self.ocr_adapter.extract_image(path, page_number=1)
        box_13_visual_marks, warnings = self._detect_box_13_visual_marks(image_paths=[path])
        return ObservationSet(
            observations=observations,
            route=AcquisitionRoute.OCR,
            box_13_visual_marks=box_13_visual_marks,
            warnings=warnings,
        )

    def _acquire_pdf(self, path: Path, ingested_document: IngestedDocument) -> ObservationSet:
        if ingested_document.pdf_text_mode == PdfTextMode.EMBEDDED_TEXT:
            observations = extract_native_pdf_observations(path)
            return ObservationSet(observations=observations, route=AcquisitionRoute.NATIVE_PDF)

        if ingested_document.pdf_text_mode == PdfTextMode.IMAGE_ONLY:
            observations = self.ocr_adapter.extract_pdf_pages(path)
            box_13_visual_marks, warnings = self._detect_box_13_visual_marks(pdf_path=path)
            return ObservationSet(
                observations=observations,
                route=AcquisitionRoute.OCR,
                box_13_visual_marks=box_13_visual_marks,
                warnings=warnings,
            )

        if ingested_document.pdf_text_mode == PdfTextMode.MIXED:
            inspection = inspect_pdf(path)
            native_pages = {
                page.page_number for page in inspection.pages if page.has_usable_embedded_text
            }
            ocr_pages = {
                page.page_number for page in inspection.pages if not page.has_usable_embedded_text
            }
            observations = [
                *extract_native_pdf_observations(path, page_numbers=native_pages),
                *self.ocr_adapter.extract_pdf_pages(path, page_numbers=ocr_pages),
            ]
            box_13_visual_marks, warnings = self._detect_box_13_visual_marks(
                pdf_path=path, pdf_page_numbers=ocr_pages
            )
            return ObservationSet(
                observations=sorted(
                    observations,
                    key=lambda observation: (
                        observation.page,
                        observation.bbox.y0,
                        observation.bbox.x0,
                    ),
                ),
                route=AcquisitionRoute.MIXED,
                box_13_visual_marks=box_13_visual_marks,
                warnings=warnings,
            )

        observations = self.ocr_adapter.extract_pdf_pages(path)
        box_13_visual_marks, warnings = self._detect_box_13_visual_marks(pdf_path=path)
        return ObservationSet(
            observations=observations,
            route=AcquisitionRoute.OCR,
            box_13_visual_marks=box_13_visual_marks,
            warnings=warnings,
        )

    def _detect_box_13_visual_marks(
        self,
        *,
        image_paths: list[Path] | None = None,
        pdf_path: Path | None = None,
        pdf_page_numbers: set[int] | None = None,
    ) -> tuple[dict[str, bool], list[str]]:
        """Run the visual checkbox detector on every OCR-routed page image.

        Results are OR'd across pages: a single-page W-2 is the only
        supported document shape, so this is a defensive merge rather than a
        meaningful multi-page aggregation. Detector failures degrade to "no
        mark detected" rather than failing extraction, since this signal is
        always an additive OR alongside the existing OCR-text-based fallback.
        """

        if pdf_path is not None:
            with rendered_pdf_pages(pdf_path, page_numbers=pdf_page_numbers) as pages:
                candidate_paths = [image_path for _, image_path in pages]
                return self._scan_pages_for_box_13_marks(candidate_paths)
        return self._scan_pages_for_box_13_marks(image_paths or [])

    def _scan_pages_for_box_13_marks(
        self, image_paths: list[Path]
    ) -> tuple[dict[str, bool], list[str]]:
        retirement_plan_detected = False
        warnings: list[str] = []
        for image_path in image_paths:
            try:
                if detect_box_13_retirement_plan_mark(image_path):
                    retirement_plan_detected = True
            except Exception as exc:  # noqa: BLE001 - optional signal, never fatal
                warnings.append(f"Box 13 visual checkbox detection failed: {exc}")
        if not image_paths:
            return {}, warnings
        return {"retirement_plan": retirement_plan_detected}, warnings
