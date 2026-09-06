import inspect
from pathlib import Path

from PIL import Image, ImageDraw

from w2_pipeline.extraction.deskew import (
    DEFAULT_TRIGGER_THRESHOLD_DEGREES,
    deskew_image_if_needed,
    estimate_skew_angle_degrees,
    rotate_image_file,
    should_deskew,
)


def _bars_image(width: int = 600, height: int = 400) -> Image.Image:
    """A synthetic 'form' image: horizontal bars simulating printed text
    rows/table gridlines, on a white background."""

    image = Image.new("L", (width, height), color=255)
    draw = ImageDraw.Draw(image)
    for y in range(40, height - 20, 30):
        draw.rectangle([40, y, width - 40, y + 8], fill=0)
    return image


def _save(image: Image.Image, path: Path) -> Path:
    image.save(path)
    return path


def test_upright_image_detects_near_zero_skew(tmp_path: Path) -> None:
    path = _save(_bars_image(), tmp_path / "upright.png")

    angle = estimate_skew_angle_degrees(path)

    assert abs(angle) < 0.05


def test_skewed_image_detects_the_correct_magnitude(tmp_path: Path) -> None:
    base = _bars_image()
    skewed = base.rotate(5.0, resample=Image.BICUBIC, expand=True, fillcolor=255)
    path = _save(skewed, tmp_path / "skewed.png")

    angle = estimate_skew_angle_degrees(path)

    # Correction angle undoes the +5.0 applied above -- confirms the sign
    # convention matches PIL's own `Image.rotate` (verified directly
    # against a real diagnosed rotated W-2 document; see the module
    # docstring and docs/experiments/phase8c9-conditional-scan-deskew.md).
    assert -5.5 < angle < -4.5


def test_inverse_rotation_sign_recovers_upright_content(tmp_path: Path) -> None:
    """Applying the estimated correction back to the skewed image should
    make it near-upright again -- the end-to-end sign/idempotence check,
    not just the raw angle value."""

    base = _bars_image()
    skewed = base.rotate(3.0, resample=Image.BICUBIC, expand=True, fillcolor=255)
    skewed_path = _save(skewed, tmp_path / "skewed3.png")

    angle = estimate_skew_angle_degrees(skewed_path)
    corrected_path = rotate_image_file(skewed_path, angle, tmp_path / "corrected3.png")

    residual_angle = estimate_skew_angle_degrees(corrected_path)
    assert abs(residual_angle) < 0.5


def test_trigger_threshold_behavior() -> None:
    assert not should_deskew(0.3, threshold_degrees=DEFAULT_TRIGGER_THRESHOLD_DEGREES)
    assert not should_deskew(-0.3, threshold_degrees=DEFAULT_TRIGGER_THRESHOLD_DEGREES)
    assert should_deskew(2.0, threshold_degrees=DEFAULT_TRIGGER_THRESHOLD_DEGREES)
    assert should_deskew(-2.0, threshold_degrees=DEFAULT_TRIGGER_THRESHOLD_DEGREES)


def test_upright_form_inside_upright_canvas_does_not_trigger(tmp_path: Path) -> None:
    path = _save(_bars_image(), tmp_path / "upright.png")

    resolved_path, angle, corrected = deskew_image_if_needed(path, output_dir=tmp_path / "out")

    assert not corrected
    assert abs(angle) < 0.05
    # The ORIGINAL path is reused, not a re-saved copy.
    assert resolved_path == path


def test_original_image_reused_when_no_correction_needed(tmp_path: Path) -> None:
    path = _save(_bars_image(), tmp_path / "upright.png")
    output_dir = tmp_path / "out"

    resolved_path, _angle, corrected = deskew_image_if_needed(path, output_dir=output_dir)

    assert not corrected
    assert resolved_path == path
    assert not output_dir.exists() or list(output_dir.iterdir()) == []


def test_skewed_form_inside_upright_canvas_triggers_correction(tmp_path: Path) -> None:
    base = _bars_image()
    skewed = base.rotate(2.5, resample=Image.BICUBIC, expand=True, fillcolor=255)
    path = _save(skewed, tmp_path / "skewed.png")

    resolved_path, angle, corrected = deskew_image_if_needed(path, output_dir=tmp_path / "out")

    assert corrected
    assert resolved_path != path
    assert resolved_path.exists()
    assert -3.0 < angle < -2.0


def test_no_clipping_canvas_expands_for_a_triggered_correction(tmp_path: Path) -> None:
    base = _bars_image(width=600, height=400)
    skewed = base.rotate(4.0, resample=Image.BICUBIC, expand=True, fillcolor=255)
    path = _save(skewed, tmp_path / "skewed.png")
    original_size = skewed.size

    resolved_path, _angle, corrected = deskew_image_if_needed(path, output_dir=tmp_path / "out")

    assert corrected
    with Image.open(resolved_path) as corrected_image:
        assert corrected_image.size[0] >= original_size[0]
        assert corrected_image.size[1] >= original_size[1]


def test_deterministic_angle_estimate(tmp_path: Path) -> None:
    base = _bars_image()
    skewed = base.rotate(3.5, resample=Image.BICUBIC, expand=True, fillcolor=255)
    path = _save(skewed, tmp_path / "skewed.png")

    first = estimate_skew_angle_degrees(path)
    second = estimate_skew_angle_degrees(path)

    assert first == second


def test_idempotence_second_pass_on_corrected_image_finds_near_zero_skew(tmp_path: Path) -> None:
    base = _bars_image()
    skewed = base.rotate(6.0, resample=Image.BICUBIC, expand=True, fillcolor=255)
    skewed_path = _save(skewed, tmp_path / "skewed.png")

    corrected_path, _angle, corrected = deskew_image_if_needed(skewed_path, output_dir=tmp_path / "out")
    assert corrected

    second_pass_path, second_angle, second_corrected = deskew_image_if_needed(
        corrected_path, output_dir=tmp_path / "out2"
    )

    assert not second_corrected
    assert abs(second_angle) < DEFAULT_TRIGGER_THRESHOLD_DEGREES
    assert second_pass_path == corrected_path


def test_estimate_skew_angle_degrees_takes_only_image_path_and_detector_parameters() -> None:
    """Structural safeguard: no `variant_id`, filename-derived label, or
    ground-truth parameter exists on the detector's signature -- it can
    only ever see the image itself."""

    signature = inspect.signature(estimate_skew_angle_degrees)
    param_names = set(signature.parameters)
    assert param_names == {
        "image_path",
        "search_range_degrees",
        "coarse_step_degrees",
        "fine_range_degrees",
        "fine_step_degrees",
        "probe_width_pixels",
    }


def test_deskew_image_if_needed_takes_no_variant_or_ground_truth_parameter() -> None:
    signature = inspect.signature(deskew_image_if_needed)
    param_names = set(signature.parameters)
    assert param_names == {"image_path", "output_dir", "threshold_degrees"}
