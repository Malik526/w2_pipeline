"""Phase 8D.4: single-document runner CLI tests.

`test_cli_accepted_path_exit_code_and_real_outputs` drives the real CLI
entry point (`main()`) end to end against a generated native-PDF
document -- no OCR/GPU dependency, same reasoning as
`tests/application/test_run_document.py`. The remaining tests patch the
imported `run_document` symbol to check the CLI's own responsibilities
in isolation: exit-code mapping and terminal output, independent of the
orchestration logic itself (already covered by
`tests/application/test_run_document.py`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from w2_pipeline.application.run_document import DocumentRunResult, DocumentRunStatus
from w2_pipeline.cli import run_document as cli
from w2_pipeline.evaluation.dataset import generate_evaluation_dataset


def test_cli_accepted_path_exit_code_and_real_outputs(tmp_path: Path) -> None:
    generate_evaluation_dataset(tmp_path, sample_count=1, seed=2026)
    pdf_path = tmp_path / "documents" / "w2_2026_0001_clean.pdf"

    exit_code = cli.main(
        [
            str(pdf_path),
            "--output-dir",
            str(tmp_path / "output"),
            "--ocr-backend",
            "tesseract",
            "--review-repo-dir",
            str(tmp_path / "review"),
        ]
    )

    assert exit_code == cli.EXIT_ACCEPTED
    doc_dir = tmp_path / "output" / "w2_2026_0001_clean"
    assert (doc_dir / "final.json").exists()
    assert (doc_dir / "final.csv").exists()
    assert (doc_dir / "run_summary.json").exists()


def _fake_result(status: DocumentRunStatus, **overrides: object) -> DocumentRunResult:
    defaults = dict(
        status=status,
        document_id="symage_900001",
        input_file="input.png",
        output_dir="output/symage_900001",
        pipeline_id="pipeline_a",
        ocr_backend="paddleocr",
        route="ocr",
        validation_status=status.value,
        issue_codes=[],
        review_id=None,
        finalized=False,
        outputs={},
        model_startup_seconds=0.01,
        processing_latency_seconds=1.22,
        total_duration_seconds=1.23,
        error_message=None,
    )
    defaults.update(overrides)
    return DocumentRunResult(**defaults)


def test_cli_maps_accepted_to_exit_zero(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    result = _fake_result(
        DocumentRunStatus.ACCEPTED,
        finalized=True,
        outputs={"json": "output/symage_900001/final.json", "csv": "output/symage_900001/final.csv"},
    )
    monkeypatch.setattr(cli, "run_document", lambda *args, **kwargs: result)

    exit_code = cli.main(["some_file.png"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "ACCEPTED" in out
    assert "final.json" in out
    assert "final.csv" in out
    assert "Model startup:" in out
    assert "Document latency:" in out
    assert "Total wall time:" in out


def test_cli_maps_needs_review_to_exit_two(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    result = _fake_result(
        DocumentRunStatus.NEEDS_REVIEW,
        issue_codes=["employer_address_extraction_incomplete", "employee_address_extraction_incomplete"],
        review_id="11111111-1111-1111-1111-111111111111",
    )
    monkeypatch.setattr(cli, "run_document", lambda *args, **kwargs: result)

    exit_code = cli.main(["some_file.png"])

    assert exit_code == 2
    out = capsys.readouterr().out
    assert "NEEDS REVIEW" in out
    assert "employer_address_extraction_incomplete" in out
    assert "11111111-1111-1111-1111-111111111111" in out
    assert "BLOCKED" in out


def test_cli_maps_failure_to_exit_one(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    result = _fake_result(
        DocumentRunStatus.FAILED,
        validation_status=None,
        error_message="DocumentNotFoundError: Source document not found: missing.png",
    )
    monkeypatch.setattr(cli, "run_document", lambda *args, **kwargs: result)

    exit_code = cli.main(["missing.png"])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "DocumentNotFoundError" in out


def test_cli_defaults_reflect_production_choices() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(["some_file.png"])

    assert args.ocr_backend == "paddleocr"
    assert args.device == "gpu"
    assert args.format == "both"
