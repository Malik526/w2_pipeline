"""Phase 8D.4: canonical single-document production entry point.

`run_document()` is the one reusable service function that orchestrates
the complete current backend workflow for one arbitrary W-2 file:

    ingestion -> Pipeline A extraction -> evidence-preserving signal
    construction -> validation -> accepted (finalize + export) or
    needs_review (persist a `ReviewRecord`)

It does not reimplement any of those steps -- it only calls the existing
production components (`w2_pipeline.extraction.factory`,
`PipelineAExtractor`, `w2_pipeline.extraction.signals.build_extraction_signals`,
`validate_w2_document`, `finalize_document`, `export_json`/`export_csv`,
`start_review`, `FileReviewRepository`) in the real production sequence.

This function is the shared orchestration boundary for every current and
future caller -- the CLI (`w2_pipeline.cli.run_document`), a future
batch runner, and a future web API/UI all call this directly rather than
duplicating this sequence or shelling out to the CLI.
"""

from __future__ import annotations

import time
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from w2_pipeline.downstream.csv_output import export_csv
from w2_pipeline.downstream.finalize import finalize_document
from w2_pipeline.downstream.json_output import export_json
from w2_pipeline.extraction.factory import build_pipeline_a_extractor
from w2_pipeline.extraction.pipeline_a import PipelineAExtractor
from w2_pipeline.extraction.signals import build_extraction_signals
from w2_pipeline.review.repository import FileReviewRepository
from w2_pipeline.review.workflow import start_review
from w2_pipeline.validation.models import ValidationStatus
from w2_pipeline.validation.validator import validate_w2_document

DEFAULT_OUTPUT_DIR = Path("output")
DEFAULT_REVIEW_REPO_DIR = Path("data/review")
DEFAULT_OCR_BACKEND = "paddleocr"
DEFAULT_DEVICE = "gpu"
SUPPORTED_OUTPUT_FORMATS = ("json", "csv", "both")


class DocumentRunStatus(str, Enum):
    """Terminal outcome of one `run_document()` call."""

    ACCEPTED = "accepted"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class DocumentRunResult(BaseModel):
    """Structured, machine-readable outcome of one single-document run.

    This is also the exact shape written to `run_summary.json`, so a
    future skill/batch runner/UI can determine behavior entirely from
    that file (or this return value) rather than scraping terminal text.
    """

    model_config = ConfigDict(extra="forbid")

    status: DocumentRunStatus
    document_id: str = Field(min_length=1)
    input_file: str
    output_dir: str
    pipeline_id: str
    ocr_backend: str
    route: str | None = None
    validation_status: str | None = None
    issue_codes: list[str] = Field(default_factory=list)
    review_id: str | None = None
    finalized: bool = False
    outputs: dict[str, str] = Field(default_factory=dict)
    duration_seconds: float = Field(ge=0.0)
    error_message: str | None = None


def run_document(
    input_file: str | Path,
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    document_id: str | None = None,
    ocr_backend: str = DEFAULT_OCR_BACKEND,
    device: str | None = None,
    output_format: str = "both",
    review_repo_dir: str | Path = DEFAULT_REVIEW_REPO_DIR,
    extractor: PipelineAExtractor | None = None,
) -> DocumentRunResult:
    """Run one W-2 file through the complete production workflow.

    `extractor`, when given, is used as-is instead of building one from
    `ocr_backend`/`device` -- the seam tests use to exercise this
    orchestration without a real OCR backend. Every real caller (the
    CLI included) leaves this `None`.

    Never raises for an ingestion/extraction/OCR failure: that outcome
    is reported as a `DocumentRunStatus.FAILED` result instead, so a
    caller can distinguish "this document needs a human" from "this run
    itself broke" without a try/except of its own.
    """

    if output_format not in SUPPORTED_OUTPUT_FORMATS:
        raise ValueError(
            f"Unsupported output format {output_format!r}; expected one of {SUPPORTED_OUTPUT_FORMATS}."
        )

    input_path = Path(input_file)
    resolved_document_id = document_id or input_path.stem
    doc_output_dir = Path(output_dir) / resolved_document_id
    doc_output_dir.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    try:
        if extractor is None:
            extractor = build_pipeline_a_extractor(
                ocr_backend=ocr_backend,
                paddle_device=device or DEFAULT_DEVICE,
            )
        ingested = extractor.ingestion_service.ingest(input_path, document_id=resolved_document_id)
        result = extractor.extract_ingested(ingested)
    except Exception as exc:  # noqa: BLE001 - isolate and report, never crash the caller.
        duration = time.perf_counter() - started
        run_result = DocumentRunResult(
            status=DocumentRunStatus.FAILED,
            document_id=resolved_document_id,
            input_file=str(input_path),
            output_dir=str(doc_output_dir),
            pipeline_id=PipelineAExtractor.pipeline_id,
            ocr_backend=ocr_backend,
            duration_seconds=duration,
            error_message=f"{exc.__class__.__name__}: {exc}",
        )
        _write_run_summary(doc_output_dir, run_result)
        return run_result

    signals = build_extraction_signals(result)
    (doc_output_dir / "extracted.json").write_text(result.document.model_dump_json(indent=2), encoding="utf-8")
    (doc_output_dir / "signals.json").write_text(signals.model_dump_json(indent=2), encoding="utf-8")

    validation_result = validate_w2_document(result.document, signals=signals)
    (doc_output_dir / "validation.json").write_text(validation_result.model_dump_json(indent=2), encoding="utf-8")

    duration = time.perf_counter() - started
    issue_codes = [issue.code for issue in validation_result.issues]

    if validation_result.status == ValidationStatus.ACCEPTED:
        finalized = finalize_document(result.document, validation_result)
        outputs: dict[str, str] = {}
        if output_format in ("json", "both"):
            json_path = doc_output_dir / "final.json"
            export_json(finalized, json_path)
            outputs["json"] = str(json_path)
        if output_format in ("csv", "both"):
            csv_path = doc_output_dir / "final.csv"
            export_csv(finalized, csv_path)
            outputs["csv"] = str(csv_path)

        run_result = DocumentRunResult(
            status=DocumentRunStatus.ACCEPTED,
            document_id=resolved_document_id,
            input_file=str(input_path),
            output_dir=str(doc_output_dir),
            pipeline_id=extractor.pipeline_id,
            ocr_backend=ocr_backend,
            route=result.route.value,
            validation_status=validation_result.status.value,
            issue_codes=issue_codes,
            review_id=None,
            finalized=True,
            outputs=outputs,
            duration_seconds=duration,
        )
        _write_run_summary(doc_output_dir, run_result)
        return run_result

    review_record = start_review(
        result.document,
        validation_result,
        document_id=resolved_document_id,
        pipeline_metadata={"pipeline_id": extractor.pipeline_id, "route": result.route.value},
    )
    FileReviewRepository(review_repo_dir).save(review_record)

    run_result = DocumentRunResult(
        status=DocumentRunStatus.NEEDS_REVIEW,
        document_id=resolved_document_id,
        input_file=str(input_path),
        output_dir=str(doc_output_dir),
        pipeline_id=extractor.pipeline_id,
        ocr_backend=ocr_backend,
        route=result.route.value,
        validation_status=validation_result.status.value,
        issue_codes=issue_codes,
        review_id=review_record.review_id,
        finalized=False,
        outputs={},
        duration_seconds=duration,
    )
    _write_run_summary(doc_output_dir, run_result)
    return run_result


def _write_run_summary(doc_output_dir: Path, run_result: DocumentRunResult) -> None:
    (doc_output_dir / "run_summary.json").write_text(run_result.model_dump_json(indent=2), encoding="utf-8")
