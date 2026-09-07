"""Phase 8D.4: `build_extraction_signals` unit tests.

Covers the shared helper extracted from
`w2_pipeline.evaluation.run_address_evidence_validator_effectiveness`'s
former private `_signals_for_result` -- the mapping itself was already
exercised indirectly by that evaluation script and by
`tests/application/test_run_document.py`; these tests pin the mapping
directly against `ExtractionResult`.
"""

from __future__ import annotations

from decimal import Decimal

from w2_pipeline.contracts.w2 import Address, Box13Flags, Employee, Employer, FederalWagesAndTaxes, W2Document, W2Metadata
from w2_pipeline.extraction.models import (
    AcquisitionRoute,
    AddressExtractionEvidence,
    Box13CheckboxEvidence,
    ExtractionResult,
)
from w2_pipeline.extraction.signals import build_extraction_signals


def _document() -> W2Document:
    return W2Document(
        metadata=W2Metadata(
            document_type="W-2", tax_year=2026, schema_version=2026, document_id="doc-1", source_file_type="png"
        ),
        employee=Employee(ssn="242-48-4959", first_name="Steven", last_name="Armstrong", address=Address()),
        employer=Employer(ein="75-5696876", name="Timberline Trading Co.", address=Address()),
        federal_wages_and_taxes=FederalWagesAndTaxes(box_1_wages_tips_other_compensation=Decimal("100.00")),
        box_13=Box13Flags(),
    )


def test_maps_route_and_pipeline_id_from_result() -> None:
    result = ExtractionResult(document=_document(), route=AcquisitionRoute.OCR, observation_count=1)

    signals = build_extraction_signals(result)

    assert signals.pipeline_id == "pipeline_a"
    assert signals.route == "ocr"


def test_none_evidence_maps_to_none_signals_not_fabricated_defaults() -> None:
    result = ExtractionResult(document=_document(), route=AcquisitionRoute.NATIVE_PDF, observation_count=1)

    signals = build_extraction_signals(result)

    assert signals.checkbox_evidence_detection_method is None
    assert signals.employer_address_evidence_region_observation_count is None
    assert signals.employee_address_evidence_parse_complete is None
    assert signals.box_12_amount_without_code_found is False


def test_full_evidence_is_threaded_field_by_field() -> None:
    checkbox = Box13CheckboxEvidence(
        detection_method="anchor_relative",
        fallback_used=False,
        anchor_found=True,
        checkbox_found=True,
        anchor_distance_px=2.5,
        horizontal_alignment_offset_px=0.5,
        shape_score=0.9,
        interior_ink_ratio=0.4,
        decision_margin=3.0,
    )
    employer_address = AddressExtractionEvidence(region_observation_count=4, usable_row_count=2, parse_complete=False)
    employee_address = AddressExtractionEvidence(region_observation_count=3, usable_row_count=3, parse_complete=True)
    result = ExtractionResult(
        document=_document(),
        route=AcquisitionRoute.OCR,
        observation_count=99,
        employer_name_observation_count=1,
        box_13_checkbox_evidence=checkbox,
        box_12_amount_without_code_found=True,
        employer_address_evidence=employer_address,
        employee_address_evidence=employee_address,
    )

    signals = build_extraction_signals(result)

    assert signals.employer_name_observation_count == 1
    assert signals.checkbox_evidence_detection_method == "anchor_relative"
    assert signals.checkbox_evidence_anchor_distance_px == 2.5
    assert signals.checkbox_evidence_decision_margin == 3.0
    assert signals.box_12_amount_without_code_found is True
    assert signals.employer_address_evidence_region_observation_count == 4
    assert signals.employer_address_evidence_parse_complete is False
    assert signals.employee_address_evidence_region_observation_count == 3
    assert signals.employee_address_evidence_parse_complete is True
