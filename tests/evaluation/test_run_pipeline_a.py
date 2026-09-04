import pytest

from w2_pipeline.evaluation.run_pipeline_a import (
    _build_parser,
    _pipeline_a_extractor,
    _pipeline_a_metadata,
)
from w2_pipeline.extraction.ocr_paddle import PaddleOcrAdapter


def test_run_pipeline_a_cli_defaults_to_tesseract_psm_3() -> None:
    args = _build_parser().parse_args(["manifest.jsonl"])

    assert args.tesseract_psm == 3
    assert args.ocr_backend == "tesseract"


@pytest.mark.parametrize("psm", [11, 12])
def test_run_pipeline_a_cli_accepts_psm_experiment_modes(psm: int) -> None:
    args = _build_parser().parse_args(
        [
            "manifest.jsonl",
            "--variant-id",
            "external_clean_render",
            "--tesseract-psm",
            str(psm),
        ]
    )

    assert args.variant_id == "external_clean_render"
    assert args.tesseract_psm == psm


def test_run_pipeline_a_cli_rejects_standalone_psm_6_experiment() -> None:
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["manifest.jsonl", "--tesseract-psm", "6"])


def test_pipeline_a_extractor_uses_selected_tesseract_psm_and_supplemental_psm_6() -> None:
    extractor = _pipeline_a_extractor(tesseract_psm=12)
    ocr_adapter = extractor.observation_acquirer.ocr_adapter

    assert ocr_adapter.page_segmentation_mode == 12
    assert ocr_adapter.supplemental_page_segmentation_modes == (6,)


def test_pipeline_a_metadata_records_selected_tesseract_psm() -> None:
    extractor = _pipeline_a_extractor(tesseract_psm=11)

    metadata = _pipeline_a_metadata(extractor, variant_id="external_clean_render")

    assert metadata["ocr_backend"] == "tesseract"
    assert metadata["ocr_configuration"]["main_page_segmentation_mode"] == 11
    assert metadata["ocr_configuration"]["page_segmentation_mode"] == 11
    assert metadata["ocr_configuration"]["supplemental_page_segmentation_modes"] == [6]
    assert metadata["variant_filter"] == "external_clean_render"


def test_run_pipeline_a_cli_accepts_paddleocr_backend() -> None:
    args = _build_parser().parse_args(["manifest.jsonl", "--ocr-backend", "paddleocr"])

    assert args.ocr_backend == "paddleocr"


def test_run_pipeline_a_cli_rejects_unsupported_backend() -> None:
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["manifest.jsonl", "--ocr-backend", "not-a-backend"])


def test_pipeline_a_extractor_selects_paddleocr_backend() -> None:
    extractor = _pipeline_a_extractor(ocr_backend="paddleocr", tesseract_psm=3)

    assert isinstance(extractor.observation_acquirer.ocr_adapter, PaddleOcrAdapter)


def test_pipeline_a_metadata_records_paddleocr_backend() -> None:
    extractor = _pipeline_a_extractor(ocr_backend="paddleocr")

    metadata = _pipeline_a_metadata(extractor, variant_id="external_clean_render")

    assert metadata["ocr_backend"] == "paddleocr"
    assert metadata["ocr_configuration"]["lang"] == "en"
    assert metadata["ocr_configuration"]["device"] == "cpu"
    assert metadata["variant_filter"] == "external_clean_render"
