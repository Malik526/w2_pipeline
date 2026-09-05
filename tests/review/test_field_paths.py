from decimal import Decimal

import pytest

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.review.errors import CorrectionValidationError, InvalidFieldPathError
from w2_pipeline.review.field_paths import get_field, set_field_value


def test_get_field_reads_scalar_value(happy_path_document: W2Document) -> None:
    assert get_field(happy_path_document, "employee.ssn") == happy_path_document.employee.ssn


def test_get_field_reads_indexed_list_value(happy_path_document: W2Document) -> None:
    # Sample 1's generator always produces at least one Box 12 entry.
    assert get_field(happy_path_document, "box_12_entries[0].code") == (
        happy_path_document.box_12_entries[0].code
    )


def test_set_field_value_updates_scalar_and_preserves_original(
    happy_path_document: W2Document,
) -> None:
    updated = set_field_value(happy_path_document, "employee.ssn", "123-45-6789")

    assert updated.employee.ssn == "123-45-6789"
    # Original document is never mutated.
    assert happy_path_document.employee.ssn != "123-45-6789"


def test_set_field_value_updates_indexed_list_entry(happy_path_document: W2Document) -> None:
    original_code = happy_path_document.box_12_entries[0].code
    new_code = "W" if original_code != "W" else "C"

    updated = set_field_value(happy_path_document, "box_12_entries[0].code", new_code)

    assert updated.box_12_entries[0].code == new_code
    assert happy_path_document.box_12_entries[0].code == original_code


def test_set_field_value_coerces_money_string_to_decimal(happy_path_document: W2Document) -> None:
    updated = set_field_value(
        happy_path_document,
        "federal_wages_and_taxes.box_1_wages_tips_other_compensation",
        "1234.56",
    )

    assert updated.federal_wages_and_taxes.box_1_wages_tips_other_compensation == Decimal(
        "1234.56"
    )


def test_get_field_rejects_unknown_top_level_field(happy_path_document: W2Document) -> None:
    with pytest.raises(InvalidFieldPathError):
        get_field(happy_path_document, "not_a_real_field")


def test_get_field_rejects_unknown_nested_field(happy_path_document: W2Document) -> None:
    with pytest.raises(InvalidFieldPathError):
        get_field(happy_path_document, "employee.not_a_real_field")


def test_set_field_value_rejects_unknown_field_path(happy_path_document: W2Document) -> None:
    with pytest.raises(InvalidFieldPathError):
        set_field_value(happy_path_document, "employee.not_a_real_field", "x")


def test_get_field_rejects_out_of_range_list_index(happy_path_document: W2Document) -> None:
    with pytest.raises(InvalidFieldPathError):
        get_field(happy_path_document, "box_12_entries[99].code")


def test_get_field_rejects_malformed_path_syntax(happy_path_document: W2Document) -> None:
    with pytest.raises(InvalidFieldPathError):
        get_field(happy_path_document, "employee..ssn")


def test_get_field_rejects_empty_path(happy_path_document: W2Document) -> None:
    with pytest.raises(InvalidFieldPathError):
        get_field(happy_path_document, "")


def test_set_field_value_rejects_invalid_box12_code_too_long(
    happy_path_document: W2Document,
) -> None:
    with pytest.raises(CorrectionValidationError):
        set_field_value(happy_path_document, "box_12_entries[0].code", "TOOLONG")


def test_set_field_value_rejects_non_boolean_box13_value(happy_path_document: W2Document) -> None:
    with pytest.raises(CorrectionValidationError):
        set_field_value(happy_path_document, "box_13.retirement_plan", "yes")


def test_set_field_value_preserves_unicode(happy_path_document: W2Document) -> None:
    updated = set_field_value(happy_path_document, "employee.first_name", "José")

    assert updated.employee.first_name == "José"


def test_set_field_value_allows_setting_null(happy_path_document: W2Document) -> None:
    updated = set_field_value(happy_path_document, "employee.suffix", None)

    assert updated.employee.suffix is None
