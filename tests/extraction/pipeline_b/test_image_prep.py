from pathlib import Path

import pymupdf
import pytest
from PIL import Image

from w2_pipeline.extraction.pipeline_b.errors import ImagePreparationError
from w2_pipeline.extraction.pipeline_b.image_prep import prepare_page_image
from w2_pipeline.ingestion.models import IngestedDocument, SourceDocumentType

_FAKE_SHA256 = "0" * 64


def _ingested_pdf(path: Path) -> IngestedDocument:
    return IngestedDocument(
        document_id="doc-1",
        source_path=str(path),
        source_filename=path.name,
        source_type=SourceDocumentType.PDF,
        mime_type="application/pdf",
        file_size_bytes=path.stat().st_size,
        sha256=_FAKE_SHA256,
        page_count=1,
    )


def _ingested_image(path: Path) -> IngestedDocument:
    file_size_bytes = path.stat().st_size if path.exists() else 0
    return IngestedDocument(
        document_id="doc-2",
        source_path=str(path),
        source_filename=path.name,
        source_type=SourceDocumentType.PNG,
        mime_type="image/png",
        file_size_bytes=file_size_bytes,
        sha256=_FAKE_SHA256,
        image_width_pixels=20,
        image_height_pixels=10,
    )


def test_prepare_page_image_renders_first_pdf_page(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    with pymupdf.open() as document:
        document.new_page()
        document.new_page()
        document.save(pdf_path)

    with prepare_page_image(_ingested_pdf(pdf_path)) as image_path:
        assert image_path.exists()
        assert image_path.suffix == ".png"

    assert not image_path.exists()


def test_prepare_page_image_uses_original_file_for_png(tmp_path: Path) -> None:
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (20, 10), color="white").save(image_path)

    with prepare_page_image(_ingested_image(image_path)) as prepared_path:
        assert prepared_path == image_path


def test_prepare_page_image_raises_for_missing_image_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "gone.png"
    ingested = _ingested_image(missing_path)

    with pytest.raises(ImagePreparationError):
        with prepare_page_image(ingested):
            pass


def test_prepare_page_image_raises_for_corrupt_pdf(tmp_path: Path) -> None:
    bad_pdf = tmp_path / "bad.pdf"
    bad_pdf.write_bytes(b"not actually a pdf")

    with pytest.raises(ImagePreparationError):
        with prepare_page_image(_ingested_pdf(bad_pdf)):
            pass
