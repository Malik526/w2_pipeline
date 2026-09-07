"""Shared production `ExtractionResult` -> `ExtractionSignals` mapping (Phase 8D.4).

This mapping previously existed only as a private helper,
`_signals_for_result` in
`w2_pipeline.evaluation.run_address_evidence_validator_effectiveness`
(Phase 8D.1B). Centralized here so the single-document production runner
(`w2_pipeline.application.run_document`) and evaluation scripts thread
the exact same evidence fields into the validator rather than each
keeping its own copy -- the same real `ExtractionResult` -> full-evidence
`ExtractionSignals` mapping either way, never a partial one (see Phase
8D.2's `--signals-json` fix for what happens when a caller supplies
`route` without the evidence a route-scoped rule requires).
"""

from __future__ import annotations

from w2_pipeline.extraction.models import ExtractionResult
from w2_pipeline.validation.models import ExtractionSignals


def build_extraction_signals(result: ExtractionResult) -> ExtractionSignals:
    """Build full-evidence `ExtractionSignals` for one real `ExtractionResult`.

    Mirrors every evidence field `ExtractionResult` carries (employer-name
    observation count, Box 13 checkbox evidence, address extraction
    evidence, Box 12 amount-without-code) into its `ExtractionSignals`
    primitive counterpart. `pipeline_id`/`route` come from the result
    itself, never a caller-supplied override -- the whole point is that a
    real extraction's own route and evidence travel together.
    """

    checkbox = result.box_13_checkbox_evidence
    employer_address = result.employer_address_evidence
    employee_address = result.employee_address_evidence
    return ExtractionSignals(
        pipeline_id=result.pipeline,
        route=result.route.value,
        employer_name_observation_count=result.employer_name_observation_count,
        checkbox_evidence_detection_method=checkbox.detection_method if checkbox else None,
        checkbox_evidence_fallback_used=checkbox.fallback_used if checkbox else None,
        checkbox_evidence_anchor_found=checkbox.anchor_found if checkbox else None,
        checkbox_evidence_checkbox_found=checkbox.checkbox_found if checkbox else None,
        checkbox_evidence_anchor_distance_px=checkbox.anchor_distance_px if checkbox else None,
        checkbox_evidence_horizontal_alignment_offset_px=(
            checkbox.horizontal_alignment_offset_px if checkbox else None
        ),
        checkbox_evidence_shape_score=checkbox.shape_score if checkbox else None,
        checkbox_evidence_interior_ink_ratio=checkbox.interior_ink_ratio if checkbox else None,
        checkbox_evidence_decision_margin=checkbox.decision_margin if checkbox else None,
        box_12_amount_without_code_found=result.box_12_amount_without_code_found,
        employer_address_evidence_region_observation_count=(
            employer_address.region_observation_count if employer_address else None
        ),
        employer_address_evidence_usable_row_count=(
            employer_address.usable_row_count if employer_address else None
        ),
        employer_address_evidence_parse_complete=(
            employer_address.parse_complete if employer_address else None
        ),
        employee_address_evidence_region_observation_count=(
            employee_address.region_observation_count if employee_address else None
        ),
        employee_address_evidence_usable_row_count=(
            employee_address.usable_row_count if employee_address else None
        ),
        employee_address_evidence_parse_complete=(
            employee_address.parse_complete if employee_address else None
        ),
    )
