"""Phase 6 validation contracts.

These types are deliberately independent of the Phase 3 evaluation
contracts (`w2_pipeline.evaluation.models`). The evaluator compares a
prediction against known ground truth to measure accuracy; the validator
never sees ground truth and instead judges whether an already-produced
`W2Document` looks safe enough to continue automatically. See
`docs/contracts/validation-and-routing.md` for the full boundary writeup.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ValidationModel(BaseModel):
    """Base model for strict validation contracts."""

    model_config = ConfigDict(extra="forbid")


class ValidationSeverity(str, Enum):
    """Severity of one validation issue."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ValidationStatus(str, Enum):
    """Terminal routing decision for one validated document."""

    ACCEPTED = "accepted"
    NEEDS_REVIEW = "needs_review"


class ExtractionOutcome(str, Enum):
    """Coarse-grained extraction result, independent of pipeline identity."""

    SUCCEEDED = "succeeded"
    EXTRACTION_FAILED = "extraction_failed"
    INVALID_CANONICAL_RESULT = "invalid_canonical_result"


class ExtractionSignals(ValidationModel):
    """Optional extraction-quality metadata a caller may attach.

    This deliberately does not carry a unified confidence score: Pipeline A
    (deterministic OCR/parsing) and Pipeline B (a generative VLM) have no
    comparable notion of per-field confidence, and manufacturing one would
    misrepresent both. `warnings` carries whatever free-text warnings the
    originating pipeline already produced (e.g. `ExtractionWarning.message`
    values), reported as-is rather than scored.
    """

    pipeline_id: str | None = None
    outcome: ExtractionOutcome = ExtractionOutcome.SUCCEEDED
    route: str | None = None
    document_condition: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ValidationIssue(ValidationModel):
    """One explainable reason a document was or was not routed for review."""

    code: str = Field(min_length=1)
    field_path: str | None = None
    severity: ValidationSeverity
    message: str = Field(min_length=1)
    observed_value: Any = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationResult(ValidationModel):
    """Outcome of validating one canonical W2Document."""

    status: ValidationStatus
    issues: list[ValidationIssue] = Field(default_factory=list)
    checks_run: int = Field(ge=0)
    pipeline_metadata: dict[str, Any] | None = None
