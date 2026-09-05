"""Explicit, deterministic review status transitions.

A small state machine rather than free-form status assignment, so an
illegal jump (e.g. `pending` straight to `resolved`, skipping human
correction and revalidation entirely) fails loudly instead of silently
corrupting a record.
"""

from __future__ import annotations

from datetime import datetime, timezone

from w2_pipeline.review.errors import IllegalReviewTransitionError
from w2_pipeline.review.models import ReviewRecord, ReviewStatus

_LEGAL_TRANSITIONS: dict[ReviewStatus, frozenset[ReviewStatus]] = {
    ReviewStatus.PENDING: frozenset({ReviewStatus.IN_REVIEW}),
    ReviewStatus.IN_REVIEW: frozenset({ReviewStatus.IN_REVIEW, ReviewStatus.RESOLVED}),
    ReviewStatus.RESOLVED: frozenset(),
}


def transition_review(record: ReviewRecord, target_status: ReviewStatus) -> ReviewRecord:
    """Return a NEW `ReviewRecord` moved to `target_status`.

    Raises `IllegalReviewTransitionError` for any transition not in
    `_LEGAL_TRANSITIONS`. `resolved` is terminal: this Phase 7 scope has
    no "reopen a resolved review" workflow.
    """

    legal_targets = _LEGAL_TRANSITIONS.get(record.status, frozenset())
    if target_status not in legal_targets:
        raise IllegalReviewTransitionError(
            f"Cannot transition review {record.review_id!r} from "
            f"{record.status.value!r} to {target_status.value!r}."
        )
    return record.model_copy(
        update={"status": target_status, "updated_at": datetime.now(timezone.utc)}
    )
