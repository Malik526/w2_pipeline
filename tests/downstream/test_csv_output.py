import csv
import io
import json
from decimal import Decimal
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


def test_export_csv_boolean_representation_is_python_style_true_false(
    happy_path_document: W2Document,
) -> None:
    """Phase 8D.1: documents the ACTUAL representation, not an aspirational
    one -- CSV has no native boolean type, and this project's flattening
    (`str(value)` on the raw Python bool) produces capitalized `True`/
    `False`, not JSON-style lowercase `true`/`false` or `1`/`0`. Any
    representation is fine as long as it is deterministic and documented
    (see docs/contracts/review-and-downstream-output.md); this test pins
    down which one the code actually produces."""

    checked_document = happy_path_document.model_copy(
        update={
            "box_13": happy_path_document.box_13.model_copy(
                update={"retirement_plan": True, "statutory_employee": False}
            )
        }
    )
    finalized = finalize_document(checked_document, validate_w2_document(checked_document))

    row = _row(export_csv(finalized))

    assert row["box_13.retirement_plan"] == "True"
    assert row["box_13.statutory_employee"] == "False"


def test_export_csv_false_is_distinguishable_from_null(happy_path_document: W2Document) -> None:
    """A `False` checkbox must never be mistaken for a missing/null value."""

    document = happy_path_document.model_copy(
        update={"box_13": happy_path_document.box_13.model_copy(update={"retirement_plan": False})}
    )
    finalized = finalize_document(document, validate_w2_document(document))

    row = _row(export_csv(finalized))

    assert row["box_13.retirement_plan"] == "False"
    assert row["box_13.retirement_plan"] != row["employee.suffix"]  # suffix is null -> ""
    assert row["employee.suffix"] == ""


def test_export_csv_money_matches_json_exact_string(happy_path_document: W2Document) -> None:
    priced_document = happy_path_document.model_copy(
        update={
            "federal_wages_and_taxes": happy_path_document.federal_wages_and_taxes.model_copy(
                update={"box_1_wages_tips_other_compensation": Decimal("114857.99")}
            )
        }
    )
    finalized = finalize_document(priced_document, validate_w2_document(priced_document))

    row = _row(export_csv(finalized))

    assert row["federal_wages_and_taxes.box_1_wages_tips_other_compensation"] == "114857.99"


def test_export_csv_ssn_leading_zero_preserved(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={"employee": happy_path_document.employee.model_copy(update={"ssn": "012-34-5678"})}
    )
    finalized = finalize_document(document, validate_w2_document(document))

    row = _row(export_csv(finalized))

    assert row["employee.ssn"] == "012-34-5678"


def test_export_csv_escapes_commas_quotes_and_apostrophes(happy_path_document: W2Document) -> None:
    tricky_name = 'Smith, "Jones" & O\'Brien Corp'
    document = happy_path_document.model_copy(
        update={"employer": happy_path_document.employer.model_copy(update={"name": tricky_name})}
    )
    finalized = finalize_document(document, validate_w2_document(document))

    text = export_csv(finalized)
    row = _row(text)

    assert row["employer.name"] == tricky_name


def test_export_csv_column_order_is_deterministic_alphabetical(happy_path_document: W2Document) -> None:
    finalized = finalize_document(happy_path_document, validate_w2_document(happy_path_document))

    header = export_csv(finalized).splitlines()[0]
    columns = header.split(",")

    assert columns == sorted(columns)


def test_export_csv_is_deterministic_across_repeated_exports(happy_path_document: W2Document) -> None:
    finalized = finalize_document(happy_path_document, validate_w2_document(happy_path_document))

    assert export_csv(finalized) == export_csv(finalized)
