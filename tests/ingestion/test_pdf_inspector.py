from pathlib import Path

import pymupdf
from PIL import Image

from w2_pipeline.ingestion.pdf_inspector import inspect_pdf
from w2_pipeline.ingestion.models import PdfTextMode


def write_fixture_image(path: Path) -> None:
    Image.new("RGB", (16, 16), color=(240, 240, 240)).save(path, format="PNG")


def write_digital_text_pdf(path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "This synthetic PDF contains enough embedded text for routing. " * 2,
        fontsize=12,
    )
    document.save(path)
    document.close()


def write_image_only_pdf(path: Path, image_path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page(width=100, height=100)
    page.insert_image(page.rect, filename=str(image_path))
    document.save(path)
    document.close()


def write_mixed_pdf(path: Path, image_path: Path) -> None:
    document = pymupdf.open()
    text_page = document.new_page()
    text_page.insert_text(
        (36, 36),
        "This first page has meaningful embedded text for inspection. " * 2,
        fontsize=12,
    )
    image_page = document.new_page(width=100, height=100)
    image_page.insert_image(image_page.rect, filename=str(image_path))
    document.save(path)
    document.close()


def test_digital_pdf_with_usable_text_is_classified_as_embedded_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "digital.pdf"
    write_digital_text_pdf(pdf_path)

    result = inspect_pdf(pdf_path)

    assert result.page_count == 1
    assert result.pdf_text_mode == PdfTextMode.EMBEDDED_TEXT
    assert result.has_usable_embedded_text is True
    assert result.pages[0].meaningful_text_character_count >= 40


def test_image_only_pdf_is_classified_as_image_only(tmp_path: Path) -> None:
    image_path = tmp_path / "source.png"
    pdf_path = tmp_path / "image_only.pdf"
    write_fixture_image(image_path)
    write_image_only_pdf(pdf_path, image_path)

    result = inspect_pdf(pdf_path)

    assert result.page_count == 1
    assert result.pdf_text_mode == PdfTextMode.IMAGE_ONLY
    assert result.has_usable_embedded_text is False
    assert result.pages[0].meaningful_text_character_count == 0


def test_mixed_pdf_is_classified_as_mixed(tmp_path: Path) -> None:
    image_path = tmp_path / "source.png"
    pdf_path = tmp_path / "mixed.pdf"
    write_fixture_image(image_path)
    write_mixed_pdf(pdf_path, image_path)

    result = inspect_pdf(pdf_path)

    assert result.page_count == 2
    assert result.pdf_text_mode == PdfTextMode.MIXED
    assert result.has_usable_embedded_text is True
    assert [page.has_usable_embedded_text for page in result.pages] == [True, False]
