"""Phase 8D.5: batch runner CLI tests.

`test_cli_accepted_path_real_native_pdf_extraction` drives the real CLI
entry point (`main()`) end to end against three generated native-PDF
documents -- no OCR/GPU dependency, same reasoning as
`tests/cli/test_run_document_cli.py`. The remaining tests patch the
imported `run_batch` symbol to check the CLI's own responsibilities in
isolation: input resolution, exit-code mapping, and terminal output,
independent of the orchestration logic itself (already covered by
`tests/application/test_run_batch.py`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from w2_pipeline.application.run_batch import BatchRunResult
from w2_pipeline.application.run_document import DocumentRunResult, DocumentRunStatus
from w2_pipeline.cli import run_batch as cli
from w2_pipeline.evaluation.dataset import generate_evaluation_dataset


def test_cli_accepted_path_real_native_pdf_extraction(tmp_path: Path) -> None:
    generate_evaluation_dataset(tmp_path, sample_count=3, seed=2026)
    documents_dir = tmp_path / "documents"
    pdf_paths = sorted(documents_dir.glob("*_clean.pdf"))
    assert len(pdf_paths) == 3

    exit_code = cli.main(
        [
            *[str(path) for path in pdf_paths],
            "--output-dir",
            str(tmp_path / "output"),
            "--ocr-backend",
            "tesseract",
            "--review-repo-dir",
            str(tmp_path / "review"),
        ]
    )

    assert exit_code == cli.EXIT_SUCCESS
    summary_path = tmp_path / "output" / "batch_summary.json"
    assert summary_path.exists()
    for pdf_path in pdf_paths:
        doc_dir = tmp_path / "output" / pdf_path.stem
        assert (doc_dir / "final.json").exists()
        assert (doc_dir / "final.csv").exists()
    aggregate_csv = tmp_path / "output" / "batch_finalized.csv"
    assert aggregate_csv.exists()


def _fake_document_result(status: DocumentRunStatus, document_id: str, **overrides: object) -> DocumentRunResult:
    defaults = dict(
        status=status,
        document_id=document_id,
        input_file=f"{document_id}.png",
        output_dir=f"output/{document_id}",
        pipeline_id="pipeline_a",
        ocr_backend="paddleocr",
        route="ocr",
        validation_status=status.value,
        issue_codes=[],
        review_id=None,
        finalized=status is DocumentRunStatus.ACCEPTED,
        outputs={},
        model_startup_seconds=0.0,
        processing_latency_seconds=1.2,
        total_duration_seconds=1.2,
        error_message=None,
    )
    defaults.update(overrides)
    return DocumentRunResult(**defaults)


def _fake_batch_result(documents: list[DocumentRunResult], **overrides: object) -> BatchRunResult:
    accepted = sum(1 for doc in documents if doc.status is DocumentRunStatus.ACCEPTED)
    needs_review = sum(1 for doc in documents if doc.status is DocumentRunStatus.NEEDS_REVIEW)
    failed = sum(1 for doc in documents if doc.status is DocumentRunStatus.FAILED)
    defaults = dict(
        pipeline_id="pipeline_a",
        ocr_backend="paddleocr",
        device="gpu",
        documents_total=len(documents),
        accepted=accepted,
        needs_review=needs_review,
        failed=failed,
        model_startup_seconds=8.1,
        batch_processing_seconds=3.6,
        total_duration_seconds=11.7,
        mean_document_latency_seconds=1.2,
        median_document_latency_seconds=1.2,
        aggregate_csv="output/batch_finalized.csv" if accepted else None,
        documents=documents,
    )
    defaults.update(overrides)
    return BatchRunResult(**defaults)


def test_cli_exit_zero_when_no_document_fails(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    documents = [
        _fake_document_result(DocumentRunStatus.ACCEPTED, "doc_a"),
        _fake_document_result(DocumentRunStatus.NEEDS_REVIEW, "doc_b", review_id="11111111-1111-1111-1111-111111111111"),
    ]
    monkeypatch.setattr(cli, "run_batch", lambda *args, **kwargs: _fake_batch_result(documents))

    exit_code = cli.main(["doc_a.png", "doc_b.png"])

    assert exit_code == cli.EXIT_SUCCESS
    out = capsys.readouterr().out
    assert "Accepted:         1" in out
    assert "Needs review:     1" in out
    assert "Failed:           0" in out
    assert "batch_finalized.csv" in out


def test_cli_exit_one_when_any_document_fails(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    documents = [
        _fake_document_result(DocumentRunStatus.ACCEPTED, "doc_a"),
        _fake_document_result(DocumentRunStatus.FAILED, "doc_bad", validation_status=None, error_message="boom"),
    ]
    monkeypatch.setattr(cli, "run_batch", lambda *args, **kwargs: _fake_batch_result(documents))

    exit_code = cli.main(["doc_a.png", "doc_bad.png"])

    assert exit_code == cli.EXIT_FAILURE
    out = capsys.readouterr().out
    assert "Failed:           1" in out


def test_cli_exit_one_when_shared_backend_cannot_start(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    def _raise(*args, **kwargs):  # noqa: ANN001 - test double
        raise RuntimeError("simulated missing OCR dependency")

    monkeypatch.setattr(cli, "run_batch", _raise)

    exit_code = cli.main(["doc_a.png"])

    assert exit_code == cli.EXIT_FAILURE
    out = capsys.readouterr().out
    assert "simulated missing OCR dependency" in out


def test_cli_requires_at_least_one_input(capsys: pytest.CaptureFixture) -> None:
    with pytest.raises(SystemExit):
        cli.main([])


def test_resolve_input_files_combines_positional_and_input_dir(tmp_path: Path) -> None:
    (tmp_path / "a.png").write_bytes(b"x")
    (tmp_path / "b.jpg").write_bytes(b"x")
    (tmp_path / "ignored.txt").write_bytes(b"x")
    positional = tmp_path / "c.png"
    positional.write_bytes(b"x")

    resolved = cli._resolve_input_files([positional], tmp_path)

    names = {path.name for path in resolved}
    assert names == {"a.png", "b.jpg", "c.png"}


def test_cli_defaults_reflect_production_choices() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(["some_file.png"])

    assert args.ocr_backend == "paddleocr"
    assert args.device == "gpu"
    assert args.aggregate_csv == cli.DEFAULT_AGGREGATE_CSV_NAME
