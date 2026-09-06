"""Phase 8C.4: evaluation-side OCR-confidence provenance for evaluated fields.

This is deliberately evaluation-side, read-only, and best-effort: it does
NOT change how `parser_2026.py` decides a field's value, and no parser or
validator code depends on it. `TextObservation.ocr_confidence` (populated
by both OCR adapters) already carries the real per-observation confidence;
this module's only job is to work out, after the fact, which observation(s)
plausibly produced a given field's already-decided value, so a caller can
look at the confidence of the text that became that value.

## Why this lives here, not in the parser

Threading real-time provenance through every helper in `parser_2026.py`
(`_value_after_label`, `_first_row_text_in_zone`, `_first_regex_text_in_zone`,
the federal-box line parser, ...) would touch a large surface of a
production parser that Phase 8C.2 declared frozen, for a purely
measurement-oriented question. Instead, this module re-derives provenance
from the *already-produced* `W2Document` plus the *same* `list[TextObservation]`
the parser saw, by searching for a contiguous run of observations (in the
parser's own reading order) whose joined text reconstructs the field's
final value exactly. This is deliberately approximate -- see "Limitations"
in `docs/experiments/phase8c4-paddle-native-confidence-analysis.md` -- but
it is safe: it cannot change extraction, and a caller consuming this data
can only ever produce *evidence*, never a routing decision on its own.

## Matching algorithm

For a field's string-normalized value `V`:

1. Observations are sorted the same way `parse_w2_2026_observations` sorts
   them before parsing: `(page, bbox.y0, bbox.x0)`.
2. Every contiguous run of 1..`_MAX_RUN_LENGTH` observations is tried, in
   order, and the run's texts are joined (space-separated for text fields,
   concatenated for money fields, matching how OCR usually renders each).
   The first run whose joined, normalized text exactly equals `V` wins.
3. If no run matches, the field is reported as unmatched (no confidence
   value is fabricated).

Money-field comparison parses both sides as `Decimal` (so `"$28,425.27"` and
`Decimal("28425.27")` compare equal regardless of formatting); text-field
comparison is an exact, case-sensitive string match (extracted names/EIN/SSN
are never reformatted by the parser, so their OCR text should match
verbatim).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.extraction.models import TextObservation
from w2_pipeline.review.errors import InvalidFieldPathError
from w2_pipeline.review.field_paths import get_field

_MAX_RUN_LENGTH = 4

MONEY_FIELD_PATHS: frozenset[str] = frozenset(
    {
        "federal_wages_and_taxes.box_1_wages_tips_other_compensation",
        "federal_wages_and_taxes.box_2_federal_income_tax_withheld",
        "federal_wages_and_taxes.box_3_social_security_wages",
        "federal_wages_and_taxes.box_4_social_security_tax_withheld",
        "federal_wages_and_taxes.box_5_medicare_wages_and_tips",
        "federal_wages_and_taxes.box_6_medicare_tax_withheld",
    }
)

# The fixed field set Phase 8C.4 inspects (Section 6 of the brief).
# box_13.retirement_plan is deliberately excluded: it is produced by the
# separate pixel-based checkbox detector, not OCR text recognition.
CONFIDENCE_ANALYSIS_FIELD_PATHS: tuple[str, ...] = (
    "employee.first_name",
    "employee.middle_initial",
    "employee.last_name",
    "employee.ssn",
    "employer.ein",
    "employer.name",
    *sorted(MONEY_FIELD_PATHS),
)


@dataclass(frozen=True)
class FieldConfidenceMatch:
    """Provenance result for one field on one document."""

    field_path: str
    field_value: str | None
    matched: bool
    contributing_observation_count: int
    confidences: list[float] = field(default_factory=list)


def _normalize_text(text: str) -> str:
    return text.strip()


def _normalize_money_text(text: str) -> str | None:
    stripped = text.strip().lstrip("$").replace(",", "").strip()
    try:
        return str(Decimal(stripped))
    except InvalidOperation:
        return None


def _field_value_as_string(document: W2Document, field_path: str) -> str | None:
    try:
        value = get_field(document, field_path)
    except InvalidFieldPathError:
        return None
    if value is None:
        return None
    return str(value)


def find_field_confidence_match(
    document: W2Document,
    observations: list[TextObservation],
    field_path: str,
) -> FieldConfidenceMatch:
    """Locate the observation(s) that plausibly produced `field_path`'s value."""

    raw_value = _field_value_as_string(document, field_path)
    if raw_value is None:
        return FieldConfidenceMatch(
            field_path=field_path, field_value=None, matched=False, contributing_observation_count=0
        )

    is_money = field_path in MONEY_FIELD_PATHS
    target = _normalize_money_text(raw_value) if is_money else _normalize_text(raw_value)
    if target is None:
        return FieldConfidenceMatch(
            field_path=field_path, field_value=raw_value, matched=False, contributing_observation_count=0
        )

    ordered = sorted(observations, key=lambda observation: (observation.page, observation.bbox.y0, observation.bbox.x0))

    # Two-phase search, smallest window first within each phase: an exact
    # whole-window match is always preferred over a looser token-membership
    # match, so a precisely isolated single observation (e.g. "D" alone)
    # always wins over a coarser one that merely contains the token
    # alongside other text (e.g. "Steven D" containing "D"). Without this
    # ordering, whichever window the outer scan reached first would win
    # arbitrarily, sometimes attributing a neighboring field's confidence
    # too.
    token_fallback: tuple[list[TextObservation], list[float]] | None = None
    for run_length in range(1, _MAX_RUN_LENGTH + 1):
        for start in range(len(ordered) - run_length + 1):
            window = ordered[start : start + run_length]
            if is_money:
                joined = "".join(observation.text.strip() for observation in window)
                normalized_joined = _normalize_money_text(joined)
                if normalized_joined == target:
                    return _matched_result(field_path, raw_value, window)
                continue

            joined = " ".join(observation.text.strip() for observation in window)
            normalized_joined = _normalize_text(joined)
            if normalized_joined == target:
                return _matched_result(field_path, raw_value, window)
            # A short field (first/middle/last name) is sometimes fused by
            # the OCR engine into one larger merged observation alongside a
            # neighboring field, e.g. Paddle reading "Steven D" as a single
            # line for first_name + middle_initial together. Remembered as
            # a fallback only -- confidence is that whole window's, the
            # only signal available since neither engine reports
            # sub-observation confidence -- and used only if no exact
            # whole-window match exists anywhere for this field.
            if token_fallback is None and target in normalized_joined.split(" "):
                token_fallback = (
                    window,
                    [observation.ocr_confidence for observation in window if observation.ocr_confidence is not None],
                )

    if token_fallback is not None:
        window, confidences = token_fallback
        return FieldConfidenceMatch(
            field_path=field_path,
            field_value=raw_value,
            matched=True,
            contributing_observation_count=len(window),
            confidences=confidences,
        )

    return FieldConfidenceMatch(
        field_path=field_path, field_value=raw_value, matched=False, contributing_observation_count=0
    )


def _matched_result(field_path: str, raw_value: str, window: list[TextObservation]) -> FieldConfidenceMatch:
    return FieldConfidenceMatch(
        field_path=field_path,
        field_value=raw_value,
        matched=True,
        contributing_observation_count=len(window),
        confidences=[observation.ocr_confidence for observation in window if observation.ocr_confidence is not None],
    )


_EMPLOYEE_NAME_CLUSTER_FIELDS = ("employee.first_name", "employee.middle_initial", "employee.last_name")
_ROW_BAND_HEIGHT_MULTIPLIER = 1.0
_ROW_BAND_MIN_TOLERANCE = 20.0


def _row_band_observations(
    observations: list[TextObservation], anchor_text: str
) -> list[TextObservation] | None:
    """Restrict a search to observations near one anchor's own text row.

    Exists specifically because a bare single-letter field value (a middle
    initial) can exactly match an unrelated same-shaped token elsewhere on
    the page -- confirmed directly on a real document, where a Box 12 code
    letter "D" sat far above the actual "Steven D" employee-name line and
    would otherwise win an exact single-observation match over the correct
    but merged "Steven D" token-membership fallback. Anchoring to
    `last_name` (the least ambiguous, most distinctive of the three name
    fields) and restricting first/middle-initial search to its row band
    avoids that specific collision. The tolerance is a heuristic, not a
    guarantee -- see the "Known Limitations" section of
    docs/experiments/phase8c4-paddle-native-confidence-analysis.md.
    """

    anchor = next((observation for observation in observations if observation.text.strip() == anchor_text), None)
    if anchor is None:
        return None
    anchor_height = anchor.bbox.y1 - anchor.bbox.y0
    tolerance = max(anchor_height * _ROW_BAND_HEIGHT_MULTIPLIER, _ROW_BAND_MIN_TOLERANCE)
    anchor_center = (anchor.bbox.y0 + anchor.bbox.y1) / 2
    return [
        observation
        for observation in observations
        if abs((observation.bbox.y0 + observation.bbox.y1) / 2 - anchor_center) <= tolerance
    ]


def find_all_field_confidence_matches(
    document: W2Document,
    observations: list[TextObservation],
    field_paths: tuple[str, ...] = CONFIDENCE_ANALYSIS_FIELD_PATHS,
) -> dict[str, FieldConfidenceMatch]:
    name_cluster_observations = observations
    if "employee.last_name" in field_paths:
        last_name_value = _field_value_as_string(document, "employee.last_name")
        if last_name_value is not None:
            band = _row_band_observations(observations, last_name_value)
            if band:
                name_cluster_observations = band

    matches: dict[str, FieldConfidenceMatch] = {}
    for field_path in field_paths:
        source_observations = (
            name_cluster_observations if field_path in _EMPLOYEE_NAME_CLUSTER_FIELDS else observations
        )
        matches[field_path] = find_field_confidence_match(document, source_observations, field_path)
    return matches


def summarize_confidences(confidences: list[float]) -> dict[str, float | int | None]:
    """Min/mean/max/count over a list of confidence values.

    Returns `None` for min/mean/max when the list is empty -- callers must
    never fabricate a value for a field with no measured confidence.
    """

    if not confidences:
        return {"min": None, "mean": None, "max": None, "count": 0}
    return {
        "min": min(confidences),
        "mean": sum(confidences) / len(confidences),
        "max": max(confidences),
        "count": len(confidences),
    }
