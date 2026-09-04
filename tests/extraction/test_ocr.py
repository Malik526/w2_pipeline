from pathlib import Path

import pytest
from PIL import Image

from w2_pipeline.extraction.errors import MissingOcrDependencyError
from w2_pipeline.extraction.models import ObservationSource
from w2_pipeline.extraction.ocr import (
    TesseractOcrAdapter,
    TesseractOcrConfig,
    parse_tesseract_tsv,
)


def _tsv_header() -> str:
    return "\t".join(
        [
            "level",
            "page_num",
            "block_num",
            "par_num",
            "line_num",
            "word_num",
            "left",
            "top",
            "width",
            "height",
            "conf",
            "text",
        ]
    )


def test_tesseract_tsv_output_converts_to_observations() -> None:
    tsv = _tsv_header()
    tsv += "\n" + "\t".join(["5", "1", "1", "1", "1", "1", "10", "20", "30", "12", "96", "SSN"])

    observations = parse_tesseract_tsv(tsv, page_number=2)

    assert len(observations) == 1
    assert observations[0].text == "SSN"
    assert observations[0].page == 2
    assert observations[0].bbox.x1 == 40
    assert observations[0].source == ObservationSource.OCR


def test_missing_tesseract_runtime_fails_clearly(tmp_path: Path) -> None:
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (20, 10), color="white").save(image_path)
    adapter = TesseractOcrAdapter(executable="definitely-missing-tesseract")

    with pytest.raises(MissingOcrDependencyError, match="Tesseract OCR runtime"):
        adapter.extract_image(image_path)


def test_tesseract_adapter_defaults_to_full_page_segmentation() -> None:
    adapter = TesseractOcrAdapter()

    assert adapter.config == TesseractOcrConfig()
    assert adapter.page_segmentation_mode == 3
    assert adapter.supplemental_page_segmentation_modes == (6,)


@pytest.mark.parametrize("main_psm", [3, 11, 12])
def test_tesseract_config_supports_controlled_main_psm_modes(main_psm: int) -> None:
    config = TesseractOcrConfig(page_segmentation_mode=main_psm)
    adapter = TesseractOcrAdapter(config=config)

    assert adapter.page_segmentation_mode == main_psm
    assert adapter.supplemental_page_segmentation_modes == (6,)


def test_tesseract_config_rejects_unsupported_main_psm() -> None:
    with pytest.raises(ValueError, match="Unsupported main Tesseract"):
        TesseractOcrConfig(page_segmentation_mode=6)


def test_tesseract_adapter_preserves_supplemental_psm_6_for_psm_11(tmp_path: Path) -> None:
    image_path = tmp_path / "sample.png"

    class RecordingAdapter(TesseractOcrAdapter):
        def __init__(self) -> None:
            super().__init__(config=TesseractOcrConfig(page_segmentation_mode=11))
            self.calls: list[int] = []

        def ensure_available(self) -> None:
            return None

        def _run_tesseract(self, image_path: Path, *, page_segmentation_mode: int) -> str:
            self.calls.append(page_segmentation_mode)
            return _tsv_header()

    adapter = RecordingAdapter()
    observations = adapter.extract_image(image_path)

    assert observations == []
    assert adapter.calls == [11, 6]
