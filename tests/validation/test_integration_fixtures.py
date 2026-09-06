"""Phase 6 small integration verification (brief item 12).

Uses only existing, already-committed fixture infrastructure (the Phase 3
deterministic synthetic generator) rather than running any OCR/VLM
inference to produce new artifacts, per the Phase 6 brief. A "known-good
Pipeline B canonical output" fixture was not readily available without
re-running VLM inference (Phase 5A's smoke-test JSON summaries record
field-level comparisons, not the full predicted document), so this uses
the same synthetic-generator fixture for both "known good" cases --
acceptable because the validator is backend-neutral by construction
(`test_isolation.py`, `test_validator.py::test_validate_w2_document_backend_neutral_for_pipeline_a_and_b_signals`):
it cannot behave differently based on which pipeline produced the document.
"""

from __future__ import annotations

from decimal import Decimal

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.synthetic import SyntheticGenerationConfig, generate_synthetic_w2_documents
from w2_pipeline.validation.models import ExtractionSignals, ValidationStatus
from w2_pipeline.validation.validator import validate_w2_document


def test_known_good_document_from_pipeline_a_style_signals_is_accepted(
    happy_path_document: W2Document,
) -> None:
    result = validate_w2_document(
        happy_path_document, signals=ExtractionSignals(pipeline_id="pipeline_a", route="native_pdf")
    )

    assert result.status == ValidationStatus.ACCEPTED


def test_known_good_document_from_pipeline_b_style_signals_is_accepted(
    happy_path_document: W2Document,
) -> None:
    result = validate_w2_document(
        happy_path_document, signals=ExtractionSignals(pipeline_id="pipeline_b", route="vlm")
    )

    assert result.status == ValidationStatus.ACCEPTED


def test_intentionally_corrupted_document_needs_review(happy_path_document: W2Document) -> None:
    corrupted = happy_path_document.model_copy(
        update={
            "employee": happy_path_document.employee.model_copy(update={"ssn": "garbage"}),
            "employer": happy_path_document.employer.model_copy(update={"ein": "also-garbage"}),
            "federal_wages_and_taxes": happy_path_document.federal_wages_and_taxes.model_copy(
                update={"box_1_wages_tips_other_compensation": Decimal("-1.00")}
            ),
        }
    )

    result = validate_w2_document(corrupted)

    assert result.status == ValidationStatus.NEEDS_REVIEW
    codes = {issue.code for issue in result.issues}
    assert {"invalid_ssn_format", "invalid_ein_format", "invalid_money_value"} <= codes


def test_document_missing_critical_field_needs_review(happy_path_document: W2Document) -> None:
    missing_critical = happy_path_document.model_copy(
        update={"employee": happy_path_document.employee.model_copy(update={"ssn": None, "last_name": None})}
    )

    result = validate_w2_document(missing_critical)

    assert result.status == ValidationStatus.NEEDS_REVIEW
    fields_flagged = {issue.field_path for issue in result.issues}
    assert "employee.ssn" in fields_flagged
    assert "employee.last_name" in fields_flagged


def test_all_generator_samples_across_seeds_are_at_least_structurally_checkable() -> None:
    # Not an accuracy claim -- just confirms the validator runs cleanly
    # (no exceptions, a real status) over every shape the generator
    # produces, across its documented optional-field variation.
    documents = generate_synthetic_w2_documents(SyntheticGenerationConfig(sample_count=12))

    for document in documents:
        result = validate_w2_document(document)
        assert result.status in {ValidationStatus.ACCEPTED, ValidationStatus.NEEDS_REVIEW}
        assert result.checks_run == 13
