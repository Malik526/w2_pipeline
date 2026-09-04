from pathlib import Path

import pytest
from PIL import Image

from w2_pipeline.extraction.errors import MissingOcrDependencyError
from w2_pipeline.extraction.models import ObservationSource
from w2_pipeline.extraction.ocr import (
    SUPPORTED_SUPPLEMENTAL_PAGE_SEGMENTATION_MODES,
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


def test_supported_supplemental_psm_modes_are_6_and_11() -> None:
    assert SUPPORTED_SUPPLEMENTAL_PAGE_SEGMENTATION_MODES == (6, 11)


@pytest.mark.parametrize("supplemental_modes", [(6, 11), (11,), (6,)])
def test_tesseract_config_supports_targeted_psm_11_supplementation(
    supplemental_modes: tuple[int, ...],
) -> None:
    config = TesseractOcrConfig(supplemental_page_segmentation_modes=supplemental_modes)

    assert config.supplemental_page_segmentation_modes == supplemental_modes


def test_tesseract_config_rejects_unsupported_supplemental_psm() -> None:
    with pytest.raises(ValueError, match="Unsupported supplemental Tesseract"):
        TesseractOcrConfig(supplemental_page_segmentation_modes=(7,))


def _tsv_row(left: float, top: float, width: float, height: float, text: str, conf: str = "96") -> str:
    return "\t".join(
        ["5", "1", "1", "1", "1", "1", str(left), str(top), str(width), str(height), conf, text]
    )


def test_targeted_psm_11_supplemental_pass_is_scoped_to_approved_fields(tmp_path: Path) -> None:
    """PSM 11 supplemental output must land only in its approved zones,
    tagged as supplemental, and never in Box 13's checkbox zone (owned by
    checkbox_vision.py, explicitly excluded from PSM 11 targeting) or the
    employee-name zone (dropped after the 5-document smoke test found a
    disqualifying `_zone_text` duplication regression there; see
    docs/experiments/pipeline-a-extraction-history.md)."""

    image_path = tmp_path / "sample.png"

    main_pass_tsv = "\n".join(
        [
            _tsv_header(),
            # Establishes a 1000x1000 reference page extent for zone ratios.
            _tsv_row(0, 990, 1000, 10, "Copy"),
        ]
    )
    supplemental_pass_tsv = "\n".join(
        [
            _tsv_header(),
            _tsv_row(100, 520, 50, 20, "John"),  # employee name zone -> dropped (no longer targeted)
            _tsv_row(250, 180, 100, 20, "12-3456789"),  # EIN zone, EIN-shaped -> kept
            _tsv_row(250, 180, 100, 20, "Acme"),  # EIN zone, not EIN-shaped -> dropped
            _tsv_row(600, 260, 50, 20, "30000.00"),  # box 3 zone -> kept
            _tsv_row(700, 560, 30, 20, "X"),  # Box 13 checkbox zone -> dropped
            _tsv_row(950, 10, 30, 20, "Stray"),  # off-target noise -> dropped
        ]
    )

    class RecordingAdapter(TesseractOcrAdapter):
        def __init__(self) -> None:
            super().__init__(
                config=TesseractOcrConfig(
                    page_segmentation_mode=3, supplemental_page_segmentation_modes=(11,)
                )
            )

        def ensure_available(self) -> None:
            return None

        def _run_tesseract(self, image_path: Path, *, page_segmentation_mode: int) -> str:
            if page_segmentation_mode == 11:
                return supplemental_pass_tsv
            return main_pass_tsv

    observations = RecordingAdapter().extract_image(image_path)

    main_texts = {observation.text for observation in observations if not observation.is_supplemental}
    supplemental_texts = {
        observation.text for observation in observations if observation.is_supplemental
    }
    assert main_texts == {"Copy"}
    assert supplemental_texts == {"12-3456789", "30000.00"}


def test_targeted_psm_6_supplemental_pass_still_recovers_ssn_only(tmp_path: Path) -> None:
    """Generalizing the filter must not change PSM 6's existing SSN-only behavior."""

    image_path = tmp_path / "sample.png"

    main_pass_tsv = "\n".join([_tsv_header(), _tsv_row(0, 990, 1000, 10, "Copy")])
    supplemental_pass_tsv = "\n".join(
        [
            _tsv_header(),
            _tsv_row(300, 130, 150, 20, "123-45-6789"),  # top identifier zone, SSN-shaped -> kept
            _tsv_row(300, 130, 150, 20, "Not An SSN"),  # same zone, wrong shape -> dropped
            _tsv_row(600, 260, 50, 20, "999-99-9999"),  # SSN-shaped but outside PSM 6's zone -> dropped
        ]
    )

    class RecordingAdapter(TesseractOcrAdapter):
        def __init__(self) -> None:
            super().__init__(config=TesseractOcrConfig(page_segmentation_mode=3))

        def ensure_available(self) -> None:
            return None

        def _run_tesseract(self, image_path: Path, *, page_segmentation_mode: int) -> str:
            if page_segmentation_mode == 6:
                return supplemental_pass_tsv
            return main_pass_tsv

    observations = RecordingAdapter().extract_image(image_path)

    supplemental_texts = {
        observation.text for observation in observations if observation.is_supplemental
    }
    assert supplemental_texts == {"123-45-6789"}
