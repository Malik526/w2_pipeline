from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from w2_pipeline.extraction.acquisition import ObservationAcquirer
from w2_pipeline.extraction.checkbox_vision import RETIREMENT_PLAN_ZONE
from w2_pipeline.extraction.models import TextObservation
from w2_pipeline.ingestion import ingest_document


class StubOcrAdapter:
    """Minimal OcrAdapter stub returning no observations, for wiring tests."""

    def extract_image(self, image_path, *, page_number: int = 1) -> list[TextObservation]:
        return []

    def extract_pdf_pages(self, pdf_path, *, page_numbers=None) -> list[TextObservation]:
        return []


def _zone_box(size: tuple[int, int], zone: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    width, height = size
    x0_ratio, x1_ratio, y0_ratio, y1_ratio = zone
    return (
        round(x0_ratio * width),
        round(y0_ratio * height),
        round(x1_ratio * width),
        round(y1_ratio * height),
    )


def _page_image(path: Path, *, marked: bool) -> None:
    image = Image.new("L", (2550, 3300), color=255)
    box = _zone_box(image.size, RETIREMENT_PLAN_ZONE)
    ImageDraw.Draw(image).rectangle(box, outline=0, width=2)
    if marked:
        ImageDraw.Draw(image).rectangle(box, fill=0)
    image.save(path)


def test_acquire_reports_visual_retirement_plan_mark_for_marked_image(tmp_path: Path) -> None:
    image_path = tmp_path / "marked.png"
    _page_image(image_path, marked=True)
    ingested = ingest_document(image_path, document_id="doc")

    observation_set = ObservationAcquirer(ocr_adapter=StubOcrAdapter()).acquire(ingested)

    assert observation_set.box_13_visual_marks == {"retirement_plan": True}


def test_acquire_reports_no_visual_mark_for_unmarked_image(tmp_path: Path) -> None:
    image_path = tmp_path / "unmarked.png"
    _page_image(image_path, marked=False)
    ingested = ingest_document(image_path, document_id="doc")

    observation_set = ObservationAcquirer(ocr_adapter=StubOcrAdapter()).acquire(ingested)

    assert observation_set.box_13_visual_marks == {"retirement_plan": False}


def test_acquire_degrades_gracefully_when_visual_detection_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_path = tmp_path / "unmarked.png"
    _page_image(image_path, marked=False)
    ingested = ingest_document(image_path, document_id="doc")

    def failing_detector(image_path):
        raise OSError("simulated decode failure")

    monkeypatch.setattr(
        "w2_pipeline.extraction.acquisition.detect_box_13_retirement_plan_mark", failing_detector
    )

    observation_set = ObservationAcquirer(ocr_adapter=StubOcrAdapter()).acquire(ingested)

    assert observation_set.box_13_visual_marks == {"retirement_plan": False}
    assert observation_set.warnings
    assert "Box 13 visual checkbox detection failed" in observation_set.warnings[0]
