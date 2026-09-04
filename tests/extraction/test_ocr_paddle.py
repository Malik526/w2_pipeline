from pathlib import Path

import pytest

from w2_pipeline.extraction.errors import MissingOcrDependencyError, OcrExecutionError
from w2_pipeline.extraction.models import ObservationSource
from w2_pipeline.extraction.ocr_paddle import PaddleOcrAdapter, PaddleOcrConfig


class RecordingAdapter(PaddleOcrAdapter):
    """Adapter stub that returns canned predict payloads without PaddleOCR installed."""

    def __init__(self, payloads: list[list[dict]]) -> None:
        super().__init__()
        self._payloads = iter(payloads)
        self.calls: list[Path] = []

    def ensure_available(self) -> None:
        return None

    def _run_predict(self, image_path: Path) -> list[dict]:
        self.calls.append(image_path)
        return next(self._payloads)


def test_paddle_adapter_converts_rec_boxes_to_observations() -> None:
    adapter = RecordingAdapter(
        payloads=[
            [
                {
                    "rec_texts": ["Employee SSN: 000-00-0005", "  "],
                    "rec_scores": [0.999, 0.5],
                    "rec_boxes": [[8, 29, 143, 43], [0, 0, 1, 1]],
                }
            ]
        ]
    )

    observations = adapter.extract_image("sample.png", page_number=3)

    assert len(observations) == 1
    observation = observations[0]
    assert observation.text == "Employee SSN: 000-00-0005"
    assert observation.page == 3
    assert observation.source == ObservationSource.OCR
    assert observation.bbox.x0 == 8
    assert observation.bbox.y0 == 29
    assert observation.bbox.x1 == 143
    assert observation.bbox.y1 == 43


def test_paddle_adapter_defaults_avoid_mkldnn_and_preprocessing() -> None:
    adapter = PaddleOcrAdapter()

    assert adapter.config == PaddleOcrConfig()
    assert adapter.config.enable_mkldnn is False
    assert adapter.config.device == "cpu"
    assert adapter.config.lang == "en"


def test_missing_paddleocr_package_fails_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "paddleocr":
            raise ImportError("No module named 'paddleocr'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    adapter = PaddleOcrAdapter()

    with pytest.raises(MissingOcrDependencyError, match="PaddleOCR is not installed"):
        adapter.ensure_available()


def test_paddle_adapter_wraps_predict_failures() -> None:
    class FailingClient:
        def predict(self, image_path: str) -> list[dict]:
            raise RuntimeError("boom")

    class FailingAdapter(PaddleOcrAdapter):
        def ensure_available(self) -> None:
            return None

        def _get_client(self) -> object:
            return FailingClient()

    with pytest.raises(OcrExecutionError, match="PaddleOCR failed"):
        FailingAdapter().extract_image("sample.png")


def test_paddle_adapter_extracts_pdf_pages(tmp_path: Path) -> None:
    import pymupdf

    pdf_path = tmp_path / "sample.pdf"
    with pymupdf.open() as document:
        document.new_page()
        document.new_page()
        document.save(pdf_path)

    adapter = RecordingAdapter(
        payloads=[
            [{"rec_texts": ["Page one"], "rec_scores": [0.9], "rec_boxes": [[0, 0, 10, 10]]}],
            [{"rec_texts": ["Page two"], "rec_scores": [0.9], "rec_boxes": [[0, 0, 10, 10]]}],
        ]
    )

    observations = adapter.extract_pdf_pages(pdf_path)

    assert [observation.text for observation in observations] == ["Page one", "Page two"]
    assert [observation.page for observation in observations] == [1, 2]
    assert len(adapter.calls) == 2
