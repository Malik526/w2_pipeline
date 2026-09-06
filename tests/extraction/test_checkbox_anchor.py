import inspect
from pathlib import Path

from PIL import Image, ImageDraw

from w2_pipeline.extraction.checkbox_anchor import (
    DEFAULT_INTERIOR_INK_THRESHOLD,
    compute_interior_ink_ratio,
    derive_checkbox_search_region,
    detect_retirement_plan,
    find_retirement_plan_anchor,
    locate_checkbox_candidate,
)
from w2_pipeline.extraction.models import BoundingBox, ObservationSource, TextObservation


def _obs(text: str, x0: float, y0: float, width: float = 100, height: float = 27) -> TextObservation:
    return TextObservation(
        text=text,
        page=1,
        bbox=BoundingBox(x0=x0, y0=y0, x1=x0 + width, y1=y0 + height),
        source=ObservationSource.OCR,
    )


# --- Anchor matching ------------------------------------------------------


def test_finds_merged_single_observation_anchor() -> None:
    observations = [_obs("Retirement plan", 1600, 805, width=105)]

    anchor = find_retirement_plan_anchor(observations)

    assert anchor is not None
    assert anchor.matched_texts == ("Retirement plan",)


def test_finds_two_line_split_anchor_real_shape() -> None:
    """Reproduces the real PaddleOCR shape: "Retirement" and "plan" as
    two separate, vertically-stacked observations."""

    observations = [
        _obs("Retirement", 1601, 805, width=104, height=20),
        _obs("plan", 1598, 824, width=49, height=27),
    ]

    anchor = find_retirement_plan_anchor(observations)

    assert anchor is not None
    assert anchor.matched_texts == ("Retirement", "plan")
    assert anchor.lower_line_bbox.y0 == 824


def test_anchor_matching_is_case_insensitive() -> None:
    observations = [_obs("RETIREMENT PLAN", 1600, 805, width=105)]

    assert find_retirement_plan_anchor(observations) is not None


def test_anchor_matching_tolerates_harmless_whitespace() -> None:
    observations = [_obs("Retirement   plan", 1600, 805, width=110)]

    assert find_retirement_plan_anchor(observations) is not None


def test_unrelated_plans_text_does_not_match_as_the_plan_line() -> None:
    """"11 Nonqualified plans" contains "plan" only as part of "plans" --
    `\\bplan\\b` must not match it, and it must not be paired with a
    nearby "Retirement" observation as if it were the real label."""

    observations = [
        _obs("Retirement", 1601, 805, width=104, height=20),
        _obs("11 Nonqualified plans", 1400, 705, width=300, height=30),
    ]

    anchor = find_retirement_plan_anchor(observations)

    assert anchor is None


def test_anchor_missing_returns_none() -> None:
    observations = [_obs("Statutory employee", 1400, 800, width=150)]

    assert find_retirement_plan_anchor(observations) is None


def test_anchor_requires_plan_line_below_not_above_retirement() -> None:
    observations = [
        _obs("Retirement", 1601, 900, width=104, height=20),
        _obs("plan", 1598, 800, width=49, height=27),  # above, not below
    ]

    assert find_retirement_plan_anchor(observations) is None


# --- Local geometry ---------------------------------------------------


def test_search_region_is_directly_below_and_scales_with_label_size() -> None:
    observations = [
        _obs("Retirement", 1601, 805, width=104, height=20),
        _obs("plan", 1598, 824, width=49, height=27),
    ]
    anchor = find_retirement_plan_anchor(observations)
    assert anchor is not None

    region = derive_checkbox_search_region(anchor)

    assert region.y0 >= anchor.lower_line_bbox.y0
    assert region.y1 > anchor.lower_line_bbox.y1
    assert region.x0 < anchor.lower_line_bbox.x0
    assert region.x1 > anchor.lower_line_bbox.x1


def test_search_region_translates_with_the_label_anywhere_on_the_page() -> None:
    """The search region must follow the label's own position -- not any
    fixed page-global location -- confirmed by placing the identical
    label/checkbox pair at two very different page positions."""

    near_top_left = [
        _obs("Retirement", 100, 100, width=104, height=20),
        _obs("plan", 97, 119, width=49, height=27),
    ]
    near_bottom_right = [
        _obs("Retirement", 2000, 3000, width=104, height=20),
        _obs("plan", 1997, 3019, width=49, height=27),
    ]

    region_a = derive_checkbox_search_region(find_retirement_plan_anchor(near_top_left))
    region_b = derive_checkbox_search_region(find_retirement_plan_anchor(near_bottom_right))

    offset_x = 2000 - 100
    offset_y = 3000 - 100
    assert round(region_b.x0 - region_a.x0) == offset_x
    assert round(region_b.y0 - region_a.y0) == offset_y


def test_search_region_scales_with_a_larger_scanned_label() -> None:
    small_label = [
        _obs("Retirement", 1601, 805, width=104, height=20),
        _obs("plan", 1598, 824, width=49, height=27),
    ]
    large_label = [
        _obs("Retirement", 3202, 1610, width=208, height=40),
        _obs("plan", 3196, 1648, width=98, height=54),
    ]

    region_small = derive_checkbox_search_region(find_retirement_plan_anchor(small_label))
    region_large = derive_checkbox_search_region(find_retirement_plan_anchor(large_label))

    small_height = region_small.y1 - region_small.y0
    large_height = region_large.y1 - region_large.y0
    # 2x scaled input label -> roughly 2x scaled search region, not a
    # fixed absolute pixel size.
    assert 1.7 < (large_height / small_height) < 2.3


# --- Candidate detection + interior classification ------------------------


def _draw_checkbox(
    draw: ImageDraw.ImageDraw, *, x0: int, y0: int, size: int = 46, border: int = 3, checked: bool = False
) -> None:
    draw.rectangle([x0, y0, x0 + size, y0 + size], outline=0, width=border)
    if checked:
        draw.line([x0 + 8, y0 + size // 2, x0 + size // 2, y0 + size - 8], fill=0, width=4)
        draw.line([x0 + size // 2, y0 + size - 8, x0 + size - 6, y0 + 8], fill=0, width=4)


def _synthetic_page(width: int = 400, height: int = 300) -> Image.Image:
    return Image.new("L", (width, height), color=255)


def test_locate_checkbox_candidate_finds_an_empty_box() -> None:
    image = _synthetic_page()
    draw = ImageDraw.Draw(image)
    _draw_checkbox(draw, x0=100, y0=140, checked=False)
    anchor_observation = _obs("Retirement plan", 60, 100, width=88, height=27)
    anchor = find_retirement_plan_anchor([anchor_observation])
    assert anchor is not None
    region = derive_checkbox_search_region(anchor)

    candidate = locate_checkbox_candidate(image, region, anchor)

    assert candidate is not None
    assert candidate.shape_score > 0.5


def test_interior_ink_ratio_distinguishes_checked_from_unchecked() -> None:
    empty_image = _synthetic_page()
    ImageDraw.Draw(empty_image).rectangle([100, 140, 146, 186], outline=0, width=3)
    checked_image = _synthetic_page()
    _draw_checkbox(ImageDraw.Draw(checked_image), x0=100, y0=140, checked=True)

    anchor_observation = _obs("Retirement plan", 60, 100, width=88, height=27)
    anchor = find_retirement_plan_anchor([anchor_observation])
    assert anchor is not None
    region = derive_checkbox_search_region(anchor)

    empty_candidate = locate_checkbox_candidate(empty_image, region, anchor)
    checked_candidate = locate_checkbox_candidate(checked_image, region, anchor)
    assert empty_candidate is not None
    assert checked_candidate is not None

    empty_ratio = compute_interior_ink_ratio(empty_image, empty_candidate)
    checked_ratio = compute_interior_ink_ratio(checked_image, checked_candidate)

    assert empty_ratio < DEFAULT_INTERIOR_INK_THRESHOLD
    assert checked_ratio >= DEFAULT_INTERIOR_INK_THRESHOLD
    assert checked_ratio > empty_ratio


def test_printed_border_alone_is_not_counted_as_a_mark() -> None:
    """A thicker-than-usual border must not, on its own, push the
    interior ink ratio over the threshold -- only genuine interior marks
    should."""

    image = _synthetic_page()
    ImageDraw.Draw(image).rectangle([100, 140, 146, 186], outline=0, width=6)
    anchor_observation = _obs("Retirement plan", 60, 100, width=88, height=27)
    anchor = find_retirement_plan_anchor([anchor_observation])
    assert anchor is not None
    region = derive_checkbox_search_region(anchor)

    candidate = locate_checkbox_candidate(image, region, anchor)
    assert candidate is not None
    ratio = compute_interior_ink_ratio(image, candidate)

    assert ratio < DEFAULT_INTERIOR_INK_THRESHOLD


def test_no_checkbox_shaped_content_in_region_returns_none() -> None:
    image = _synthetic_page()  # blank -- no checkbox drawn at all
    anchor_observation = _obs("Retirement plan", 60, 100, width=88, height=27)
    anchor = find_retirement_plan_anchor([anchor_observation])
    assert anchor is not None
    region = derive_checkbox_search_region(anchor)

    candidate = locate_checkbox_candidate(image, region, anchor)

    assert candidate is None


# --- Full pipeline, tmp_path-based image files -----------------------------


def test_detect_retirement_plan_end_to_end_checked(tmp_path: Path) -> None:
    image = _synthetic_page()
    _draw_checkbox(ImageDraw.Draw(image), x0=100, y0=140, checked=True)
    path = tmp_path / "checked.png"
    image.save(path)
    observations = [_obs("Retirement plan", 60, 100, width=88, height=27)]

    result = detect_retirement_plan(path, observations)

    assert result.anchor_found
    assert result.checkbox_found
    assert result.retirement_plan is True


def test_detect_retirement_plan_end_to_end_unchecked(tmp_path: Path) -> None:
    image = _synthetic_page()
    ImageDraw.Draw(image).rectangle([100, 140, 146, 186], outline=0, width=3)
    path = tmp_path / "unchecked.png"
    image.save(path)
    observations = [_obs("Retirement plan", 60, 100, width=88, height=27)]

    result = detect_retirement_plan(path, observations)

    assert result.anchor_found
    assert result.checkbox_found
    assert result.retirement_plan is False


def test_detect_retirement_plan_never_fabricates_a_result_without_an_anchor(tmp_path: Path) -> None:
    image = _synthetic_page()
    path = tmp_path / "no_anchor.png"
    image.save(path)
    observations = [_obs("Statutory employee", 50, 50, width=150)]

    result = detect_retirement_plan(path, observations)

    assert not result.anchor_found
    assert result.retirement_plan is None


# --- Leakage / architecture -------------------------------------------


def test_find_retirement_plan_anchor_takes_only_observations() -> None:
    signature = inspect.signature(find_retirement_plan_anchor)
    assert list(signature.parameters) == ["observations"]


def test_detect_retirement_plan_takes_no_variant_or_ground_truth_parameter() -> None:
    signature = inspect.signature(detect_retirement_plan)
    assert set(signature.parameters) == {"image_path", "observations", "interior_ink_threshold"}


def test_module_has_no_validation_dependency() -> None:
    import ast

    import w2_pipeline.extraction.checkbox_anchor as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)

    assert not any(module_name.startswith("w2_pipeline.validation") for module_name in imported)
