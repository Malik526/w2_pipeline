from pathlib import Path

import pymupdf

from w2_pipeline.extraction.pdf_rendering import rendered_pdf_pages


def _sample_pdf(path: Path, *, page_count: int) -> None:
    with pymupdf.open() as document:
        for _ in range(page_count):
            document.new_page()
        document.save(path)


def test_rendered_pdf_pages_renders_every_page_by_default(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    _sample_pdf(pdf_path, page_count=3)

    with rendered_pdf_pages(pdf_path) as pages:
        page_numbers = [page_number for page_number, _ in pages]
        assert page_numbers == [1, 2, 3]
        assert all(image_path.exists() for _, image_path in pages)

    assert not pages[0][1].exists()


def test_rendered_pdf_pages_filters_to_requested_page_numbers(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    _sample_pdf(pdf_path, page_count=3)

    with rendered_pdf_pages(pdf_path, page_numbers={2}) as pages:
        assert [page_number for page_number, _ in pages] == [2]
