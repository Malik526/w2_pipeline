from pathlib import Path

import pytest
from PIL import Image

from w2_pipeline.extraction.errors import MissingOcrDependencyError
from w2_pipeline.extraction.models import ObservationSource
from w2_pipeline.extraction.ocr import TesseractOcrAdapter, parse_tesseract_tsv


def test_tesseract_tsv_output_converts_to_observations() -> None:
    tsv = "\t".join(
        ["level", "page_num", "block_num", "par_num", "line_num", "word_num", "left", "top", "width", "height", "conf", "text"]
    )
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
