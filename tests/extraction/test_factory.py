"""Phase 8D.4: shared Pipeline A extractor/OCR-adapter factory tests.

`w2_pipeline.evaluation.run_pipeline_a` and
`w2_pipeline.application.run_document` both build extractors through
this module now instead of each keeping a private copy; these tests pin
the factory's own backend-selection behavior directly.
"""

from __future__ import annotations

import pytest

from w2_pipeline.extraction.factory import build_ocr_adapter, build_pipeline_a_extractor
from w2_pipeline.extraction.ocr import TesseractOcrAdapter
from w2_pipeline.extraction.ocr_paddle import PaddleOcrAdapter
from w2_pipeline.extraction.pipeline_a import PipelineAExtractor


def test_build_ocr_adapter_tesseract_default() -> None:
    adapter = build_ocr_adapter("tesseract")

    assert isinstance(adapter, TesseractOcrAdapter)
    assert adapter.page_segmentation_mode == 3


def test_build_ocr_adapter_paddleocr_uses_requested_device() -> None:
    adapter = build_ocr_adapter("paddleocr", paddle_device="gpu")

    assert isinstance(adapter, PaddleOcrAdapter)
    assert adapter.config.device == "gpu"


def test_build_ocr_adapter_rejects_unsupported_backend() -> None:
    with pytest.raises(ValueError):
        build_ocr_adapter("not_a_real_backend")


def test_build_pipeline_a_extractor_wires_requested_backend() -> None:
    extractor = build_pipeline_a_extractor(ocr_backend="paddleocr", paddle_device="cpu")

    assert isinstance(extractor, PipelineAExtractor)
    assert isinstance(extractor.observation_acquirer.ocr_adapter, PaddleOcrAdapter)
    assert extractor.observation_acquirer.ocr_adapter.config.device == "cpu"
