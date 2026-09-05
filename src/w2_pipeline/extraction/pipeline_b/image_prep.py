"""Prepare one rendered page image for Pipeline B's vision-language inference.

Reuses the same low-level page rasterization
(`w2_pipeline.extraction.pdf_rendering`) Pipeline A's OCR backends already
use to turn a PDF page into a PNG for image-based processing -- plain
PyMuPDF rasterization, not text extraction, OCR, or parsing -- so both
pipelines see the identical input image for a given source document. For
JPEG/PNG sources, the already-ingested file is used directly. Pipeline B
does not implement its own document-rendering path.

Single-page W-2 is the only supported document shape (matching the
assumption already encoded in `checkbox_vision.py`), so only page 1 is ever
rendered.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from w2_pipeline.extraction.pdf_rendering import rendered_pdf_pages
from w2_pipeline.extraction.pipeline_b.errors import ImagePreparationError
from w2_pipeline.ingestion.models import IngestedDocument, SourceDocumentType


@contextmanager
def prepare_page_image(ingested_document: IngestedDocument) -> Iterator[Path]:
    """Yield a page-1 image path suitable for vision-language inference.

    For PDFs, the yielded path lives in a temporary directory that is
    removed when the context manager exits, so it must only be read inside
    the `with` block (same contract as `rendered_pdf_pages`).
    """

    path = Path(ingested_document.source_path)
    if ingested_document.source_type != SourceDocumentType.PDF:
        if not path.exists():
            raise ImagePreparationError(f"Source image not found: {path}")
        yield path
        return

    try:
        with rendered_pdf_pages(path, page_numbers={1}) as pages:
            if not pages:
                raise ImagePreparationError(f"PDF has no page 1 to render: {path}")
            _, image_path = pages[0]
            yield image_path
    except ImagePreparationError:
        raise
    except Exception as exc:
        raise ImagePreparationError(f"Failed to render PDF page for inference: {exc}") from exc
