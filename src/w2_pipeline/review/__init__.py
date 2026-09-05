"""Phase 7 human review workflow: needs_review -> correction -> revalidation.

See `docs/contracts/review-and-downstream-output.md` for the full
architecture and lifecycle contract.
"""

from w2_pipeline.review.errors import (
    CorrectionValidationError,
    IllegalReviewTransitionError,
    InvalidFieldPathError,
    ReviewError,
    ReviewRecordNotFoundError,
)
from w2_pipeline.review.field_paths import get_field, set_field_value
from w2_pipeline.review.models import Correction, ReviewRecord, ReviewStatus
from w2_pipeline.review.repository import FileReviewRepository, ReviewRepository
from w2_pipeline.review.transitions import transition_review
from w2_pipeline.review.workflow import apply_correction, revalidate, start_review

__all__ = [
    "Correction",
    "CorrectionValidationError",
    "FileReviewRepository",
    "IllegalReviewTransitionError",
    "InvalidFieldPathError",
    "ReviewError",
    "ReviewRecord",
    "ReviewRecordNotFoundError",
    "ReviewRepository",
    "ReviewStatus",
    "apply_correction",
    "get_field",
    "revalidate",
    "set_field_value",
    "start_review",
    "transition_review",
]
