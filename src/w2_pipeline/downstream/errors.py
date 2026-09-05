"""Explicit errors for downstream output finalization."""


class DownstreamError(Exception):
    """Base class for downstream-output failures."""


class NotAcceptedError(DownstreamError):
    """Raised when finalization is attempted on a non-accepted document.

    Only an `accepted` `ValidationResult` may produce a downstream
    artifact -- a `needs_review` document must go through the Phase 7
    review workflow and reach an `accepted` revalidation first.
    """
