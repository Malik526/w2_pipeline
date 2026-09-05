import csv
import io
import json
from pathlib import Path

from w2_pipeline.contracts.w2 import Box12Entry, W2Document
from w2_pipeline.downstream.csv_output import export_csv
from w2_pipeline.downstream.finalize import finalize_document
from w2_pipeline.validation.validator import validate_w2_document


def _row(text: str) -> dict[str, str]:
    reader = csv.DictReader(io.StringIO(text))
    return next(reader)


def test_export_csv_produces_single_row_with_scalar_columns(happy_path_document: W2Document) -> None:
    finalized = finalize_document(happy_path_document, validate_w2_document(happy_path_document))

    text = export_csv(finalized)

    row = _row(text)
    assert row["employee.ssn"] == happy_path_document.employee.ssn
    assert row["employer.ein"] == happy_path_document.employer.ein
    assert row["metadata.tax_year"] == "2026"


def test_export_csv_encodes_repeated_structures_as_json_strings(
    happy_path_document: W2Document,
) -> None:
    document = happy_path_document.model_copy(
        update={
            "box_12_entries": [
                Box12Entry(code="D", amount="500.00"),
                Box12Entry(code="DD", amount="1200.00"),
            ]
        }
    )
    finalized = finalize_document(document, validate_w2_document(document))

    text = export_csv(finalized)

    row = _row(text)
    decoded = json.loads(row["box_12_entries"])
    assert decoded == [
        {"code": "D", "amount": "500.00"},
        {"code": "DD", "amount": "1200.00"},
    ]


def test_export_csv_empty_repeated_structure_is_empty_json_array(
    happy_path_document: W2Document,
) -> None:
    document = happy_path_document.model_copy(update={"box_12_entries": []})
    finalized = finalize_document(document, validate_w2_document(document))

    text = export_csv(finalized)

    row = _row(text)
    assert json.loads(row["box_12_entries"]) == []


def test_export_csv_writes_to_path(happy_path_document: W2Document, tmp_path: Path) -> None:
    finalized = finalize_document(happy_path_document, validate_w2_document(happy_path_document))
    output_path = tmp_path / "out.csv"

    text = export_csv(finalized, output_path)

    # Compare via csv.DictReader rather than raw string equality: `Path.read_text`
    # normalizes the CSV module's "\r\n" line endings to "\n" under universal
    # newlines, so a byte-for-byte comparison against the in-memory `text`
    # (still raw "\r\n") would fail despite the file being written correctly.
    assert _row(output_path.read_text(encoding="utf-8")) == _row(text)


def test_export_csv_preserves_unicode(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={"employee": happy_path_document.employee.model_copy(update={"first_name": "José"})}
    )
    finalized = finalize_document(document, validate_w2_document(document))

    text = export_csv(finalized)

    row = _row(text)
    assert row["employee.first_name"] == "José"


def test_export_csv_null_scalar_becomes_empty_cell(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={"employee": happy_path_document.employee.model_copy(update={"suffix": None})}
    )
    finalized = finalize_document(document, validate_w2_document(document))

    text = export_csv(finalized)

    row = _row(text)
    assert row["employee.suffix"] == ""


def test_export_csv_excludes_field_observations_column(happy_path_document: W2Document) -> None:
    finalized = finalize_document(happy_path_document, validate_w2_document(happy_path_document))

    text = export_csv(finalized)

    header = text.splitlines()[0]
    assert "field_observations" not in header
