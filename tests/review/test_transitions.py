import pytest

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.review.errors import IllegalReviewTransitionError
from w2_pipeline.review.models import ReviewRecord, ReviewStatus
from w2_pipeline.review.transitions import transition_review
from w2_pipeline.validation.models import ValidationResult


def _record(status: ReviewStatus, document: W2Document, result: ValidationResult) -> ReviewRecord:
    return ReviewRecord(
        review_id="r1",
        document_id="doc-1",
        status=status,
        original_document=document,
        validation_result=result,
    )


def test_pending_to_in_review_is_legal(
    happy_path_document: W2Document, needs_review_result: ValidationResult
) -> None:
    record = _record(ReviewStatus.PENDING, happy_path_document, needs_review_result)

    updated = transition_review(record, ReviewStatus.IN_REVIEW)

    assert updated.status == ReviewStatus.IN_REVIEW


def test_in_review_to_resolved_is_legal(
    happy_path_document: W2Document, needs_review_result: ValidationResult
) -> None:
    record = _record(ReviewStatus.IN_REVIEW, happy_path_document, needs_review_result)

    updated = transition_review(record, ReviewStatus.RESOLVED)

    assert updated.status == ReviewStatus.RESOLVED


def test_in_review_to_in_review_is_legal_idempotent(
    happy_path_document: W2Document, needs_review_result: ValidationResult
) -> None:
    record = _record(ReviewStatus.IN_REVIEW, happy_path_document, needs_review_result)

    updated = transition_review(record, ReviewStatus.IN_REVIEW)

    assert updated.status == ReviewStatus.IN_REVIEW


def test_pending_to_resolved_is_illegal(
    happy_path_document: W2Document, needs_review_result: ValidationResult
) -> None:
    record = _record(ReviewStatus.PENDING, happy_path_document, needs_review_result)

    with pytest.raises(IllegalReviewTransitionError):
        transition_review(record, ReviewStatus.RESOLVED)


def test_resolved_to_anything_is_illegal(
    happy_path_document: W2Document, needs_review_result: ValidationResult
) -> None:
    record = _record(ReviewStatus.RESOLVED, happy_path_document, needs_review_result)

    with pytest.raises(IllegalReviewTransitionError):
        transition_review(record, ReviewStatus.IN_REVIEW)
    with pytest.raises(IllegalReviewTransitionError):
        transition_review(record, ReviewStatus.PENDING)


def test_transition_does_not_mutate_original_record(
    happy_path_document: W2Document, needs_review_result: ValidationResult
) -> None:
    record = _record(ReviewStatus.PENDING, happy_path_document, needs_review_result)

    transition_review(record, ReviewStatus.IN_REVIEW)

    assert record.status == ReviewStatus.PENDING
