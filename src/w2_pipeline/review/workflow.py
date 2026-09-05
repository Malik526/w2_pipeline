"""Phase 7 review workflow: create -> correct -> revalidate -> resolve.

Every function here returns a NEW `ReviewRecord`; none mutates its input.
Revalidation always calls the same backend-neutral Phase 6
`validate_w2_document` this project already ships -- no validation logic
is duplicated here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.review.errors import IllegalReviewTransitionError, ReviewError
from w2_pipeline.review.field_paths import get_field, set_field_value
from w2_pipeline.review.models import Correction, ReviewRecord, ReviewStatus
from w2_pipeline.review.transitions import transition_review
from w2_pipeline.validation.models import ExtractionSignals, ValidationResult, ValidationStatus
from w2_pipeline.validation.routing import RoutingPolicy
from w2_pipeline.validation.validator import validate_w2_document


def start_review(
    document: W2Document,
    validation_result: ValidationResult,
    *,
    document_id: str,
    pipeline_metadata: dict[str, Any] | None = None,
) -> ReviewRecord:
    """Create a new `pending` `ReviewRecord` for a document that needs review.

    Raises `ReviewError` if `validation_result.status` is `accepted` --
    an accepted document never needs a review record at all.
    """

    if validation_result.status != ValidationStatus.NEEDS_REVIEW:
        raise ReviewError(
            "Cannot start a review for a document whose validation status is "
            f"{validation_result.status.value!r}, not 'needs_review'."
        )

    now = datetime.now(timezone.utc)
    return ReviewRecord(
        review_id=str(uuid4()),
        document_id=document_id,
        status=ReviewStatus.PENDING,
        original_document=document,
        validation_result=validation_result,
        pipeline_metadata=pipeline_metadata,
        created_at=now,
        updated_at=now,
    )


def apply_correction(
    record: ReviewRecord,
    *,
    field_path: str,
    new_value: Any,
    reason: str | None = None,
    reviewer_id: str | None = None,
) -> ReviewRecord:
    """Apply one correction on top of the record's latest document snapshot.

    The first correction on a `pending` record transitions it to
    `in_review`. Corrections on an already-`resolved` record are rejected
    (this Phase 7 scope has no reopen workflow -- see
    `transitions.transition_review`). Raises `InvalidFieldPathError`/
    `CorrectionValidationError` (from `field_paths`) for a bad path or an
    invalid new value; neither the record nor the base document is
    modified when that happens.
    """

    if record.status == ReviewStatus.RESOLVED:
        raise IllegalReviewTransitionError(
            f"Review {record.review_id!r} is already resolved; it has no reopen workflow."
        )

    base_document = record.corrected_document or record.original_document
    old_value = get_field(base_document, field_path)
    corrected_document = set_field_value(base_document, field_path, new_value)

    correction = Correction(
        field_path=field_path,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
        reviewer_id=reviewer_id,
    )

    updated_record = record
    if updated_record.status == ReviewStatus.PENDING:
        updated_record = transition_review(updated_record, ReviewStatus.IN_REVIEW)

    return updated_record.model_copy(
        update={
            "corrections": [*updated_record.corrections, correction],
            "corrected_document": corrected_document,
            "updated_at": datetime.now(timezone.utc),
        }
    )


def revalidate(record: ReviewRecord, *, policy: RoutingPolicy | None = None) -> ReviewRecord:
    """Revalidate the record's latest document snapshot.

    Uses a fresh `ExtractionSignals()` (the default `succeeded` outcome,
    no warnings): once a human has reviewed and corrected a document, the
    originating pipeline's extraction-quality signals no longer describe
    the document being checked -- the corrected content is what is being
    judged now, not the original extraction attempt.

    Moves the record to `resolved` when the result is `accepted`;
    otherwise the record's status is left unchanged (still `in_review`),
    matching the brief's "remains in_review / pending resolution" rule.
    """

    document_to_check = record.corrected_document or record.original_document
    result = validate_w2_document(document_to_check, signals=ExtractionSignals(), policy=policy)

    updated_record = record.model_copy(
        update={"revalidation_result": result, "updated_at": datetime.now(timezone.utc)}
    )
    if result.status == ValidationStatus.ACCEPTED:
        updated_record = transition_review(updated_record, ReviewStatus.RESOLVED)
    return updated_record
