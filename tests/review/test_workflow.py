import pytest

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.review.errors import IllegalReviewTransitionError, ReviewError
from w2_pipeline.review.models import ReviewStatus
from w2_pipeline.review.transitions import transition_review
from w2_pipeline.review.workflow import apply_correction, revalidate, start_review
from w2_pipeline.validation.models import ValidationResult, ValidationStatus


def test_start_review_creates_pending_record(
    missing_ssn_document: W2Document, needs_review_result: ValidationResult
) -> None:
    record = start_review(missing_ssn_document, needs_review_result, document_id="doc-1")

    assert record.status == ReviewStatus.PENDING
    assert record.document_id == "doc-1"
    assert record.original_document == missing_ssn_document
    assert record.validation_result == needs_review_result
    assert record.corrections == []
    assert record.corrected_document is None


def test_start_review_rejects_accepted_result(
    happy_path_document: W2Document, accepted_result: ValidationResult
) -> None:
    with pytest.raises(ReviewError):
        start_review(happy_path_document, accepted_result, document_id="doc-1")


def test_start_review_records_pipeline_metadata(
    missing_ssn_document: W2Document, needs_review_result: ValidationResult
) -> None:
    record = start_review(
        missing_ssn_document,
        needs_review_result,
        document_id="doc-1",
        pipeline_metadata={"pipeline_id": "pipeline_a", "route": "ocr"},
    )

    assert record.pipeline_metadata == {"pipeline_id": "pipeline_a", "route": "ocr"}


def test_apply_correction_transitions_pending_to_in_review(
    missing_ssn_document: W2Document, needs_review_result: ValidationResult
) -> None:
    record = start_review(missing_ssn_document, needs_review_result, document_id="doc-1")

    updated = apply_correction(record, field_path="employee.ssn", new_value="123-45-6789")

    assert updated.status == ReviewStatus.IN_REVIEW
    assert len(updated.corrections) == 1
    correction = updated.corrections[0]
    assert correction.field_path == "employee.ssn"
    assert correction.old_value is None
    assert correction.new_value == "123-45-6789"
    assert updated.corrected_document.employee.ssn == "123-45-6789"


def test_apply_correction_does_not_mutate_original_document(
    missing_ssn_document: W2Document, needs_review_result: ValidationResult
) -> None:
    record = start_review(missing_ssn_document, needs_review_result, document_id="doc-1")

    updated = apply_correction(record, field_path="employee.ssn", new_value="123-45-6789")

    assert updated.original_document.employee.ssn is None
    assert record.original_document.employee.ssn is None


def test_apply_correction_supports_multiple_corrections_in_sequence(
    missing_ssn_document: W2Document, needs_review_result: ValidationResult
) -> None:
    record = start_review(missing_ssn_document, needs_review_result, document_id="doc-1")

    record = apply_correction(record, field_path="employee.ssn", new_value="123-45-6789")
    record = apply_correction(
        record, field_path="employer.name", new_value="Corrected Employer Name"
    )

    assert len(record.corrections) == 2
    assert record.corrected_document.employee.ssn == "123-45-6789"
    assert record.corrected_document.employer.name == "Corrected Employer Name"


def test_apply_correction_records_reason_and_reviewer_id(
    missing_ssn_document: W2Document, needs_review_result: ValidationResult
) -> None:
    record = start_review(missing_ssn_document, needs_review_result, document_id="doc-1")

    updated = apply_correction(
        record,
        field_path="employee.ssn",
        new_value="123-45-6789",
        reason="Confirmed against source document",
        reviewer_id="reviewer-42",
    )

    correction = updated.corrections[0]
    assert correction.reason == "Confirmed against source document"
    assert correction.reviewer_id == "reviewer-42"


def test_apply_correction_rejected_on_resolved_record(
    missing_ssn_document: W2Document, needs_review_result: ValidationResult
) -> None:
    record = start_review(missing_ssn_document, needs_review_result, document_id="doc-1")
    record = apply_correction(record, field_path="employee.ssn", new_value="123-45-6789")
    record = revalidate(record)
    assert record.status == ReviewStatus.RESOLVED

    with pytest.raises(IllegalReviewTransitionError):
        apply_correction(record, field_path="employee.suffix", new_value="Jr")


def test_revalidate_moves_to_resolved_when_correction_fixes_the_issue(
    missing_ssn_document: W2Document, needs_review_result: ValidationResult
) -> None:
    record = start_review(missing_ssn_document, needs_review_result, document_id="doc-1")
    record = apply_correction(record, field_path="employee.ssn", new_value="123-45-6789")

    updated = revalidate(record)

    assert updated.status == ReviewStatus.RESOLVED
    assert updated.revalidation_result.status == ValidationStatus.ACCEPTED


def test_revalidate_stays_in_review_when_still_invalid(
    missing_ssn_document: W2Document, needs_review_result: ValidationResult
) -> None:
    record = start_review(missing_ssn_document, needs_review_result, document_id="doc-1")
    # Correct an unrelated field; the SSN is still missing.
    record = apply_correction(record, field_path="employee.suffix", new_value="Jr")

    updated = revalidate(record)

    assert updated.status == ReviewStatus.IN_REVIEW
    assert updated.revalidation_result.status == ValidationStatus.NEEDS_REVIEW


def test_revalidate_without_any_correction_uses_original_document(
    missing_ssn_document: W2Document, needs_review_result: ValidationResult
) -> None:
    record = start_review(missing_ssn_document, needs_review_result, document_id="doc-1")

    updated = revalidate(record)

    assert updated.revalidation_result.status == ValidationStatus.NEEDS_REVIEW
    assert updated.status == ReviewStatus.PENDING


def test_revalidate_preserves_pre_review_validation_result(
    missing_ssn_document: W2Document, needs_review_result: ValidationResult
) -> None:
    record = start_review(missing_ssn_document, needs_review_result, document_id="doc-1")
    record = apply_correction(record, field_path="employee.ssn", new_value="123-45-6789")

    updated = revalidate(record)

    assert updated.validation_result == needs_review_result
    assert updated.revalidation_result != needs_review_result


def test_full_flow_b_end_to_end(
    missing_ssn_document: W2Document, needs_review_result: ValidationResult
) -> None:
    """The brief's Flow B: corrupted -> review -> correct -> revalidate -> resolved."""

    record = start_review(missing_ssn_document, needs_review_result, document_id="doc-1")
    assert record.status == ReviewStatus.PENDING

    record = apply_correction(
        record, field_path="employee.ssn", new_value="123-45-6789", reason="verified"
    )
    assert record.status == ReviewStatus.IN_REVIEW

    record = revalidate(record)
    assert record.status == ReviewStatus.RESOLVED
    assert record.revalidation_result.status == ValidationStatus.ACCEPTED

    # Only the corrected field changed; everything else matches the original.
    original_dump = record.original_document.model_dump(mode="python")
    corrected_dump = record.corrected_document.model_dump(mode="python")
    original_dump["employee"]["ssn"] = corrected_dump["employee"]["ssn"]
    assert original_dump == corrected_dump


def test_transition_review_still_directly_usable(
    missing_ssn_document: W2Document, needs_review_result: ValidationResult
) -> None:
    record = start_review(missing_ssn_document, needs_review_result, document_id="doc-1")

    updated = transition_review(record, ReviewStatus.IN_REVIEW)

    assert updated.status == ReviewStatus.IN_REVIEW
