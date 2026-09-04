from decimal import Decimal

import pytest
from pydantic import ValidationError

from w2_pipeline.contracts.w2 import FieldStatus, W2Document


def valid_w2_payload() -> dict:
    return {
        "metadata": {
            "document_type": "W-2",
            "tax_year": 2026,
            "schema_version": 2026,
            "document_id": "doc_fake_001",
            "source_filename": "fake-w2.pdf",
            "source_file_type": "pdf",
        },
        "employee": {
            "ssn": "000-00-0000",
            "first_name": "Test",
            "middle_initial": "Q",
            "last_name": "Employee",
            "suffix": "",
            "address": {
                "address_line_1": "100 Example Ave",
                "address_line_2": "",
                "city": "Faketown",
                "state": "NY",
                "postal_code": "00000",
                "country": "US",
            },
        },
        "employer": {
            "ein": "00-0000000",
            "name": "Example Payroll LLC",
            "address": {
                "address_line_1": "200 Payroll Plaza",
                "address_line_2": "Suite 100",
                "city": "Sample City",
                "state": "NJ",
                "postal_code": "11111",
                "country": "US",
            },
            "control_number": "CTRL-FAKE-001",
        },
        "federal_wages_and_taxes": {
            "box_1_wages_tips_other_compensation": "50000.00",
            "box_2_federal_income_tax_withheld": "7500.25",
            "box_3_social_security_wages": "50000.00",
            "box_4_social_security_tax_withheld": "3100.00",
            "box_5_medicare_wages_and_tips": "50000.00",
            "box_6_medicare_tax_withheld": "725.00",
            "box_7_social_security_tips": "100.00",
            "box_8_allocated_tips": "50.00",
            "box_9_verification_code": "",
            "box_10_dependent_care_benefits": "1200.00",
            "box_11_nonqualified_plans": "0.00",
        },
        "box_12_entries": [
            {"code": "D", "amount": "1500.00"},
            {"code": "DD", "amount": "6000.00"},
        ],
        "box_13": {
            "statutory_employee": False,
            "retirement_plan": True,
            "third_party_sick_pay": False,
        },
        "box_14_entries": [
            {"label": "UNION", "amount": "25.00", "value": None},
            {"label": "MEMO", "amount": None, "value": "Informational"},
        ],
        "tipped_occupation_codes": [{"code": "TTOC-000"}],
        "state_local_entries": [
            {
                "box_15_state": "NY",
                "box_15_employer_state_id_number": "NY-0000000",
                "box_16_state_wages_tips_etc": "50000.00",
                "box_17_state_income_tax": "2500.00",
                "box_18_local_wages_tips_etc": "10000.00",
                "box_19_local_income_tax": "300.00",
                "box_20_locality_name": "NYC",
            },
            {
                "box_15_state": "NJ",
                "box_15_employer_state_id_number": "NJ-0000000",
                "box_16_state_wages_tips_etc": "1000.00",
                "box_17_state_income_tax": "40.00",
                "box_18_local_wages_tips_etc": None,
                "box_19_local_income_tax": None,
                "box_20_locality_name": None,
            },
        ],
        "field_observations": [
            {
                "field_path": "employee.suffix",
                "status": "observed_blank",
                "raw_value": "",
                "message": None,
            },
            {
                "field_path": "state_local_entries.1.box_20_locality_name",
                "status": "not_applicable",
                "raw_value": None,
                "message": "No locality reported on the source document.",
            },
        ],
    }


def test_complete_valid_2026_w2_payload_passes() -> None:
    document = W2Document.model_validate(valid_w2_payload())

    assert document.metadata.document_type == "W-2"
    assert document.metadata.tax_year == 2026
    assert document.federal_wages_and_taxes.box_1_wages_tips_other_compensation == Decimal(
        "50000.00"
    )
    assert document.box_12_entries[1].code == "DD"
    assert document.box_13.retirement_plan is True
    assert document.tipped_occupation_codes[0].code == "TTOC-000"
    assert len(document.state_local_entries) == 2


def test_minimal_optional_nullable_payload_passes() -> None:
    payload = {
        "metadata": {
            "document_type": "W-2",
            "tax_year": 2026,
            "schema_version": 2026,
            "document_id": "doc_fake_minimal",
            "source_filename": None,
            "source_file_type": "png",
        },
        "employee": {"address": {}},
        "employer": {"address": {}},
        "federal_wages_and_taxes": {},
        "box_13": {},
        "field_observations": [
            {
                "field_path": "employee.middle_initial",
                "status": FieldStatus.EXTRACTION_FAILED,
                "raw_value": None,
                "message": "Unreadable source field.",
            }
        ],
    }

    document = W2Document.model_validate(payload)

    assert document.employee.ssn is None
    assert document.box_12_entries == []
    assert document.field_observations[0].status == FieldStatus.EXTRACTION_FAILED


def test_employee_middle_initial_and_suffix_are_independent_optional_fields() -> None:
    payload = valid_w2_payload()
    payload["employee"]["first_name"] = "Jordan"
    payload["employee"]["middle_initial"] = None
    payload["employee"]["last_name"] = "Lee"
    payload["employee"]["suffix"] = "Jr"

    document = W2Document.model_validate(payload)

    assert document.employee.first_name == "Jordan"
    assert document.employee.middle_initial is None
    assert document.employee.last_name == "Lee"
    assert document.employee.suffix == "Jr"


@pytest.mark.parametrize(
    "field_name",
    [
        "box_1_wages_tips_other_compensation",
        "box_2_federal_income_tax_withheld",
        "box_10_dependent_care_benefits",
    ],
)
def test_malformed_money_fields_fail_structural_validation(field_name: str) -> None:
    payload = valid_w2_payload()
    payload["federal_wages_and_taxes"][field_name] = "not-money"

    with pytest.raises(ValidationError):
        W2Document.model_validate(payload)


def test_malformed_repeated_fields_fail_structural_validation() -> None:
    payload = valid_w2_payload()
    payload["box_12_entries"] = {"code": "D", "amount": "1500.00"}

    with pytest.raises(ValidationError):
        W2Document.model_validate(payload)


def test_malformed_box_14_entry_without_amount_or_value_fails() -> None:
    payload = valid_w2_payload()
    payload["box_14_entries"] = [{"label": "INFO"}]

    with pytest.raises(ValidationError):
        W2Document.model_validate(payload)


def test_malformed_box_13_boolean_fields_fail_structural_validation() -> None:
    payload = valid_w2_payload()
    payload["box_13"]["retirement_plan"] = "yes"

    with pytest.raises(ValidationError):
        W2Document.model_validate(payload)


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [("tax_year", 2025), ("schema_version", 2025), ("document_type", "1099")],
)
def test_unsupported_metadata_values_fail(field_name: str, bad_value: object) -> None:
    payload = valid_w2_payload()
    payload["metadata"][field_name] = bad_value

    with pytest.raises(ValidationError):
        W2Document.model_validate(payload)


def test_canonical_json_serialization_preserves_contract_shape() -> None:
    document = W2Document.model_validate(valid_w2_payload())

    dumped = document.model_dump()
    json_payload = document.model_dump_json()

    assert dumped["box_12_entries"][0]["amount"] == Decimal("1500.00")
    assert '"box_12_entries":[{"code":"D","amount":"1500.00"}' in json_payload
    assert '"tipped_occupation_codes":[{"code":"TTOC-000"}]' in json_payload
