from w2_pipeline.evaluation.employer_name_layout_signals import (
    EMPLOYER_NAME_ZONE,
    compute_layout_signals,
    find_employer_name_row_group,
)
from w2_pipeline.extraction.models import BoundingBox, ObservationSource, TextObservation

_MAX_Y = 1700.0
_MAX_X = 2000.0
_ZONE_Y0 = EMPLOYER_NAME_ZONE[2] * _MAX_Y


def _obs(text: str, x0: float, y0: float, width: float = 250, height: float = 40) -> TextObservation:
    return TextObservation(
        text=text,
        page=1,
        bbox=BoundingBox(x0=x0, y0=y0, x1=x0 + width, y1=y0 + height),
        source=ObservationSource.OCR,
    )


def _filler() -> TextObservation:
    """Sets page extent (`max_x`/`max_y`) without landing inside the
    employer-name zone itself: its own center falls well outside the
    zone's y-ratio band, so `_observations_in_zone` never includes it."""

    return _obs("filler", 0, 0, width=_MAX_X, height=_MAX_Y)


def test_single_observation_row_span_equals_its_own_text_height() -> None:
    """A single-observation row's span is that observation's own bounding
    box height -- not zero -- since span is measured over the whole row
    (`y_max - y_min`), which for one observation is just its own extent.
    This is the expected baseline for a normal, correct, single-line
    employer name (confirmed against real data: ~39-49px)."""

    observation = _obs("Timberline Trading Co.", 200, _ZONE_Y0 + 20, height=40)

    signals = compute_layout_signals("Timberline Trading Co.", [observation, _filler()])

    assert signals.matched
    assert signals.observation_count == 1
    assert signals.vertical_span_px == 40.0
    assert signals.max_center_y_gap_px == 0.0
    assert signals.tight_sub_row_count == 1


def test_multi_observation_merged_row_has_larger_span_and_two_sub_rows() -> None:
    """Reproduces the real shape: name and a merged address line clustered
    into one row-group by `_group_observation_rows`'s tolerance (which
    scales with each observation's own height -- tall enough observations
    with a 33px center-to-center gap fall within it, matching the real
    diagnosed case), while still being far enough apart for the tight,
    fixed 15px reclustering diagnostic to see them as two real physical
    lines."""

    height = 60.0  # tolerance = max(6, height * 0.65) = 39, comfortably >= the 33px gap below.
    name_row = _obs("Elan Consulting Corp", 200, _ZONE_Y0 + 20, width=250, height=height)
    address_row = _obs(
        "2861 Geneva Ponce De Leon Rd", 200, _ZONE_Y0 + 20 + 33, width=350, height=height
    )

    signals = compute_layout_signals(
        "Elan Consulting Corp 2861 Geneva Ponce De Leon Rd", [name_row, address_row, _filler()]
    )

    assert signals.matched
    assert signals.observation_count == 2
    # Span covers both lines' extent, well beyond either line's own height.
    assert signals.vertical_span_px == height + 33.0
    assert signals.max_center_y_gap_px == 33.0
    assert signals.tight_sub_row_count == 2


def test_no_matching_row_group_reports_unmatched() -> None:
    observations = [_obs("something else entirely", 200, _ZONE_Y0 + 20), _filler()]

    signals = compute_layout_signals("Timberline Trading Co.", observations)

    assert not signals.matched
    assert signals.observation_count == 0
    assert signals.vertical_span_px is None


def test_none_predicted_name_reports_unmatched_without_crashing() -> None:
    signals = compute_layout_signals(None, [_obs("Timberline Trading Co.", 200, _ZONE_Y0 + 20), _filler()])

    assert not signals.matched


def test_empty_observations_reports_unmatched() -> None:
    signals = compute_layout_signals("Timberline Trading Co.", [])

    assert not signals.matched


def test_vertical_span_ratio_normalizes_by_page_height() -> None:
    tall_row = _obs("Timberline Trading Co.", 200, _ZONE_Y0 + 20, height=170)

    signals = compute_layout_signals("Timberline Trading Co.", [tall_row, _filler()])

    assert signals.vertical_span_ratio == 170.0 / _MAX_Y
    zone_height_ratio = EMPLOYER_NAME_ZONE[3] - EMPLOYER_NAME_ZONE[2]
    assert signals.zone_span_ratio == (170.0 / _MAX_Y) / zone_height_ratio


def test_find_employer_name_row_group_returns_the_matching_observations() -> None:
    target = _obs("Timberline Trading Co.", 200, _ZONE_Y0 + 20, height=39)

    row = find_employer_name_row_group("Timberline Trading Co.", [target, _filler()])

    assert row is not None
    assert [observation.text for observation in row] == ["Timberline Trading Co."]


def test_find_employer_name_row_group_returns_none_when_zone_is_empty() -> None:
    row = find_employer_name_row_group("Timberline Trading Co.", [_filler()])

    assert row is None


def test_module_has_no_semantic_address_heuristic_dependency() -> None:
    """Phase 8C.6 must be an independent signal family from Phase 8C.5's
    address-leak heuristic (no street-number/road-suffix/ZIP inspection,
    and no import of that module) -- geometry only."""

    import ast
    from pathlib import Path

    import w2_pipeline.evaluation.employer_name_layout_signals as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
        elif isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)

    assert "w2_pipeline.evaluation.employer_name_heuristics" not in imported_modules


def test_parser_module_does_not_import_this_phases_evaluation_code() -> None:
    """No new dependency was introduced from the production parser back
    into this phase's evaluation-side code -- the dependency direction
    stays evaluation -> extraction, never the reverse."""

    import ast
    from pathlib import Path

    import w2_pipeline.extraction.parser_2026 as parser_module

    source = Path(parser_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
        elif isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)

    assert not any(module.startswith("w2_pipeline.evaluation") for module in imported_modules)
