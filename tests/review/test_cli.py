import json
from pathlib import Path

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.review.cli import main
from w2_pipeline.validation.models import ExtractionSignals


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


def test_cli_route_ocr_without_signals_json_flags_missing_checkbox_evidence(
    happy_path_document: W2Document, tmp_path: Path, capsys
) -> None:
    """Documents the pre-fix gap: `--route ocr` alone (no evidence) makes even
    a well-extracted document fail the route-scoped checkbox-evidence rule,
    because `--pipeline-id`/`--route` cannot carry the evidence that a real
    `pipeline_a` OCR-route extraction actually produces (Phase 8D.2)."""

    doc_path = tmp_path / "w2.json"
    _write_document(happy_path_document, doc_path)

    main(["validate", str(doc_path), "--pipeline-id", "pipeline_a", "--route", "ocr"])

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "needs_review"
    assert any(issue["code"] == "retirement_plan_checkbox_evidence_missing" for issue in output["issues"])


def test_cli_signals_json_supplies_full_route_evidence(
    happy_path_document: W2Document, tmp_path: Path, capsys
) -> None:
    """Phase 8D.2 fix: `--signals-json` lets a caller supply the full
    `ExtractionSignals` a real extraction produced (checkbox/address
    evidence included), so a genuinely well-extracted `--route ocr`
    document validates as accepted instead of falsely needing review."""

    doc_path = tmp_path / "w2.json"
    _write_document(happy_path_document, doc_path)
    signals = ExtractionSignals(
        pipeline_id="pipeline_a",
        route="ocr",
        employer_name_observation_count=1,
        checkbox_evidence_detection_method="anchor_relative",
        checkbox_evidence_fallback_used=False,
        checkbox_evidence_anchor_found=True,
        checkbox_evidence_checkbox_found=True,
        checkbox_evidence_anchor_distance_px=-1.0,
        checkbox_evidence_horizontal_alignment_offset_px=0.0,
        checkbox_evidence_shape_score=0.86,
        checkbox_evidence_interior_ink_ratio=0.26,
        checkbox_evidence_decision_margin=0.14,
    )
    signals_path = tmp_path / "signals.json"
    signals_path.write_text(signals.model_dump_json(), encoding="utf-8")

    main(
        [
            "validate",
            str(doc_path),
            "--pipeline-id",
            "pipeline_a",
            "--route",
            "ocr",
            "--signals-json",
            str(signals_path),
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "accepted"
    assert output["issues"] == []


def test_cli_signals_json_overridden_by_explicit_pipeline_flags(
    happy_path_document: W2Document, tmp_path: Path, capsys
) -> None:
    """`--pipeline-id`/`--route`, when also passed, override the
    corresponding fields loaded from `--signals-json`."""

    doc_path = tmp_path / "w2.json"
    _write_document(happy_path_document, doc_path)
    signals_path = tmp_path / "signals.json"
    signals_path.write_text(
        ExtractionSignals(pipeline_id="pipeline_a", route="ocr").model_dump_json(), encoding="utf-8"
    )

    main(
        [
            "validate",
            str(doc_path),
            "--pipeline-id",
            "pipeline_b",
            "--route",
            "vlm",
            "--signals-json",
            str(signals_path),
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert output["pipeline_metadata"] == {"pipeline_id": "pipeline_b", "route": "vlm"}


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
