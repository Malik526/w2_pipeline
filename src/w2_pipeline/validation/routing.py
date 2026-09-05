"""Deterministic routing policy: issues -> accepted / needs_review.

Kept separate from rule evaluation (`rules.py`) so a firm's throughput
policy can change without touching what counts as an issue. Phase 6 ships
one policy dimension -- whether a warning alone escalates to review -- and
no configuration UI; a future phase may expose this as a firm-level
setting.
"""

from __future__ import annotations

from dataclasses import dataclass

from w2_pipeline.validation.models import ValidationIssue, ValidationSeverity, ValidationStatus


@dataclass(frozen=True)
class RoutingPolicy:
    """Routing policy: any `error` issue always sends a document to review.

    `escalate_warnings`: when `True` ("conservative mode"), a document with
    only `warning`-severity issues (no errors) is also sent to review.
    Defaults to `False` ("high-throughput mode"): warnings are recorded but
    do not block automatic acceptance on their own.
    """

    escalate_warnings: bool = False


DEFAULT_ROUTING_POLICY = RoutingPolicy()


def decide_status(
    issues: list[ValidationIssue],
    policy: RoutingPolicy | None = None,
) -> ValidationStatus:
    """Decide accepted vs. needs_review from a document's issues."""

    policy = policy or DEFAULT_ROUTING_POLICY
    if any(issue.severity == ValidationSeverity.ERROR for issue in issues):
        return ValidationStatus.NEEDS_REVIEW
    if policy.escalate_warnings and any(
        issue.severity == ValidationSeverity.WARNING for issue in issues
    ):
        return ValidationStatus.NEEDS_REVIEW
    return ValidationStatus.ACCEPTED
