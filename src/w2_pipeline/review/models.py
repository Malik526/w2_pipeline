"""Phase 7 human review workflow contracts.

The original extracted `W2Document` on a `ReviewRecord` is never mutated:
a correction produces a new `corrected_document` snapshot plus an
append-only `Correction` audit entry, never an in-place edit. This module
depends on `w2_pipeline.validation` (unlike the validation package itself,
which must stay extraction/evaluation-agnostic) -- the whole point of the
review workflow is to consume Phase 6's `ValidationResult`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.validation.models import ValidationResult


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReviewModel(BaseModel):
    """Base model for strict review-workflow contracts."""

    model_config = ConfigDict(extra="forbid")


class ReviewStatus(str, Enum):
    """Lifecycle status for one human review record."""

    PENDING = "pending"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"


class Correction(ReviewModel):
    """One audited human correction to a single canonical field path."""

    field_path: str = Field(min_length=1)
    old_value: Any = None
    new_value: Any = None
    reason: str | None = None
    reviewer_id: str | None = None
    corrected_at: datetime = Field(default_factory=_utc_now)


class ReviewRecord(ReviewModel):
    """Durable review record for one document that needed human review.

    `original_document` is immutable for the life of the record.
    `corrections` is append-only. `corrected_document` is `None` until the
    first correction is applied, then always reflects every correction
    applied so far (not just the most recent one). `revalidation_result`
    is `None` until `revalidate()` has been called at least once.
    """

    review_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    status: ReviewStatus = ReviewStatus.PENDING
    original_document: W2Document
    validation_result: ValidationResult
    corrections: list[Correction] = Field(default_factory=list)
    corrected_document: W2Document | None = None
    revalidation_result: ValidationResult | None = None
    pipeline_metadata: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
