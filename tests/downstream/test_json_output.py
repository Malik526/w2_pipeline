import json
from decimal import Decimal
from pathlib import Path

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.downstream.finalize import finalize_document
from w2_pipeline.downstream.json_output import export_json
from w2_pipeline.validation.validator import validate_w2_document


def test_export_json_returns_valid_json(happy_path_document: W2Document) -> None:
    finalized = finalize_document(happy_path_document, validate_w2_document(happy_path_document))

    text = export_json(finalized)

    payload = json.loads(text)
    assert payload["document_id"] == happy_path_document.metadata.document_id
    assert payload["status"] == "accepted"
    assert payload["document"]["employee"]["ssn"] == happy_path_document.employee.ssn


def test_export_json_writes_to_path(happy_path_document: W2Document, tmp_path: Path) -> None:
    finalized = finalize_document(happy_path_document, validate_w2_document(happy_path_document))
    output_path = tmp_path / "out.json"

    text = export_json(finalized, output_path)

    assert output_path.read_text(encoding="utf-8") == text
    assert json.loads(output_path.read_text(encoding="utf-8"))["document_id"] == (
        happy_path_document.metadata.document_id
    )


def test_export_json_preserves_unicode(happy_path_document: W2Document) -> None:
    unicode_document = happy_path_document.model_copy(
        update={"employee": happy_path_document.employee.model_copy(update={"first_name": "José"})}
    )
    finalized = finalize_document(unicode_document, validate_w2_document(unicode_document))

    text = export_json(finalized)

    assert "José" in text
    assert "\\u00e9" not in text
    assert json.loads(text)["document"]["employee"]["first_name"] == "José"


def test_export_json_booleans_are_real_json_booleans(happy_path_document: W2Document) -> None:
    checked_document = happy_path_document.model_copy(
        update={"box_13": happy_path_document.box_13.model_copy(update={"retirement_plan": True})}
    )
    finalized = finalize_document(checked_document, validate_w2_document(checked_document))

    text = export_json(finalized)

    assert '"retirement_plan":true' in text.replace(" ", "").replace("\n", "")
    assert json.loads(text)["document"]["box_13"]["retirement_plan"] is True


def test_export_json_money_is_exact_string_not_float(happy_path_document: W2Document) -> None:
    """Phase 8D.1: money must never round-trip through a binary float --
    Decimal("114857.99999999997")-style artifacts are exactly what an
    exact-precision string representation avoids."""

    priced_document = happy_path_document.model_copy(
        update={
            "federal_wages_and_taxes": happy_path_document.federal_wages_and_taxes.model_copy(
                update={"box_1_wages_tips_other_compensation": Decimal("114857.99")}
            )
        }
    )
    finalized = finalize_document(priced_document, validate_w2_document(priced_document))

    text = export_json(finalized)
    payload = json.loads(text)

    assert payload["document"]["federal_wages_and_taxes"]["box_1_wages_tips_other_compensation"] == "114857.99"
    assert isinstance(
        payload["document"]["federal_wages_and_taxes"]["box_1_wages_tips_other_compensation"], str
    )


def test_export_json_null_field_is_json_null_not_empty_string(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={"employee": happy_path_document.employee.model_copy(update={"suffix": None})}
    )
    finalized = finalize_document(document, validate_w2_document(document))

    payload = json.loads(export_json(finalized))

    assert payload["document"]["employee"]["suffix"] is None


def test_export_json_ssn_leading_zero_preserved(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={"employee": happy_path_document.employee.model_copy(update={"ssn": "012-34-5678"})}
    )
    finalized = finalize_document(document, validate_w2_document(document))

    payload = json.loads(export_json(finalized))

    assert payload["document"]["employee"]["ssn"] == "012-34-5678"


def test_export_json_is_deterministic_across_repeated_exports(happy_path_document: W2Document) -> None:
    finalized = finalize_document(happy_path_document, validate_w2_document(happy_path_document))

    assert export_json(finalized) == export_json(finalized)
