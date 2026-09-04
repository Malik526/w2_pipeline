from pathlib import Path

from PIL import Image, ImageDraw

from w2_pipeline.extraction.checkbox_vision import (
    RETIREMENT_PLAN_ZONE,
    detect_box_13_retirement_plan_mark,
    detect_ink_coverage_ratio,
)


def _blank_page(path: Path, *, size: tuple[int, int] = (2550, 3300)) -> None:
    Image.new("L", size, color=255).save(path)


def _draw_zone_border(image: Image.Image, zone: tuple[float, float, float, float]) -> None:
    width, height = image.size
    x0_ratio, x1_ratio, y0_ratio, y1_ratio = zone
    box = (
        round(x0_ratio * width),
        round(y0_ratio * height),
        round(x1_ratio * width),
        round(y1_ratio * height),
    )
    ImageDraw.Draw(image).rectangle(box, outline=0, width=2)


def _draw_zone_filled(image: Image.Image, zone: tuple[float, float, float, float]) -> None:
    width, height = image.size
    x0_ratio, x1_ratio, y0_ratio, y1_ratio = zone
    box = (
        round(x0_ratio * width),
        round(y0_ratio * height),
        round(x1_ratio * width),
        round(y1_ratio * height),
    )
    ImageDraw.Draw(image).rectangle(box, fill=0)


def test_unmarked_checkbox_zone_has_low_ink_coverage(tmp_path: Path) -> None:
    image_path = tmp_path / "unmarked.png"
    image = Image.new("L", (2550, 3300), color=255)
    _draw_zone_border(image, RETIREMENT_PLAN_ZONE)
    image.save(image_path)

    ratio = detect_ink_coverage_ratio(image_path, RETIREMENT_PLAN_ZONE)

    assert ratio < 0.09
    assert detect_box_13_retirement_plan_mark(image_path) is False


def test_marked_checkbox_zone_has_high_ink_coverage(tmp_path: Path) -> None:
    image_path = tmp_path / "marked.png"
    image = Image.new("L", (2550, 3300), color=255)
    _draw_zone_border(image, RETIREMENT_PLAN_ZONE)
    _draw_zone_filled(image, RETIREMENT_PLAN_ZONE)
    image.save(image_path)

    ratio = detect_ink_coverage_ratio(image_path, RETIREMENT_PLAN_ZONE)

    assert ratio >= 0.09
    assert detect_box_13_retirement_plan_mark(image_path) is True


def test_blank_page_reports_no_mark(tmp_path: Path) -> None:
    image_path = tmp_path / "blank.png"
    _blank_page(image_path)

    assert detect_box_13_retirement_plan_mark(image_path) is False


def test_ink_outside_zone_is_ignored(tmp_path: Path) -> None:
    image_path = tmp_path / "unrelated_ink.png"
    image = Image.new("L", (2550, 3300), color=255)
    ImageDraw.Draw(image).rectangle((0, 0, 200, 200), fill=0)
    image.save(image_path)

    assert detect_box_13_retirement_plan_mark(image_path) is False
