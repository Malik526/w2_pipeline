from pathlib import Path

import pymupdf
import pytest
from PIL import Image

from w2_pipeline.ingestion import (
    CorruptImageError,
    CorruptPdfError,
    DocumentNotFoundError,
    DocumentTypeMismatchError,
    IngestionService,
    IngestionStatus,
    SourceDocumentType,
    UnsupportedDocumentTypeError,
    ingest_document,
)


def write_text_pdf(path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "Synthetic document intake text for routing. " * 3,
        fontsize=12,
    )
    document.save(path)
    document.close()


def write_image(path: Path, image_format: str) -> None:
    Image.new("RGB", (20, 10), color=(120, 40, 200)).save(path, format=image_format)


def write_image_only_pdf(path: Path, image_path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page(width=100, height=100)
    page.insert_image(page.rect, filename=str(image_path))
    document.save(path)
    document.close()


def test_valid_pdf_is_accepted_with_metadata(tmp_path: Path) -> None:
    pdf_path = tmp_path / "digital_text.pdf"
    write_text_pdf(pdf_path)

    result = ingest_document(pdf_path, document_id="doc_fixed")

    assert result.document_id == "doc_fixed"
    assert result.source_filename == "digital_text.pdf"
    assert result.source_type == SourceDocumentType.PDF
    assert result.mime_type == "application/pdf"
    assert result.file_size_bytes == pdf_path.stat().st_size
    assert len(result.sha256) == 64
    assert result.page_count == 1
    assert result.has_usable_embedded_text is True
    assert result.status == IngestionStatus.READY


def test_valid_jpeg_is_accepted_with_dimensions(tmp_path: Path) -> None:
    image_path = tmp_path / "sample.jpg"
    write_image(image_path, "JPEG")

    result = ingest_document(image_path)

    assert result.document_id
    assert result.source_type == SourceDocumentType.JPEG
    assert result.mime_type == "image/jpeg"
    assert result.image_width_pixels == 20
    assert result.image_height_pixels == 10
    assert result.page_count is None


def test_valid_png_is_accepted_with_dimensions(tmp_path: Path) -> None:
    image_path = tmp_path / "sample.png"
    write_image(image_path, "PNG")

    result = ingest_document(image_path)

    assert result.source_type == SourceDocumentType.PNG
    assert result.mime_type == "image/png"
    assert result.image_width_pixels == 20
    assert result.image_height_pixels == 10


def test_unsupported_extension_is_rejected(tmp_path: Path) -> None:
    text_path = tmp_path / "notes.txt"
    text_path.write_text("not a supported source document", encoding="utf-8")

    with pytest.raises(UnsupportedDocumentTypeError):
        ingest_document(text_path)


def test_extension_and_content_mismatch_is_rejected(tmp_path: Path) -> None:
    image_path = tmp_path / "mismatch.pdf"
    write_image(image_path, "PNG")

    with pytest.raises(DocumentTypeMismatchError):
        ingest_document(image_path)


def test_nonexistent_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(DocumentNotFoundError):
        ingest_document(tmp_path / "missing.pdf")


def test_sha256_is_deterministic_and_content_based(tmp_path: Path) -> None:
    service = IngestionService()
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    third = tmp_path / "third.png"
    first.write_bytes(b"same bytes")
    second.write_bytes(b"same bytes")
    third.write_bytes(b"different bytes")

    assert service.calculate_sha256(first) == service.calculate_sha256(second)
    assert service.calculate_sha256(first) != service.calculate_sha256(third)


def test_corrupt_pdf_fails_cleanly(tmp_path: Path) -> None:
    pdf_path = tmp_path / "corrupt.pdf"
    pdf_path.write_bytes(b"%PDF-1.7\nnot a real pdf")

    with pytest.raises(CorruptPdfError):
        ingest_document(pdf_path)


def test_corrupt_image_fails_cleanly(tmp_path: Path) -> None:
    image_path = tmp_path / "corrupt.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nnot a real png")

    with pytest.raises(CorruptImageError):
        ingest_document(image_path)


def test_ingestion_result_serializes_predictably(tmp_path: Path) -> None:
    pdf_path = tmp_path / "digital_text.pdf"
    write_text_pdf(pdf_path)

    result = ingest_document(pdf_path, document_id="doc_json")
    json_payload = result.model_dump_json()

    assert '"document_id":"doc_json"' in json_payload
    assert '"source_type":"pdf"' in json_payload
    assert '"status":"ready"' in json_payload
