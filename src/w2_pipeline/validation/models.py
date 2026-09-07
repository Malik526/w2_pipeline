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
    employer_name_observation_count: int | None = Field(
        default=None,
        ge=0,
        description=(
            "How many OCR observations contributed to employer.name's "
            "value (Phase 8C.8), as computed by "
            "w2_pipeline.extraction.parser_2026.compute_employer_name_observation_count "
            "-- real layout provenance from the extraction/parser path, "
            "never reconstructed inside validation. None when "
            "unavailable (e.g. Pipeline B, or employer.name is None)."
        ),
    )
    checkbox_evidence_detection_method: str | None = Field(
        default=None,
        description=(
            "Phase 8C.12: mirrors "
            "w2_pipeline.extraction.models.Box13CheckboxEvidence.detection_method "
            "('anchor_relative' / 'fixed_zone_fallback' / 'fixed_zone_disabled') "
            "as a plain string, not the extraction-side pydantic type -- this "
            "module stays independent of w2_pipeline.extraction by construction "
            "(see validator.py's module docstring), so every "
            "Box13CheckboxEvidence field is duplicated here as a primitive "
            "rather than imported. None when no checkbox evidence was supplied "
            "at all (see checkbox_evidence_* fields below)."
        ),
    )
    checkbox_evidence_fallback_used: bool | None = None
    checkbox_evidence_anchor_found: bool | None = None
    checkbox_evidence_checkbox_found: bool | None = None
    checkbox_evidence_anchor_distance_px: float | None = None
    checkbox_evidence_horizontal_alignment_offset_px: float | None = None
    checkbox_evidence_shape_score: float | None = None
    checkbox_evidence_interior_ink_ratio: float | None = None
    checkbox_evidence_decision_margin: float | None = None
    # Phase 8D.1B: mirror w2_pipeline.extraction.models.AddressExtractionEvidence
    # as primitives, same reasoning as checkbox_evidence_* above. None
    # when the route never attempted the address zone at all.
    employer_address_evidence_region_observation_count: int | None = None
    employer_address_evidence_usable_row_count: int | None = None
    employer_address_evidence_parse_complete: bool | None = None
    employee_address_evidence_region_observation_count: int | None = None
    employee_address_evidence_usable_row_count: int | None = None
    employee_address_evidence_parse_complete: bool | None = None
    box_12_amount_without_code_found: bool = Field(
        default=False,
        description=(
            "Phase 8D.1B: mirrors "
            "w2_pipeline.extraction.models.ExtractionResult.box_12_amount_without_code_found "
            "-- whether OCR found a real (nonzero) Box 12 amount with no "
            "matching code, evidence of possibly-incomplete Box 12 "
            "extraction rather than a genuine unused-slot placeholder "
            "(a placeholder's amount is always blank or exactly '$0.00', "
            "never a real nonzero value -- confirmed across all 600 real "
            "slots in the external benchmark, see "
            "docs/experiments/phase8d1b-address-safety-and-box12-slot-semantics.md)."
        ),
    )


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
