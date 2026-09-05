import json
from pathlib import Path

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.validation.validate_w2 import main


def test_cli_accepts_valid_document(
    happy_path_document: W2Document, tmp_path: Path, capsys
) -> None:
    document_path = tmp_path / "w2.json"
    document_path.write_text(happy_path_document.model_dump_json(), encoding="utf-8")

    main([str(document_path)])

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "accepted"
    assert output["issues"] == []


def test_cli_flags_missing_ssn(happy_path_document: W2Document, tmp_path: Path, capsys) -> None:
    document = happy_path_document.model_copy(
        update={"employee": happy_path_document.employee.model_copy(update={"ssn": None})}
    )
    document_path = tmp_path / "w2.json"
    document_path.write_text(document.model_dump_json(), encoding="utf-8")

    main([str(document_path)])

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "needs_review"
    assert any(issue["code"] == "required_field_missing" for issue in output["issues"])


def test_cli_handles_invalid_json_as_invalid_canonical_result(tmp_path: Path, capsys) -> None:
    document_path = tmp_path / "broken.json"
    document_path.write_text("{not valid json", encoding="utf-8")

    main([str(document_path)])

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "needs_review"
    assert output["issues"][0]["code"] == "extraction_output_invalid"


def test_cli_handles_missing_file(tmp_path: Path, capsys) -> None:
    missing_path = tmp_path / "does_not_exist.json"

    main([str(missing_path)])

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "needs_review"
    assert output["issues"][0]["code"] == "extraction_output_invalid"


def test_cli_records_pipeline_id_and_route_flags(
    happy_path_document: W2Document, tmp_path: Path, capsys
) -> None:
    document_path = tmp_path / "w2.json"
    document_path.write_text(happy_path_document.model_dump_json(), encoding="utf-8")

    main([str(document_path), "--pipeline-id", "pipeline_a", "--route", "native_pdf"])

    output = json.loads(capsys.readouterr().out)
    assert output["pipeline_metadata"] == {"pipeline_id": "pipeline_a", "route": "native_pdf"}
