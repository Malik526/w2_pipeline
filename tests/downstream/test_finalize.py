import pytest
from pydantic import ValidationError

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.downstream.errors import NotAcceptedError
from w2_pipeline.downstream.finalize import finalize_document
from w2_pipeline.downstream.models import FinalizedW2
from w2_pipeline.validation.validator import validate_w2_document


def test_finalize_accepted_document(happy_path_document: W2Document) -> None:
    result = validate_w2_document(happy_path_document)

    finalized = finalize_document(happy_path_document, result)

    assert finalized.document_id == happy_path_document.metadata.document_id
    assert finalized.status == "accepted"
    assert finalized.schema_version == happy_path_document.metadata.schema_version
    assert finalized.tax_year == happy_path_document.metadata.tax_year
    assert finalized.document == happy_path_document


def test_finalize_rejects_needs_review_document(happy_path_document: W2Document) -> None:
    bad_document = happy_path_document.model_copy(
        update={"employee": happy_path_document.employee.model_copy(update={"ssn": None})}
    )
    result = validate_w2_document(bad_document)

    with pytest.raises(NotAcceptedError):
        finalize_document(bad_document, result)


def test_finalized_w2_cannot_be_constructed_with_a_non_accepted_status(
    happy_path_document: W2Document,
) -> None:
    """Phase 8D.1: closes the gap where `finalize_document`'s gate was
    convention-only -- a caller constructing `FinalizedW2` directly
    (bypassing `finalize_document` entirely) could previously set
    `status="needs_review"` (or any other string) and have both
    `export_json`/`export_csv` happily treat it as downstream-ready."""

    with pytest.raises(ValidationError):
        FinalizedW2(
            document_id="bypass-attempt",
            status="needs_review",
            schema_version=happy_path_document.metadata.schema_version,
            tax_year=happy_path_document.metadata.tax_year,
            document=happy_path_document,
        )
