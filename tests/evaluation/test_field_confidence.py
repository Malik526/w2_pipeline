from decimal import Decimal

import pytest

from w2_pipeline.contracts.w2 import (
    Address,
    Box13Flags,
    Employee,
    Employer,
    FederalWagesAndTaxes,
    W2Document,
    W2Metadata,
)
from w2_pipeline.extraction.models import BoundingBox, ObservationSource, TextObservation
from w2_pipeline.evaluation.field_confidence import (
    find_all_field_confidence_matches,
    find_field_confidence_match,
    summarize_confidences,
)


def _obs(text: str, x0: float, y0: float, *, confidence: float | None, width: float = 80, height: float = 20) -> TextObservation:
    return TextObservation(
        text=text,
        page=1,
        bbox=BoundingBox(x0=x0, y0=y0, x1=x0 + width, y1=y0 + height),
        source=ObservationSource.OCR,
        ocr_confidence=confidence,
    )


def _document(**overrides: object) -> W2Document:
    defaults: dict[str, object] = dict(
        metadata=W2Metadata(
            document_type="W-2",
            tax_year=2026,
            schema_version=2026,
            document_id="doc-1",
            source_file_type="png",
        ),
        employee=Employee(
            ssn="242-48-4959",
            first_name="Steven",
            middle_initial="D",
            last_name="Armstrong",
            address=Address(),
        ),
        employer=Employer(ein="75-5696876", name="Timberline Trading Co.", address=Address()),
        federal_wages_and_taxes=FederalWagesAndTaxes(
            box_1_wages_tips_other_compensation=Decimal("114858.00"),
        ),
        box_13=Box13Flags(),
    )
    defaults.update(overrides)
    return W2Document(**defaults)


def test_single_merged_observation_match_for_ssn() -> None:
    document = _document()
    observations = [_obs("242-48-4959", 100, 100, confidence=0.97)]

    match = find_field_confidence_match(document, observations, "employee.ssn")

    assert match.matched
    assert match.contributing_observation_count == 1
    assert match.confidences == [0.97]


def test_fragmented_multi_observation_match_for_employer_name() -> None:
    document = _document()
    observations = [
        _obs("Timberline", 100, 200, confidence=0.9),
        _obs("Trading", 190, 200, confidence=0.8),
        _obs("Co.", 270, 200, confidence=0.95),
    ]

    match = find_field_confidence_match(document, observations, "employer.name")

    assert match.matched
    assert match.contributing_observation_count == 3
    assert sorted(match.confidences) == sorted([0.9, 0.8, 0.95])


def test_isolates_last_name_from_a_shared_multi_word_row() -> None:
    """Regression guard for the exact real-world shape: first/middle/last
    share one visual row but are three separate observations, and each
    field's match must isolate only its own token(s), not the whole row."""

    document = _document()
    observations = [
        _obs("Steven", 100, 300, confidence=0.5),
        _obs("D", 200, 300, confidence=0.6),
        _obs("Armstrong", 230, 300, confidence=0.7),
    ]

    first = find_field_confidence_match(document, observations, "employee.first_name")
    middle = find_field_confidence_match(document, observations, "employee.middle_initial")
    last = find_field_confidence_match(document, observations, "employee.last_name")

    assert first.confidences == [0.5]
    assert middle.confidences == [0.6]
    assert last.confidences == [0.7]


def test_first_name_and_middle_initial_merged_into_one_observation() -> None:
    """Real-world shape confirmed via direct PaddleOCR inspection: first
    name and middle initial sometimes fuse into one observation (e.g.
    "Steven D"), separate from last_name. An exact single-observation match
    ("D" alone) must always win over the coarser fused-window match, even
    though the fused window also contains "D" as a token."""

    document = _document()
    observations = [
        _obs("Steven D", 100, 300, confidence=0.4),
        _obs("Armstrong", 250, 300, confidence=0.9),
    ]

    first = find_field_confidence_match(document, observations, "employee.first_name")
    middle = find_field_confidence_match(document, observations, "employee.middle_initial")
    last = find_field_confidence_match(document, observations, "employee.last_name")

    assert first.confidences == [0.4]
    assert first.contributing_observation_count == 1
    # "D" has no standalone observation, so the fallback correctly reports
    # the fused window's confidence -- not fabricated, but coarser.
    assert middle.confidences == [0.4]
    assert last.confidences == [0.9]


def test_exact_isolated_match_preferred_over_coarser_token_membership_match() -> None:
    """When both an exact single-observation match AND a coarser
    token-membership match exist for the same field, the exact match must
    win regardless of which one the scan would reach first."""

    document = _document()
    observations = [
        _obs("Steven D", 100, 300, confidence=0.2),  # coarser fallback candidate
        _obs("D", 300, 300, confidence=0.9),  # exact isolated match
    ]

    middle = find_field_confidence_match(document, observations, "employee.middle_initial")

    assert middle.confidences == [0.9]
    assert middle.contributing_observation_count == 1


def test_middle_initial_does_not_collide_with_unrelated_distant_single_letter() -> None:
    """Reproduces a real collision found on `symage_900001-...-rotated.png`:
    a Box 12 code letter "D" sitting far above the actual employee-name row
    is an exact single-observation match for `employee.middle_initial`
    ("D"), but `find_all_field_confidence_matches` must prefer the correct,
    row-anchored "Steven D" fused observation instead. Only
    `find_all_field_confidence_matches` (not the single-field function in
    isolation) applies this anchoring."""

    document = _document()
    observations = [
        _obs("D", 1994, 824, confidence=0.05, width=20, height=36),  # unrelated Box 12 code letter, far above
        _obs("Steven D", 189, 882, confidence=0.9, width=120, height=42),
        _obs("Armstrong", 756, 865, confidence=0.95, width=140, height=41),
    ]

    matches = find_all_field_confidence_matches(document, observations)

    assert matches["employee.middle_initial"].confidences == [0.9]
    assert matches["employee.first_name"].confidences == [0.9]
    assert matches["employee.last_name"].confidences == [0.95]


def test_money_field_matches_despite_dollar_sign_and_commas() -> None:
    document = _document()
    observations = [_obs("$114,858.00", 100, 400, confidence=0.88)]

    match = find_field_confidence_match(document, observations, "federal_wages_and_taxes.box_1_wages_tips_other_compensation")

    assert match.matched
    assert match.confidences == [0.88]


def test_unmatched_field_reports_no_fabricated_confidence() -> None:
    document = _document()
    observations = [_obs("nothing relevant here", 100, 100, confidence=0.99)]

    match = find_field_confidence_match(document, observations, "employer.name")

    assert not match.matched
    assert match.confidences == []
    assert match.field_value == "Timberline Trading Co."


def test_none_valued_field_is_reported_as_unmatched_without_a_value() -> None:
    document = _document(employee=Employee(ssn="242-48-4959", address=Address()))

    match = find_field_confidence_match(document, [], "employee.first_name")

    assert not match.matched
    assert match.field_value is None


def test_missing_observation_confidence_excluded_from_confidences_but_still_counted() -> None:
    document = _document()
    observations = [_obs("242-48-4959", 100, 100, confidence=None)]

    match = find_field_confidence_match(document, observations, "employee.ssn")

    assert match.matched
    assert match.contributing_observation_count == 1
    assert match.confidences == []


def test_summarize_confidences_computes_min_mean_max_count() -> None:
    summary = summarize_confidences([0.5, 0.7, 0.9])

    assert summary == {"min": 0.5, "mean": pytest.approx(0.7), "max": 0.9, "count": 3}


def test_summarize_confidences_empty_list_returns_none_not_zero() -> None:
    summary = summarize_confidences([])

    assert summary == {"min": None, "mean": None, "max": None, "count": 0}


def test_find_all_field_confidence_matches_covers_the_fixed_field_set() -> None:
    document = _document()
    observations = [
        _obs("242-48-4959", 0, 0, confidence=0.9),
        _obs("Steven", 0, 50, confidence=0.9),
        _obs("D", 100, 50, confidence=0.9),
        _obs("Armstrong", 130, 50, confidence=0.9),
        _obs("75-5696876", 0, 100, confidence=0.9),
        _obs("Timberline Trading Co.", 0, 150, confidence=0.9),
        _obs("$114,858.00", 0, 200, confidence=0.9),
    ]

    matches = find_all_field_confidence_matches(document, observations)

    assert matches["employee.ssn"].matched
    assert matches["employer.name"].matched
    assert matches["federal_wages_and_taxes.box_1_wages_tips_other_compensation"].matched
    # box_2 has no value on this document and no matching observation.
    assert not matches["federal_wages_and_taxes.box_2_federal_income_tax_withheld"].matched
