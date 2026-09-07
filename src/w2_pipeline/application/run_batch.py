"""Phase 8D.5: canonical multi-document production entry point.

`run_batch()` is the reusable service function that runs many W-2 files
through the exact same production workflow `run_document()` already
orchestrates, while reusing one Pipeline A extractor (and therefore one
warmed OCR backend, e.g. one loaded PaddleOCR model) across every
document instead of paying that one-time cost per file.

It does not reimplement extraction, validation, review, finalization, or
export -- it builds one extractor, warms it up once, then calls
`w2_pipeline.application.run_document.run_document()` once per input
file with that same extractor. The only batch-specific logic here is:
looping over inputs, aggregating per-document results into
`BatchRunResult`, and building the accepted-only aggregate CSV (itself
built on `w2_pipeline.downstream.csv_output.export_csv_rows`, the same
flattening/column-ordering primitive a single document's own CSV uses).

Each `run_document()` call already never raises for an
ingestion/extraction/OCR failure (it reports `DocumentRunStatus.FAILED`
instead), so one bad document cannot stop this loop -- failure isolation
falls out of reusing that existing contract rather than needing its own
try/except here. Only the shared extractor's own one-time `warm_up()` is
allowed to raise out of this function: if the OCR backend itself cannot
become ready, no document in the batch could have processed anyway, so
that is a runtime-unusable condition, not a per-document outcome.
"""

from __future__ import annotations

import statistics
import time
from pathlib import Path
from typing import Callable, Sequence

from pydantic import BaseModel, ConfigDict, Field

from w2_pipeline.application.run_document import (
    DEFAULT_DEVICE,
    DEFAULT_OCR_BACKEND,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_REVIEW_REPO_DIR,
    DocumentRunResult,
    DocumentRunStatus,
    run_document,
)
from w2_pipeline.downstream.csv_output import export_csv_rows
from w2_pipeline.downstream.models import FinalizedW2
from w2_pipeline.extraction.factory import build_pipeline_a_extractor
from w2_pipeline.extraction.pipeline_a import PipelineAExtractor

DEFAULT_AGGREGATE_CSV_NAME = "batch_finalized.csv"


class BatchRunResult(BaseModel):
    """Structured, machine-readable outcome of one `run_batch()` call.

    This is also the exact shape written to `batch_summary.json`, so a
    future skill/UI can determine batch outcome entirely from that file
    (or this return value) rather than scraping terminal text -- same
    convention `DocumentRunResult`/`run_summary.json` already establish.
    """

    model_config = ConfigDict(extra="forbid")

    pipeline_id: str
    ocr_backend: str
    device: str
    documents_total: int = Field(ge=0)
    accepted: int = Field(ge=0)
    needs_review: int = Field(ge=0)
    failed: int = Field(ge=0)
    model_startup_seconds: float = Field(ge=0.0)
    batch_processing_seconds: float = Field(ge=0.0)
    total_duration_seconds: float = Field(ge=0.0)
    mean_document_latency_seconds: float = Field(ge=0.0)
    median_document_latency_seconds: float = Field(ge=0.0)
    aggregate_csv: str | None = None
    documents: list[DocumentRunResult] = Field(default_factory=list)


def run_batch(
    input_files: Sequence[str | Path],
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    ocr_backend: str = DEFAULT_OCR_BACKEND,
    device: str | None = None,
    review_repo_dir: str | Path = DEFAULT_REVIEW_REPO_DIR,
    aggregate_csv_name: str = DEFAULT_AGGREGATE_CSV_NAME,
    extractor: PipelineAExtractor | None = None,
    on_ready: Callable[[float], None] | None = None,
    on_document_start: Callable[[int, int, Path], None] | None = None,
    on_document_complete: Callable[[DocumentRunResult], None] | None = None,
) -> BatchRunResult:
    """Run many W-2 files through the complete production workflow.

    `extractor`, when given, is used as-is (and still has its own
    `warm_up()` called, which is a cheap no-op if it is already warm) --
    the seam tests use to exercise this orchestration without a real OCR
    backend. Every real caller (the CLI included) leaves this `None`, in
    which case one extractor is built here from `ocr_backend`/`device`
    and reused for every document.

    Unlike `run_document()`, there is no `output_format` choice here:
    each document is always run with `output_format="both"` so an
    accepted document's `final.json` is always on disk, which the
    aggregate CSV (`_write_aggregate_csv`) reads back rather than
    re-deriving -- matching this project's existing per-document output
    contract (`docs/single-document-runner.md`) and this phase's own
    recommended batch CLI surface, neither of which expose a `--format`
    flag at the batch level.

    `on_ready`/`on_document_start`/`on_document_complete` are optional
    progress hooks (each called synchronously, in order) so a thin CLI
    can render per-document terminal output without reimplementing this
    loop or the timing/ordering it produces.
    """

    resolved_device = device or DEFAULT_DEVICE
    input_paths = [Path(input_file) for input_file in input_files]
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    total_started = time.perf_counter()
    if extractor is None:
        extractor = build_pipeline_a_extractor(ocr_backend=ocr_backend, paddle_device=resolved_device)
    warmup_started = time.perf_counter()
    extractor.warm_up()
    model_startup_seconds = time.perf_counter() - warmup_started
    if on_ready is not None:
        on_ready(model_startup_seconds)

    processing_started = time.perf_counter()
    documents: list[DocumentRunResult] = []
    for index, input_path in enumerate(input_paths, start=1):
        if on_document_start is not None:
            on_document_start(index, len(input_paths), input_path)
        result = run_document(
            input_path,
            output_dir=out_dir,
            ocr_backend=ocr_backend,
            device=resolved_device,
            output_format="both",
            review_repo_dir=review_repo_dir,
            extractor=extractor,
        )
        documents.append(result)
        if on_document_complete is not None:
            on_document_complete(result)
    batch_processing_seconds = time.perf_counter() - processing_started

    accepted = [doc for doc in documents if doc.status is DocumentRunStatus.ACCEPTED]
    needs_review_count = sum(1 for doc in documents if doc.status is DocumentRunStatus.NEEDS_REVIEW)
    failed_count = sum(1 for doc in documents if doc.status is DocumentRunStatus.FAILED)

    latencies = [doc.processing_latency_seconds for doc in documents]
    mean_latency = statistics.mean(latencies) if latencies else 0.0
    median_latency = statistics.median(latencies) if latencies else 0.0

    aggregate_csv_path = _write_aggregate_csv(accepted, out_dir / aggregate_csv_name)

    batch_result = BatchRunResult(
        pipeline_id=PipelineAExtractor.pipeline_id,
        ocr_backend=ocr_backend,
        device=resolved_device,
        documents_total=len(documents),
        accepted=len(accepted),
        needs_review=needs_review_count,
        failed=failed_count,
        model_startup_seconds=model_startup_seconds,
        batch_processing_seconds=batch_processing_seconds,
        total_duration_seconds=time.perf_counter() - total_started,
        mean_document_latency_seconds=mean_latency,
        median_document_latency_seconds=median_latency,
        aggregate_csv=str(aggregate_csv_path) if aggregate_csv_path is not None else None,
        documents=documents,
    )
    (out_dir / "batch_summary.json").write_text(batch_result.model_dump_json(indent=2), encoding="utf-8")
    return batch_result


def _write_aggregate_csv(accepted: list[DocumentRunResult], path: Path) -> Path | None:
    """Write one row per accepted/finalized document to `path`.

    Returns `None` (and writes nothing) when there are zero accepted
    documents -- there is no schema-independent way to produce a header
    with no finalized document to derive columns from, and a
    `needs_review`/`failed` document must never appear here regardless.
    Reads each document's own already-written `final.json` back rather
    than re-deriving a `FinalizedW2`, so this is guaranteed to match that
    document's individually exported `final.csv` byte for byte.
    """

    if not accepted:
        return None

    finalized_documents = [
        FinalizedW2.model_validate_json(Path(doc.outputs["json"]).read_text(encoding="utf-8"))
        for doc in accepted
    ]
    export_csv_rows(finalized_documents, path=path)
    return path
