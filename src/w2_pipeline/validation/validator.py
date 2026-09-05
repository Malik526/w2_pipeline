"""Phase 6 validator: canonical W2Document -> ValidationResult.

Backend-neutral by construction: this module imports only
`w2_pipeline.contracts.w2` and its own sibling modules. It does not import
anything from `w2_pipeline.extraction` (Pipeline A or Pipeline B) or
`w2_pipeline.evaluation` (which carries benchmark ground truth) -- Pipeline
A and Pipeline B call this same function on their own canonical output; the
validator never knows or cares which one produced it.
"""

from __future__ import annotations

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.validation.models import (
    ExtractionSignals,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)
from w2_pipeline.validation.routing import RoutingPolicy, decide_status
from w2_pipeline.validation.rules import ALL_RULE_NAMES, run_all_rules

_NULL_DOCUMENT_CHECKS_RUN = 1


def validate_w2_document(
    document: W2Document | None,
    *,
    signals: ExtractionSignals | None = None,
    policy: RoutingPolicy | None = None,
) -> ValidationResult:
    """Validate one canonical W2Document and decide accepted vs. needs_review.

    `document` is `None` when extraction did not produce a valid canonical
    result at all (e.g. a raised exception, or a payload that failed
    Pydantic validation before it ever became a `W2Document`) -- callers
    should pass `None` rather than fabricate a placeholder document. In
    that case every field-level rule is skipped (there is nothing to
    check) and the result is `needs_review` with a single
    `extraction_output_invalid` issue.
    """

    resolved_signals = signals or ExtractionSignals()

    if document is None:
        issue = ValidationIssue(
            code="extraction_output_invalid",
            severity=ValidationSeverity.ERROR,
            message="Extraction did not produce a valid canonical W2Document.",
        )
        return ValidationResult(
            status=ValidationStatus.NEEDS_REVIEW,
            issues=[issue],
            checks_run=_NULL_DOCUMENT_CHECKS_RUN,
            pipeline_metadata=_pipeline_metadata(resolved_signals),
        )

    issues = run_all_rules(document, resolved_signals)
    status = decide_status(issues, policy)
    return ValidationResult(
        status=status,
        issues=issues,
        checks_run=len(ALL_RULE_NAMES),
        pipeline_metadata=_pipeline_metadata(resolved_signals),
    )


def _pipeline_metadata(signals: ExtractionSignals) -> dict[str, str] | None:
    metadata = {
        key: value
        for key, value in (
            ("pipeline_id", signals.pipeline_id),
            ("route", signals.route),
            ("document_condition", signals.document_condition),
        )
        if value is not None
    }
    return metadata or None
