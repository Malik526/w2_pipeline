import pytest

from w2_pipeline.evaluation.run_pipeline_a import (
    _build_parser,
    _parse_supplemental_psm,
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


def test_run_pipeline_a_cli_defaults_supplemental_psm_to_6() -> None:
    args = _build_parser().parse_args(["manifest.jsonl"])

    assert args.tesseract_supplemental_psm == "6"


def test_run_pipeline_a_cli_accepts_targeted_psm_11_supplementation() -> None:
    args = _build_parser().parse_args(
        ["manifest.jsonl", "--tesseract-supplemental-psm", "6,11"]
    )

    assert _parse_supplemental_psm(args.tesseract_supplemental_psm) == (6, 11)


def test_pipeline_a_extractor_threads_targeted_psm_11_supplementation() -> None:
    extractor = _pipeline_a_extractor(tesseract_psm=3, tesseract_supplemental_psm=(6, 11))
    ocr_adapter = extractor.observation_acquirer.ocr_adapter

    assert ocr_adapter.page_segmentation_mode == 3
    assert ocr_adapter.supplemental_page_segmentation_modes == (6, 11)


def test_pipeline_a_metadata_records_targeted_psm_11_supplementation() -> None:
    extractor = _pipeline_a_extractor(tesseract_psm=3, tesseract_supplemental_psm=(6, 11))

    metadata = _pipeline_a_metadata(extractor, variant_id="external_clean_render")

    assert metadata["ocr_configuration"]["supplemental_page_segmentation_modes"] == [6, 11]


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


def test_run_pipeline_a_cli_defaults_paddle_device_to_cpu() -> None:
    args = _build_parser().parse_args(["manifest.jsonl"])

    assert args.paddle_device == "cpu"


def test_run_pipeline_a_cli_accepts_explicit_paddle_device() -> None:
    args = _build_parser().parse_args(
        ["manifest.jsonl", "--ocr-backend", "paddleocr", "--paddle-device", "gpu:0"]
    )

    assert args.paddle_device == "gpu:0"


def test_pipeline_a_extractor_threads_paddle_device_into_config() -> None:
    extractor = _pipeline_a_extractor(ocr_backend="paddleocr", paddle_device="gpu:0")
    ocr_adapter = extractor.observation_acquirer.ocr_adapter

    assert isinstance(ocr_adapter, PaddleOcrAdapter)
    assert ocr_adapter.config.device == "gpu:0"


def test_pipeline_a_metadata_records_selected_paddle_device() -> None:
    extractor = _pipeline_a_extractor(ocr_backend="paddleocr", paddle_device="gpu:0")

    metadata = _pipeline_a_metadata(extractor, variant_id="external_clean_render")

    assert metadata["ocr_configuration"]["device"] == "gpu:0"
