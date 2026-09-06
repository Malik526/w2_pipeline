"""Phase 8C.6: geometry-only layout-span signals for `employer.name`.

This is an OFFLINE VALIDATION EXPERIMENT, not a production change and not
combined with Phase 8C.5's address-leak heuristic. It deliberately
inspects only spatial/provenance evidence -- observation bounding boxes,
counts, vertical spans -- and never the text's semantic content (no
street-number, road-suffix, or ZIP inspection here; that is Phase 8C.5,
kept separate per this phase's brief).

## Provenance: why this reuses two parser functions read-only, unmodified

Phase 8C.4's reverse-value-matcher (`field_confidence.py`) could not
automatically find contributing observations for the 4 known
`employer.name` row-merge failures, because their merged value (name +
full street line) exceeds that matcher's deliberately small
`_MAX_RUN_LENGTH` window. Silently raising that cap was explicitly ruled
out by this phase's brief. Instead, this module takes a different,
smallest-safe approach specific to `employer.name`: it reuses
`_observations_in_zone` and `_group_observation_rows` from
`w2_pipeline.extraction.parser_2026` -- **the exact same functions the
production `employer.name` fallback itself calls** -- read-only, to
reconstruct the exact same row-groups the parser saw. Confirmed directly
against a real failing document (`symage_900033`): zone-restricting to
the real employer.name zone and grouping into rows using the parser's own
`_group_observation_rows` produces a row whose joined text is *exactly*
`"Elan Consulting Corp 2861 Geneva Ponce De Leon Rd"` -- the real merged
prediction -- because that grouping merge is the real root cause (Phase
8C.1) this phase is measuring the geometric footprint of. No parser code
was modified; both functions are called exactly as the parser calls
them, and nothing here feeds back into any parser decision.

The zone tuple `(0.04, 0.35, 0.25, 0.33)` below is a literal copy of the
zone `_apply_ocr_employer_layout_fallbacks` passes to
`_first_row_text_in_zone` in `parser_2026.py` -- if that zone ever
changes, this module's provenance would silently drift out of sync with
production and must be updated alongside it. This coupling is
deliberately documented, not hidden.

## Matching method

For a document's predicted `employer.name` value, every zone-restricted
row-group (not a fixed-size sliding window, unlike Phase 8C.4) is checked
for an exact, whitespace-normalized text match. A row-group is an
unbounded-size cluster by construction (however many observations
`_group_observation_rows`'s tolerance merged), so no window-size cap is
needed or applied here -- this is precisely why it succeeds where Phase
8C.4's capped matcher could not.
"""

from __future__ import annotations

from dataclasses import dataclass

from w2_pipeline.extraction.models import TextObservation
from w2_pipeline.extraction.parser_2026 import _group_observation_rows, _observations_in_zone

# Must stay identical to the zone `_apply_ocr_employer_layout_fallbacks`
# passes to `_first_row_text_in_zone` for `employer.name` in parser_2026.py.
EMPLOYER_NAME_ZONE: tuple[float, float, float, float] = (0.04, 0.35, 0.25, 0.33)

# A tighter, fixed (not per-observation-height-scaled) tolerance used only
# for a secondary, read-only diagnostic reclustering -- never for
# production-equivalent grouping. Estimates how many real physical print
# lines a matched row-group likely absorbed, independent of the exact
# tolerance value that happened to cause an over-merge in production.
_TIGHT_SUB_ROW_TOLERANCE_PX = 15.0


@dataclass(frozen=True)
class EmployerNameLayoutSignals:
    """Raw, non-semantic geometry measurements for one matched row-group."""

    matched: bool
    observation_count: int = 0
    y_min: float | None = None
    y_max: float | None = None
    vertical_span_px: float | None = None
    vertical_span_ratio: float | None = None
    zone_span_ratio: float | None = None
    max_center_y_gap_px: float | None = None
    max_center_y_gap_ratio: float | None = None
    tight_sub_row_count: int | None = None


def _page_height(observations: list[TextObservation]) -> float:
    return max((observation.bbox.y1 for observation in observations), default=1.0)


def find_employer_name_row_group(
    predicted_name: str, observations: list[TextObservation]
) -> list[TextObservation] | None:
    """Locate the zone-restricted row-group whose joined text matches `predicted_name`."""

    zone_observations = _observations_in_zone(observations, EMPLOYER_NAME_ZONE)
    if not zone_observations:
        return None
    target = predicted_name.strip()
    for row in _group_observation_rows(zone_observations):
        joined = " ".join(observation.text.strip() for observation in row)
        if joined == target:
            return row
    return None


def _tight_sub_row_count(row: list[TextObservation]) -> int:
    """Re-cluster the same row's observations with a small fixed tolerance.

    Purely diagnostic: if the row-group genuinely contains more than one
    real physical print line merged together, a much tighter, non-scaled
    tolerance will usually split it back into multiple sub-clusters, even
    though production's own per-observation-height-scaled tolerance merged
    them into one row. This never changes what the parser decided; it only
    measures a property of its already-decided output.
    """

    centers = sorted((observation.bbox.y0 + observation.bbox.y1) / 2 for observation in row)
    if not centers:
        return 0
    clusters = 1
    current = centers[0]
    for center in centers[1:]:
        if center - current > _TIGHT_SUB_ROW_TOLERANCE_PX:
            clusters += 1
        current = center
    return clusters


def compute_layout_signals(
    predicted_name: str | None, observations: list[TextObservation]
) -> EmployerNameLayoutSignals:
    if predicted_name is None:
        return EmployerNameLayoutSignals(matched=False)

    row = find_employer_name_row_group(predicted_name, observations)
    if row is None:
        return EmployerNameLayoutSignals(matched=False)

    page_height = _page_height(observations)
    y_min = min(observation.bbox.y0 for observation in row)
    y_max = max(observation.bbox.y1 for observation in row)
    vertical_span_px = y_max - y_min
    zone_height_ratio = EMPLOYER_NAME_ZONE[3] - EMPLOYER_NAME_ZONE[2]

    centers = sorted((observation.bbox.y0 + observation.bbox.y1) / 2 for observation in row)
    gaps = [later - earlier for earlier, later in zip(centers, centers[1:])]
    max_gap = max(gaps) if gaps else 0.0

    return EmployerNameLayoutSignals(
        matched=True,
        observation_count=len(row),
        y_min=y_min,
        y_max=y_max,
        vertical_span_px=vertical_span_px,
        vertical_span_ratio=vertical_span_px / page_height if page_height else None,
        zone_span_ratio=(vertical_span_px / page_height) / zone_height_ratio if page_height else None,
        max_center_y_gap_px=max_gap,
        max_center_y_gap_ratio=max_gap / page_height if page_height else None,
        tight_sub_row_count=_tight_sub_row_count(row),
    )
