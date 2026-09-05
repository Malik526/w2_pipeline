"""Gate a canonical W2Document into a downstream-ready FinalizedW2.

This is the only place a `FinalizedW2` is constructed, and the only
enforcement point for "non-accepted documents never reach downstream
output": every output adapter (`json_output.py`, `csv_output.py`) takes a
`FinalizedW2`, never a raw `W2Document` + `ValidationResult` pair, so an
adapter cannot accidentally skip the gate.
"""

from __future__ import annotations

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.downstream.errors import NotAcceptedError
from w2_pipeline.downstream.models import FinalizedW2
from w2_pipeline.validation.models import ValidationResult, ValidationStatus


def finalize_document(document: W2Document, validation_result: ValidationResult) -> FinalizedW2:
    """Return a `FinalizedW2` for an accepted document.

    Raises `NotAcceptedError` if `validation_result.status` is not
    `accepted` -- a `needs_review` document must complete the Phase 7
    review workflow (`w2_pipeline.review`) and reach an `accepted`
    revalidation before it can be finalized.
    """

    if validation_result.status != ValidationStatus.ACCEPTED:
        raise NotAcceptedError(
            f"Cannot finalize a document with validation status "
            f"{validation_result.status.value!r}; only 'accepted' documents "
            "may become downstream output."
        )

    return FinalizedW2(
        document_id=document.metadata.document_id,
        status=validation_result.status.value,
        schema_version=document.metadata.schema_version,
        tax_year=document.metadata.tax_year,
        document=document,
    )
