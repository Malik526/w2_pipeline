"""Phase 8C.9: conditional small-angle scan-deskew preprocessing for Pipeline A.

Detects and corrects small-angle form/scan tilt (roughly +/-1 to +/-8
degrees -- the form content is uniformly tilted inside an otherwise
upright image canvas) using only the image's own pixel content. This is
deliberately NOT a 90/180/270-degree orientation classifier -- that is a
different, unrelated problem this phase does not address.

## Method: horizontal projection-profile search

For a range of small candidate rotation angles, the (downsampled,
grayscale) image is rotated by each candidate and scored by how sharply
its horizontal ink-density profile is banded -- real printed text/table
rows produce sharp, well-separated horizontal bands of ink when properly
aligned, and a blurred, smeared profile when misaligned. The angle
producing the sharpest profile is the estimated correction: rotating the
real image by exactly that angle (same sign) brings it into alignment.

Chosen over an OCR-bounding-box row-slope method (also considered, see
`docs/experiments/phase8c9-conditional-scan-deskew.md`) because
`_group_observation_rows`'s per-observation-height-scaled tolerance,
applied across a whole two-column page rather than one pre-filtered
zone, was found to chain-merge unrelated same-height text from different
columns into false "rows" with wildly inconsistent slopes -- an
unreliable signal for this whole-page use, confirmed by direct
inspection before this method was chosen instead. The projection-profile
method needs no OCR output at all (it runs on the raw image, before OCR),
uses only Pillow (already a declared project dependency -- no OpenCV or
numpy dependency introduced), and was verified directly against real
diagnosed rotated documents (see the phase doc) to detect a consistent,
plausible angle.

## Runtime contract

`estimate_skew_angle_degrees` and `deskew_image_if_needed` accept only an
image path -- no `variant_id`, filename, dataset label, or ground truth
of any kind. A real production scan carries none of that, and this
module never looks for it.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

# Small-angle scan/form tilt only -- not a 90-degree orientation problem.
DEFAULT_SEARCH_RANGE_DEGREES = 8.0
DEFAULT_COARSE_STEP_DEGREES = 1.0
DEFAULT_FINE_RANGE_DEGREES = 1.0
DEFAULT_FINE_STEP_DEGREES = 0.1
DEFAULT_PROBE_WIDTH_PIXELS = 150

# Conservative: chosen from the measured 600-document distribution
# (docs/experiments/phase8c9-conditional-scan-deskew.md, "Establishing
# The Normal/Upright Distribution") to sit well above the clean/JPEG/blur
# population's own detector noise ceiling and well below the rotated
# population's floor -- not merely because it perfectly separates this
# one synthetic dataset.
DEFAULT_TRIGGER_THRESHOLD_DEGREES = 0.75


def _row_ink_sums(gray_image: Image.Image) -> list[int]:
    width, height = gray_image.size
    pixels = list(gray_image.getdata())
    return [sum(255 - pixel for pixel in pixels[row * width : (row + 1) * width]) for row in range(height)]


def _profile_sharpness_score(gray_image: Image.Image) -> int:
    """Higher = more sharply banded horizontal ink profile (better aligned)."""

    row_sums = _row_ink_sums(gray_image)
    return sum((row_sums[index + 1] - row_sums[index]) ** 2 for index in range(len(row_sums) - 1))


def _best_angle_in_range(
    probe_image: Image.Image, *, start: float, stop: float, step: float
) -> tuple[float, int]:
    best_angle, best_score = 0.0, -1
    angle = start
    while angle <= stop + 1e-9:
        rotated = probe_image.rotate(angle, resample=Image.BILINEAR, expand=False, fillcolor=255)
        score = _profile_sharpness_score(rotated)
        if score > best_score:
            best_score, best_angle = score, angle
        angle += step
    return best_angle, best_score


def estimate_skew_angle_degrees(
    image_path: str | Path,
    *,
    search_range_degrees: float = DEFAULT_SEARCH_RANGE_DEGREES,
    coarse_step_degrees: float = DEFAULT_COARSE_STEP_DEGREES,
    fine_range_degrees: float = DEFAULT_FINE_RANGE_DEGREES,
    fine_step_degrees: float = DEFAULT_FINE_STEP_DEGREES,
    probe_width_pixels: int = DEFAULT_PROBE_WIDTH_PIXELS,
) -> float:
    """Estimate the small-angle correction (degrees) that best aligns the
    image's own printed content -- deterministic given the same image and
    parameters (a two-stage coarse-then-fine grid search, not a
    stochastic method). Positive/negative sign matches
    `PIL.Image.rotate`'s own convention: applying
    `image.rotate(result, expand=True)` is the correction to apply."""

    with Image.open(image_path) as original:
        grayscale = original.convert("L")
        width, _height = grayscale.size
        scale = probe_width_pixels / width
        probe = grayscale.resize((probe_width_pixels, max(1, round(grayscale.size[1] * scale))))

    coarse_best, _coarse_score = _best_angle_in_range(
        probe, start=-search_range_degrees, stop=search_range_degrees, step=coarse_step_degrees
    )
    fine_best, _fine_score = _best_angle_in_range(
        probe,
        start=coarse_best - fine_range_degrees,
        stop=coarse_best + fine_range_degrees,
        step=fine_step_degrees,
    )
    return fine_best


def should_deskew(
    angle_degrees: float, *, threshold_degrees: float = DEFAULT_TRIGGER_THRESHOLD_DEGREES
) -> bool:
    return abs(angle_degrees) > threshold_degrees


def rotate_image_file(image_path: str | Path, angle_degrees: float, output_path: str | Path) -> Path:
    """Apply the inverse-skew correction, expanding the canvas so no
    content is clipped, filling newly-exposed corners with white (a
    neutral page-background fill matching a real scanned/rendered W-2's
    background), and using bicubic interpolation (a standard,
    quality-preserving choice for a small-angle image rotation, as
    opposed to nearest-neighbor's jagged edges or a heavier filter that
    would not measurably improve a sub-10-degree correction)."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(image_path) as image:
        corrected = image.rotate(angle_degrees, resample=Image.BICUBIC, expand=True, fillcolor="white")
        corrected.save(output_path)
    return output_path


def deskew_image_if_needed(
    image_path: str | Path,
    *,
    output_dir: str | Path,
    threshold_degrees: float = DEFAULT_TRIGGER_THRESHOLD_DEGREES,
) -> tuple[Path, float, bool]:
    """Conditionally deskew one image.

    Returns `(path_to_use, estimated_angle_degrees, corrected)`.
    `path_to_use` is the **original, untouched** `image_path` when no
    correction triggers -- deliberately never a re-saved copy of an
    already-upright image, so an already-correct page is never
    resampled or otherwise degraded. Only a triggered correction produces
    a new file, written under `output_dir`.
    """

    image_path = Path(image_path)
    angle = estimate_skew_angle_degrees(image_path)
    if not should_deskew(angle, threshold_degrees=threshold_degrees):
        return image_path, angle, False

    output_path = Path(output_dir) / f"{image_path.stem}_deskewed{image_path.suffix}"
    corrected_path = rotate_image_file(image_path, angle, output_path)
    return corrected_path, angle, True
