"""Shared Pipeline A extractor/OCR-adapter construction (Phase 8D.4).

Centralizes OCR-backend selection so the single-document production
runner (`w2_pipeline.application.run_document`) and the batch evaluation
CLI (`w2_pipeline.evaluation.run_pipeline_a`) build a `PipelineAExtractor`
the exact same way, rather than each keeping its own private copy of
this branch.
"""

from __future__ import annotations

from w2_pipeline.extraction.acquisition import ObservationAcquirer
from w2_pipeline.extraction.ocr import TesseractOcrAdapter, TesseractOcrConfig
from w2_pipeline.extraction.ocr_backend import OcrAdapter
from w2_pipeline.extraction.ocr_paddle import PaddleOcrAdapter, PaddleOcrConfig
from w2_pipeline.extraction.pipeline_a import PipelineAExtractor

SUPPORTED_OCR_BACKENDS = ("tesseract", "paddleocr")


def build_ocr_adapter(
    ocr_backend: str,
    *,
    tesseract_psm: int = 3,
    tesseract_supplemental_psm: tuple[int, ...] = (6,),
    paddle_device: str = "cpu",
) -> OcrAdapter:
    """Construct the OCR adapter behind Pipeline A's observation boundary."""

    if ocr_backend == "paddleocr":
        return PaddleOcrAdapter(config=PaddleOcrConfig(device=paddle_device))
    if ocr_backend == "tesseract":
        return TesseractOcrAdapter(
            config=TesseractOcrConfig(
                page_segmentation_mode=tesseract_psm,
                supplemental_page_segmentation_modes=tesseract_supplemental_psm,
            )
        )
    raise ValueError(f"Unsupported OCR backend {ocr_backend!r}; expected one of: {SUPPORTED_OCR_BACKENDS}.")


def build_pipeline_a_extractor(
    *,
    ocr_backend: str = "tesseract",
    tesseract_psm: int = 3,
    tesseract_supplemental_psm: tuple[int, ...] = (6,),
    paddle_device: str = "cpu",
) -> PipelineAExtractor:
    """Construct a default-wired `PipelineAExtractor` for the given OCR backend."""

    return PipelineAExtractor(
        observation_acquirer=ObservationAcquirer(
            ocr_adapter=build_ocr_adapter(
                ocr_backend,
                tesseract_psm=tesseract_psm,
                tesseract_supplemental_psm=tesseract_supplemental_psm,
                paddle_device=paddle_device,
            )
        )
    )
