import json
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
