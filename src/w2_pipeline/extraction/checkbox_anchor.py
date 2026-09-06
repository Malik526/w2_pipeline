"""Phase 8C.10: OCR-anchor-relative `box_13.retirement_plan` checkbox detector.

`checkbox_vision.RETIREMENT_PLAN_ZONE` locates the checkbox using a fixed
page-global ratio zone. Phase 8C.9 showed this is geometrically fragile:
the raw `rotated_png` variant's canvas is already a different size than
the clean render's before any rotation is even considered, so a
fixed-zone ratio can land on the wrong printed structure entirely (a
table gridline, not the checkbox) once the page's global geometry
shifts.

This module localizes the checkbox **relative to something that moves
with it**: the printed "Retirement plan" label, already present in the
same OCR observations Pipeline A already produced (no second OCR pass).
Verified directly against real documents before writing any detection
code (see `docs/experiments/phase8c10-anchor-relative-checkbox-detector.md`,
"Real Geometry Investigation"): on both a clean render and a rotated
document, the checkbox sits immediately below the label's lower line
("plan"), left-aligned with it -- a small, stable *local* relationship
that holds even though the checkbox's *global* page position differs
enormously between the two documents.

## Runtime contract

Every function here takes only OCR observations and/or the source image
-- never `variant_id`, filename, dataset labels, or ground truth. Ground
truth is used only offline, after detection, for evaluation/calibration
(`run_anchor_checkbox_localization_scan.py`,
`run_anchor_checkbox_benchmark.py` in `w2_pipeline.evaluation`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from w2_pipeline.extraction.models import BoundingBox, TextObservation

_RETIREMENT_RE = re.compile(r"retirement", re.IGNORECASE)
_PLAN_RE = re.compile(r"\bplan\b", re.IGNORECASE)

# How far below/around the anchor's own bounding box to search for the
# checkbox, expressed as multiples of the anchor's own line height/width
# -- never raw page pixels -- so the same relative search region works
# regardless of the page's global scale or rotation.
SEARCH_BELOW_HEIGHT_MULTIPLIER = 3.0
SEARCH_HORIZONTAL_MARGIN_MULTIPLIER = 0.6

# Calibrated offline (Section 11 of the phase doc) against the frozen
# 600-document evaluation set's ground truth -- never against a single
# document, and never using variant/filename/document-ID information.
DEFAULT_INTERIOR_INK_THRESHOLD = 0.12
_DARK_PIXEL_THRESHOLD = 160
_BORDER_INSET_FRACTION = 0.22


@dataclass(frozen=True)
class AnchorMatch:
    """The located "Retirement plan" label, combined from one or two
    OCR observations (some OCR output merges it into one line; PaddleOCR
    was observed splitting it into "Retirement" and "plan" on separate
    lines -- both are handled)."""

    bbox: BoundingBox
    matched_texts: tuple[str, ...]
    lower_line_bbox: BoundingBox


@dataclass(frozen=True)
class CheckboxCandidate:
    bbox: BoundingBox
    anchor_distance_px: float
    horizontal_alignment_offset_px: float
    shape_score: float


@dataclass(frozen=True)
class RetirementPlanDetection:
    """Complete, ground-truth-free detection evidence for one document.

    `retirement_plan` is `None` (never fabricated as `False`) when the
    anchor or checkbox candidate could not be located confidently.
    """

    anchor_found: bool
    anchor: AnchorMatch | None
    checkbox_found: bool
    checkbox: CheckboxCandidate | None
    interior_ink_ratio: float | None
    retirement_plan: bool | None
    decision_margin: float | None


def find_retirement_plan_anchor(observations: list[TextObservation]) -> AnchorMatch | None:
    """Locate the printed "Retirement plan" label among OCR observations.

    Handles both a single merged observation ("Retirement plan") and the
    two-line-split case actually observed from PaddleOCR ("Retirement"
    and "plan" as separate observations, one above the other). Exact/
    normalized substring matching only -- deliberately not fuzzy, per
    the brief's instruction to prefer exact matching first.
    """

    merged = [
        observation
        for observation in observations
        if _RETIREMENT_RE.search(observation.text) and _PLAN_RE.search(observation.text)
    ]
    if merged:
        best = min(merged, key=lambda observation: observation.bbox.y0)
        return AnchorMatch(bbox=best.bbox, matched_texts=(best.text,), lower_line_bbox=best.bbox)

    retirement_candidates = [observation for observation in observations if _RETIREMENT_RE.search(observation.text)]
    plan_candidates = [
        observation
        for observation in observations
        if _PLAN_RE.search(observation.text) and not _RETIREMENT_RE.search(observation.text)
    ]
    if not retirement_candidates or not plan_candidates:
        return None

    best_pair: tuple[TextObservation, TextObservation] | None = None
    best_distance = float("inf")
    for retirement_observation in retirement_candidates:
        for plan_observation in plan_candidates:
            # "plan" must be the next line down, roughly x-aligned --
            # a W-2-local structural constraint, not document metadata.
            if plan_observation.bbox.y0 < retirement_observation.bbox.y0:
                continue
            retirement_height = retirement_observation.bbox.y1 - retirement_observation.bbox.y0
            horizontal_offset = abs(plan_observation.bbox.x0 - retirement_observation.bbox.x0)
            vertical_gap = plan_observation.bbox.y0 - retirement_observation.bbox.y1
            if horizontal_offset > 3 * retirement_height:
                continue
            # OCR line boxes for adjacent wrapped lines can genuinely
            # overlap by several pixels (observed directly under blur:
            # -7px), so a generous negative lower bound is required, not
            # just a small allowance for exact-adjacency noise.
            if vertical_gap < -0.75 * retirement_height or vertical_gap > 2 * retirement_height:
                continue
            distance = horizontal_offset + abs(vertical_gap)
            if distance < best_distance:
                best_distance = distance
                best_pair = (retirement_observation, plan_observation)

    if best_pair is None:
        return None
    retirement_observation, plan_observation = best_pair
    combined = BoundingBox(
        x0=min(retirement_observation.bbox.x0, plan_observation.bbox.x0),
        y0=retirement_observation.bbox.y0,
        x1=max(retirement_observation.bbox.x1, plan_observation.bbox.x1),
        y1=plan_observation.bbox.y1,
    )
    return AnchorMatch(
        bbox=combined,
        matched_texts=(retirement_observation.text, plan_observation.text),
        lower_line_bbox=plan_observation.bbox,
    )


def derive_checkbox_search_region(anchor: AnchorMatch) -> BoundingBox:
    """The local region to search for the checkbox: directly below the
    anchor's lower line, sized relative to the anchor's own dimensions
    -- never a raw page-global zone."""

    lower = anchor.lower_line_bbox
    line_height = lower.y1 - lower.y0
    line_width = lower.x1 - lower.x0
    horizontal_margin = line_width * SEARCH_HORIZONTAL_MARGIN_MULTIPLIER
    return BoundingBox(
        x0=lower.x0 - horizontal_margin,
        y0=lower.y1 - line_height * 0.2,
        x1=lower.x1 + horizontal_margin,
        y1=lower.y1 + line_height * SEARCH_BELOW_HEIGHT_MULTIPLIER,
    )


def _row_dark_runs(row_pixels: list[int]) -> int:
    """Longest contiguous run of dark pixels in one pixel row."""

    longest = current = 0
    for pixel in row_pixels:
        if pixel < _DARK_PIXEL_THRESHOLD:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def locate_checkbox_candidate(
    image: Image.Image, search_region: BoundingBox, anchor: AnchorMatch
) -> CheckboxCandidate | None:
    """Find the checkbox's rectangular border within `search_region`.

    Deterministic, Pillow-only (no OpenCV/numpy): scans for the two
    horizontal border rows (top and bottom of the square) as the rows
    with the longest contiguous dark-pixel run, then scans for the two
    vertical border columns between them the same way. This identifies
    the checkbox's own border/shape first, rather than merely searching
    for "dark pixels" anywhere in the region (which would not distinguish
    the checkbox from a stray ink mark or gridline crossing).
    """

    width, height = image.size
    x0 = max(0, int(search_region.x0))
    y0 = max(0, int(search_region.y0))
    x1 = min(width, int(search_region.x1))
    y1 = min(height, int(search_region.y1))
    if x1 <= x0 or y1 <= y0:
        return None

    crop = image.crop((x0, y0, x1, y1)).convert("L")
    crop_width, crop_height = crop.size
    pixels = list(crop.getdata())
    rows = [pixels[row * crop_width : (row + 1) * crop_width] for row in range(crop_height)]

    # A checkbox border run is expected to be roughly as wide as the
    # anchor's own text line height (observed directly: ~1.5-1.7x on real
    # documents) -- scaled off the anchor, not the search region's own
    # width, since the region includes generous alignment-uncertainty
    # margins the checkbox itself does not fill.
    anchor_line_height = anchor.lower_line_bbox.y1 - anchor.lower_line_bbox.y0
    min_border_run = max(anchor_line_height * 1.0, 10.0)
    border_rows = [row_index for row_index, row in enumerate(rows) if _row_dark_runs(row) >= min_border_run]
    if len(border_rows) < 2:
        return None

    top_row = border_rows[0]
    bottom_row = border_rows[-1]
    box_height = bottom_row - top_row
    if box_height < anchor_line_height * 0.5:
        return None

    columns = [[pixels[row * crop_width + col] for row in range(top_row, bottom_row + 1)] for col in range(crop_width)]
    min_border_run_vertical = box_height * 0.5
    border_columns = [col_index for col_index, column in enumerate(columns) if _row_dark_runs(column) >= min_border_run_vertical]
    if len(border_columns) < 2:
        return None

    left_col = border_columns[0]
    right_col = border_columns[-1]
    box_width = right_col - left_col
    if box_width <= 0:
        return None

    aspect_ratio = box_width / box_height if box_height else 0.0
    shape_score = 1.0 - min(abs(aspect_ratio - 1.0), 1.0)

    candidate_bbox = BoundingBox(
        x0=x0 + left_col,
        y0=y0 + top_row,
        x1=x0 + right_col,
        y1=y0 + bottom_row,
    )
    candidate_center_x = (candidate_bbox.x0 + candidate_bbox.x1) / 2
    anchor_center_x = (anchor.lower_line_bbox.x0 + anchor.lower_line_bbox.x1) / 2
    horizontal_alignment_offset = abs(candidate_center_x - anchor_center_x)
    anchor_distance = candidate_bbox.y0 - anchor.lower_line_bbox.y1

    return CheckboxCandidate(
        bbox=candidate_bbox,
        anchor_distance_px=anchor_distance,
        horizontal_alignment_offset_px=horizontal_alignment_offset,
        shape_score=shape_score,
    )


def compute_interior_ink_ratio(image: Image.Image, checkbox: CheckboxCandidate) -> float:
    """Ink ratio inside the checkbox, excluding a border band.

    The printed checkbox border itself contributes dark pixels that must
    not be counted as a "mark" -- only the interior, inset by
    `_BORDER_INSET_FRACTION` on each side, is inspected.
    """

    bbox = checkbox.bbox
    width = bbox.x1 - bbox.x0
    height = bbox.y1 - bbox.y0
    inset_x = width * _BORDER_INSET_FRACTION
    inset_y = height * _BORDER_INSET_FRACTION
    interior_box = (
        round(bbox.x0 + inset_x),
        round(bbox.y0 + inset_y),
        round(bbox.x1 - inset_x),
        round(bbox.y1 - inset_y),
    )
    if interior_box[2] <= interior_box[0] or interior_box[3] <= interior_box[1]:
        return 0.0
    crop = image.crop(interior_box).convert("L")
    histogram = crop.histogram()
    dark_pixel_count = sum(histogram[:_DARK_PIXEL_THRESHOLD])
    total_pixels = crop.width * crop.height
    return dark_pixel_count / total_pixels if total_pixels else 0.0


def detect_retirement_plan(
    image_path: str | Path,
    observations: list[TextObservation],
    *,
    interior_ink_threshold: float = DEFAULT_INTERIOR_INK_THRESHOLD,
) -> RetirementPlanDetection:
    """Full anchor-relative detection pipeline for one document.

    Never fabricates a result: if the anchor or checkbox cannot be
    located, `retirement_plan` is `None`, not `False`.
    """

    anchor = find_retirement_plan_anchor(observations)
    if anchor is None:
        return RetirementPlanDetection(
            anchor_found=False,
            anchor=None,
            checkbox_found=False,
            checkbox=None,
            interior_ink_ratio=None,
            retirement_plan=None,
            decision_margin=None,
        )

    search_region = derive_checkbox_search_region(anchor)
    with Image.open(image_path) as image:
        checkbox = locate_checkbox_candidate(image, search_region, anchor)
        if checkbox is None:
            return RetirementPlanDetection(
                anchor_found=True,
                anchor=anchor,
                checkbox_found=False,
                checkbox=None,
                interior_ink_ratio=None,
                retirement_plan=None,
                decision_margin=None,
            )
        interior_ink_ratio = compute_interior_ink_ratio(image, checkbox)

    retirement_plan = interior_ink_ratio >= interior_ink_threshold
    decision_margin = interior_ink_ratio - interior_ink_threshold
    return RetirementPlanDetection(
        anchor_found=True,
        anchor=anchor,
        checkbox_found=True,
        checkbox=checkbox,
        interior_ink_ratio=interior_ink_ratio,
        retirement_plan=retirement_plan,
        decision_margin=decision_margin,
    )
