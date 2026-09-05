from decimal import Decimal

import pytest

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.extraction.pipeline_b.errors import SchemaValidationError
from w2_pipeline.extraction.pipeline_b.mapping import build_w2_document
from w2_pipeline.ingestion.models import SourceDocumentType

_MINIMAL_PARSED: dict = {
    "employee": {"first_name": "Ada", "last_name": "Lovelace"},
    "employer": {"name": "Acme"},
    "federal_wages_and_taxes": {"box_1_wages_tips_other_compensation": "1234.56"},
    "box_12_entries": [{"code": "D", "amount": "500.00"}],
    "box_13": {"retirement_plan": True},
    "box_14_entries": [{"label": "Union dues", "amount": "12.00"}],
    "tipped_occupation_codes": [],
    "state_local_entries": [],
}


def test_build_w2_document_produces_valid_canonical_document() -> None:
    document = build_w2_document(
        _MINIMAL_PARSED,
        document_id="doc-1",
        source_filename="w2.png",
        source_type=SourceDocumentType.PNG,
    )

    assert isinstance(document, W2Document)
    assert document.employee.first_name == "Ada"
    assert document.employee.last_name == "Lovelace"
    assert document.employer.name == "Acme"
    assert document.federal_wages_and_taxes.box_1_wages_tips_other_compensation == Decimal(
        "1234.56"
    )
    assert document.box_12_entries[0].code == "D"
    assert document.box_13.retirement_plan is True
    assert document.box_13.statutory_employee is False
    assert document.metadata.document_id == "doc-1"
    assert document.metadata.source_filename == "w2.png"
    assert document.metadata.tax_year == 2026
    assert document.metadata.schema_version == 2026


def test_build_w2_document_fills_metadata_not_model_supplied() -> None:
    document = build_w2_document(
        {**_MINIMAL_PARSED, "metadata": {"document_id": "should-be-ignored"}},
        document_id="doc-2",
        source_filename="w2.pdf",
        source_type=SourceDocumentType.PDF,
    )

    # metadata isn't read from parsed output at all: an extra "metadata" key
    # in the payload doesn't affect the pipeline-constructed metadata.
    assert document.metadata.document_id == "doc-2"
    assert document.metadata.source_file_type.value == "pdf"


def test_build_w2_document_defaults_missing_address_to_empty() -> None:
    document = build_w2_document(
        {"employee": {"first_name": "Ada"}, "employer": {}},
        document_id="doc-3",
        source_filename=None,
        source_type=SourceDocumentType.JPEG,
    )

    assert document.employee.address.city is None
    assert document.employer.address.city is None


def test_build_w2_document_handles_entirely_empty_payload() -> None:
    document = build_w2_document(
        {},
        document_id="doc-4",
        source_filename=None,
        source_type=SourceDocumentType.PNG,
    )

    assert document.employee.first_name is None
    assert document.box_13.retirement_plan is False
    assert document.box_12_entries == []


def test_build_w2_document_preserves_unicode_names() -> None:
    document = build_w2_document(
        {"employee": {"first_name": "José", "last_name": "Muñoz"}},
        document_id="doc-5",
        source_filename=None,
        source_type=SourceDocumentType.PNG,
    )

    assert document.employee.first_name == "José"
    assert document.employee.last_name == "Muñoz"


def test_build_w2_document_null_middle_initial_stays_null() -> None:
    document = build_w2_document(
        {"employee": {"first_name": "Ada", "middle_initial": None}},
        document_id="doc-6",
        source_filename=None,
        source_type=SourceDocumentType.PNG,
    )

    assert document.employee.middle_initial is None


def test_build_w2_document_rejects_invalid_box12_code_length() -> None:
    with pytest.raises(SchemaValidationError):
        build_w2_document(
            {"box_12_entries": [{"code": "TOOLONG", "amount": "1.00"}]},
            document_id="doc-7",
            source_filename=None,
            source_type=SourceDocumentType.PNG,
        )


def test_build_w2_document_rejects_box14_entry_missing_amount_and_value() -> None:
    with pytest.raises(SchemaValidationError):
        build_w2_document(
            {"box_14_entries": [{"label": "Something"}]},
            document_id="doc-8",
            source_filename=None,
            source_type=SourceDocumentType.PNG,
        )


def test_build_w2_document_rejects_extra_unknown_keys() -> None:
    with pytest.raises(SchemaValidationError):
        build_w2_document(
            {"employee": {"first_name": "Ada", "nickname": "Countess"}},
            document_id="doc-9",
            source_filename=None,
            source_type=SourceDocumentType.PNG,
        )


def test_build_w2_document_rejects_non_boolean_box13_value() -> None:
    with pytest.raises(SchemaValidationError):
        build_w2_document(
            {"box_13": {"retirement_plan": "yes"}},
            document_id="doc-10",
            source_filename=None,
            source_type=SourceDocumentType.PNG,
        )


def test_build_w2_document_normalizes_non_prefixed_state_local_keys() -> None:
    document = build_w2_document(
        {
            "state_local_entries": [
                {
                    "state": "NC",
                    "employer_state_id_number": "35-6152316",
                    "state_wages_tips_etc": "114858.00",
                    "state_income_tax": "4339.59",
                    "local_wages_tips_etc": None,
                    "local_income_tax": None,
                    "locality_name": None,
                }
            ]
        },
        document_id="doc-11",
        source_filename=None,
        source_type=SourceDocumentType.PNG,
    )

    entry = document.state_local_entries[0]
    assert entry.box_15_state == "NC"
    assert entry.box_15_employer_state_id_number == "35-6152316"
    assert entry.box_16_state_wages_tips_etc == Decimal("114858.00")
    assert entry.box_17_state_income_tax == Decimal("4339.59")
    assert entry.box_18_local_wages_tips_etc is None


def test_build_w2_document_accepts_already_canonical_state_local_keys() -> None:
    document = build_w2_document(
        {"state_local_entries": [{"box_15_state": "CA"}]},
        document_id="doc-12",
        source_filename=None,
        source_type=SourceDocumentType.PNG,
    )

    assert document.state_local_entries[0].box_15_state == "CA"


def test_build_w2_document_does_not_import_pipeline_a_parser() -> None:
    import w2_pipeline.extraction.pipeline_b.mapping as mapping_module

    with open(mapping_module.__file__, encoding="utf-8") as file_obj:
        contents = file_obj.read()

    for forbidden in ("parser_2026", "tesseract", "paddle", "ObservationSet", "TextObservation"):
        assert forbidden not in contents
