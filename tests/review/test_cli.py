import json
from pathlib import Path

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.review.cli import main


def _write_document(document: W2Document, path: Path) -> None:
    path.write_text(document.model_dump_json(), encoding="utf-8")


def test_cli_validate_accepted_document(
    happy_path_document: W2Document, tmp_path: Path, capsys
) -> None:
    doc_path = tmp_path / "w2.json"
    _write_document(happy_path_document, doc_path)

    main(["validate", str(doc_path)])

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "accepted"


def test_cli_export_document_accepted(
    happy_path_document: W2Document, tmp_path: Path, capsys
) -> None:
    doc_path = tmp_path / "w2.json"
    _write_document(happy_path_document, doc_path)

    main(["export-document", str(doc_path), "--format", "json"])

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "accepted"
    assert output["document"]["employee"]["ssn"] == happy_path_document.employee.ssn


def test_cli_export_document_writes_csv_to_output_path(
    happy_path_document: W2Document, tmp_path: Path, capsys
) -> None:
    doc_path = tmp_path / "w2.json"
    _write_document(happy_path_document, doc_path)
    output_path = tmp_path / "out.csv"

    main(["export-document", str(doc_path), "--format", "csv", "--output", str(output_path)])

    capsys.readouterr()
    assert output_path.exists()
    assert happy_path_document.employer.ein in output_path.read_text(encoding="utf-8")


def test_cli_full_review_flow(happy_path_document: W2Document, tmp_path: Path, capsys) -> None:
    """The brief's Flow B, driven entirely through the CLI."""

    bad_document = happy_path_document.model_copy(
        update={"employee": happy_path_document.employee.model_copy(update={"ssn": None})}
    )
    doc_path = tmp_path / "w2.json"
    _write_document(bad_document, doc_path)
    repo_dir = tmp_path / "repo"

    main(["review-create", str(doc_path), "--repo-dir", str(repo_dir)])
    record = json.loads(capsys.readouterr().out)
    assert record["status"] == "pending"
    review_id = record["review_id"]

    main(
        [
            "review-correct",
            review_id,
            "--repo-dir",
            str(repo_dir),
            "--field-path",
            "employee.ssn",
            "--new-value",
            '"123-45-6789"',
            "--reason",
            "verified against source",
        ]
    )
    corrected = json.loads(capsys.readouterr().out)
    assert corrected["status"] == "in_review"
    assert len(corrected["corrections"]) == 1

    main(["review-revalidate", review_id, "--repo-dir", str(repo_dir)])
    revalidated = json.loads(capsys.readouterr().out)
    assert revalidated["status"] == "resolved"
    assert revalidated["revalidation_result"]["status"] == "accepted"

    main(["export-review", review_id, "--repo-dir", str(repo_dir), "--format", "json"])
    exported = json.loads(capsys.readouterr().out)
    assert exported["document"]["employee"]["ssn"] == "123-45-6789"


def test_cli_review_create_reports_accepted_without_creating_record(
    happy_path_document: W2Document, tmp_path: Path, capsys
) -> None:
    doc_path = tmp_path / "w2.json"
    _write_document(happy_path_document, doc_path)
    repo_dir = tmp_path / "repo"

    main(["review-create", str(doc_path), "--repo-dir", str(repo_dir)])

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "accepted"
    assert not repo_dir.exists() or list(repo_dir.glob("*.json")) == []


def test_cli_new_value_parses_json_boolean(happy_path_document: W2Document, tmp_path: Path, capsys) -> None:
    bad_document = happy_path_document.model_copy(
        update={"employee": happy_path_document.employee.model_copy(update={"ssn": None})}
    )
    doc_path = tmp_path / "w2.json"
    _write_document(bad_document, doc_path)
    repo_dir = tmp_path / "repo"

    main(["review-create", str(doc_path), "--repo-dir", str(repo_dir)])
    review_id = json.loads(capsys.readouterr().out)["review_id"]

    main(
        [
            "review-correct",
            review_id,
            "--repo-dir",
            str(repo_dir),
            "--field-path",
            "box_13.statutory_employee",
            "--new-value",
            "true",
        ]
    )
    corrected = json.loads(capsys.readouterr().out)
    assert corrected["corrected_document"]["box_13"]["statutory_employee"] is True
