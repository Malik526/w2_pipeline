"""Phase 6 validation and human-review routing.

Answers "does this already-extracted canonical W2Document look safe enough
to continue automatically?" -- distinct from extraction ("what values did
we read?") and benchmark evaluation ("was extraction correct compared with
known ground truth?"). See `docs/contracts/validation-and-routing.md`.
"""

from w2_pipeline.validation.models import (
    ExtractionOutcome,
    ExtractionSignals,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)
from w2_pipeline.validation.routing import DEFAULT_ROUTING_POLICY, RoutingPolicy, decide_status
from w2_pipeline.validation.validator import validate_w2_document

__all__ = [
    "DEFAULT_ROUTING_POLICY",
    "ExtractionOutcome",
    "ExtractionSignals",
    "RoutingPolicy",
    "ValidationIssue",
    "ValidationResult",
    "ValidationSeverity",
    "ValidationStatus",
    "decide_status",
    "validate_w2_document",
]
