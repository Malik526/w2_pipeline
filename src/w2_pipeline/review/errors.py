"""Explicit errors for the Phase 7 human review workflow."""


class ReviewError(Exception):
    """Base class for review-workflow failures."""


class InvalidFieldPathError(ReviewError):
    """Raised when a correction names a field path that does not exist on
    the canonical `W2Document` contract."""


class CorrectionValidationError(ReviewError):
    """Raised when a correction's new value fails canonical validation."""


class IllegalReviewTransitionError(ReviewError):
    """Raised when a review status transition is not permitted."""


class ReviewRecordNotFoundError(ReviewError):
    """Raised when a repository lookup finds no record for a review ID."""
