"""Shared PDF-page-to-image rendering used by Pipeline A's OCR backends."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf


@contextmanager
def rendered_pdf_pages(
    pdf_path: str | Path,
    *,
    page_numbers: set[int] | None = None,
    zoom: float = 2.0,
) -> Iterator[list[tuple[int, Path]]]:
    """Render selected PDF pages to temporary PNG files for OCR.

    Yields a list of (1-indexed page number, image path) pairs. The backing
    temporary directory is removed when the context manager exits, so the
    rendered image paths must only be read inside the `with` block.
    """

    with TemporaryDirectory(prefix="w2_pipeline_ocr_") as temp_dir:
        rendered: list[tuple[int, Path]] = []
        with pymupdf.open(Path(pdf_path)) as document:
            for page_index, page in enumerate(document, start=1):
                if page_numbers is not None and page_index not in page_numbers:
                    continue
                image_path = Path(temp_dir) / f"page_{page_index}.png"
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
                pixmap.save(image_path)
                rendered.append((page_index, image_path))
        yield rendered
