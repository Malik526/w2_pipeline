"""Backend-neutral visual checkbox-mark detection for Pipeline A.

OCR backends differ in whether they emit any text observation for a small
non-linguistic checkbox glyph: PaddleOCR's learned text detector does not
treat the Box 13 retirement-plan mark as a text region at all, while
Tesseract's classical segmentation happens to garble it into stray text
(see docs/experiments/pipeline-a-extraction-history.md, "PaddleOCR
box_13.retirement_plan Failure Investigation"). This module answers the
checkbox question directly from page pixels instead of relying on either
backend's OCR text output, so checkbox extraction does not depend on an OCR
engine's incidental willingness to "read" a non-text glyph.

Scope: only the `retirement_plan` zone below is populated by this module.
`statutory_employee` and `third_party_sick_pay` have no ground-truth-positive
example in the currently available benchmark data to calibrate a zone
against, so introducing zones for them here would be an unvalidated guess
risking a regression on fields that are currently 100% correct. They remain
on the existing OCR-token fallback in `parser_2026.py` until a validated
zone can be established.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

# (x0_ratio, x1_ratio, y0_ratio, y1_ratio) as fractions of the true page
# image width/height, not of any OCR-detected text extent. Calibrated
# against the external Symage clean-render benchmark: the retirement-plan
# checkbox glyph sits at this position on every inspected 2550x3300 clean
# render, with the measured ink-coverage ratio separating cleanly into an
# unchecked cluster (~0.0787, checkbox border only) and a checked cluster
# (~0.1000, border plus mark) with no overlap across all 150 documents.
RETIREMENT_PLAN_ZONE: tuple[float, float, float, float] = (0.615, 0.655, 0.250, 0.280)

_DARK_PIXEL_THRESHOLD = 160
_INK_COVERAGE_THRESHOLD = 0.09


def detect_ink_coverage_ratio(
    image_path: str | Path,
    zone: tuple[float, float, float, float],
) -> float:
    """Compute the fraction of dark pixels within a page zone.

    `zone` is expressed as (x0_ratio, x1_ratio, y0_ratio, y1_ratio) relative
    to the actual image dimensions, independent of any OCR output.
    """

    with Image.open(image_path) as image:
        grayscale = image.convert("L")
        width, height = grayscale.size
        x0_ratio, x1_ratio, y0_ratio, y1_ratio = zone
        box = (
            round(x0_ratio * width),
            round(y0_ratio * height),
            round(x1_ratio * width),
            round(y1_ratio * height),
        )
        crop = grayscale.crop(box)
        if crop.width == 0 or crop.height == 0:
            return 0.0
        histogram = crop.histogram()
        dark_pixel_count = sum(histogram[:_DARK_PIXEL_THRESHOLD])
        return dark_pixel_count / (crop.width * crop.height)


def detect_box_13_retirement_plan_mark(image_path: str | Path) -> bool:
    """Visually detect whether the Box 13 retirement-plan checkbox is marked."""

    ratio = detect_ink_coverage_ratio(image_path, RETIREMENT_PLAN_ZONE)
    return ratio >= _INK_COVERAGE_THRESHOLD
