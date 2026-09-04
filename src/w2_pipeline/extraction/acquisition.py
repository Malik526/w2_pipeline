"""Route ingested documents into native text or OCR acquisition."""

from __future__ import annotations

from pathlib import Path

from w2_pipeline.extraction.models import AcquisitionRoute, ObservationSet
from w2_pipeline.extraction.native_pdf import extract_native_pdf_observations
from w2_pipeline.extraction.ocr import TesseractOcrAdapter
from w2_pipeline.extraction.ocr_backend import OcrAdapter
from w2_pipeline.ingestion.models import IngestedDocument, PdfTextMode, SourceDocumentType
from w2_pipeline.ingestion.pdf_inspector import inspect_pdf


class ObservationAcquirer:
    """Build common observations from an already-ingested source document.

    `ocr_adapter` accepts any backend implementing the `OcrAdapter` contract
    (Tesseract by default, or PaddleOCR); the routing and parsing logic below
    is backend-agnostic.
    """

    def __init__(self, ocr_adapter: OcrAdapter | None = None) -> None:
        self.ocr_adapter = ocr_adapter or TesseractOcrAdapter()

    def acquire(self, ingested_document: IngestedDocument) -> ObservationSet:
        """Acquire text observations using native PDF text or OCR."""

        path = Path(ingested_document.source_path)
        if ingested_document.source_type == SourceDocumentType.PDF:
            return self._acquire_pdf(path, ingested_document)

        observations = self.ocr_adapter.extract_image(path, page_number=1)
        return ObservationSet(observations=observations, route=AcquisitionRoute.OCR)

    def _acquire_pdf(self, path: Path, ingested_document: IngestedDocument) -> ObservationSet:
        if ingested_document.pdf_text_mode == PdfTextMode.EMBEDDED_TEXT:
            observations = extract_native_pdf_observations(path)
            return ObservationSet(observations=observations, route=AcquisitionRoute.NATIVE_PDF)

        if ingested_document.pdf_text_mode == PdfTextMode.IMAGE_ONLY:
            observations = self.ocr_adapter.extract_pdf_pages(path)
            return ObservationSet(observations=observations, route=AcquisitionRoute.OCR)

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
            )

        observations = self.ocr_adapter.extract_pdf_pages(path)
        return ObservationSet(observations=observations, route=AcquisitionRoute.OCR)
