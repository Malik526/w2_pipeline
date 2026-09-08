"""Application-layer glue between the demo UI's uploads and the
canonical `run_document()`/`run_batch()` services.

Holds the one thing genuinely new here: a lazily-built, warmed-once,
lock-serialized shared Pipeline A extractor reused across requests, so
a long-running API process pays PaddleOCR startup once rather than per
request -- the same shared-extractor pattern `run_batch()` already uses
within a single batch, extended across HTTP requests. No extraction,
validation, review, or export logic is reimplemented here.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from w2_pipeline.api.schemas import DocumentDetailOut, DocumentResultOut, ProcessingRunOut
from w2_pipeline.api.uploads import StagedUpload
from w2_pipeline.application.run_batch import DEFAULT_AGGREGATE_CSV_NAME, BatchRunResult, run_batch
from w2_pipeline.application.run_document import DocumentRunResult, DocumentRunStatus, run_document
from w2_pipeline.extraction.factory import build_pipeline_a_extractor
from w2_pipeline.extraction.pipeline_a import PipelineAExtractor

_RUN_METADATA_FILENAME = "ui_run.json"

_extractor_lock = threading.Lock()
_shared_extractor: PipelineAExtractor | None = None


class ProcessorBusyError(RuntimeError):
    """Another request is currently holding the shared extractor."""


class ProcessorUnavailableError(RuntimeError):
    """The shared OCR backend could not become ready."""


def _get_shared_extractor() -> PipelineAExtractor:
    """Build and warm the shared extractor on first use; cache it after.

    Left `None` on a warm-up failure so a later request can retry rather
    than permanently caching a broken extractor.
    """

    global _shared_extractor
    if _shared_extractor is None:
        extractor = build_pipeline_a_extractor(ocr_backend="paddleocr", paddle_device="gpu")
        extractor.warm_up()
        _shared_extractor = extractor
    return _shared_extractor


def process_uploads(
    staged: list[StagedUpload],
    *,
    run_id: str,
    output_root: Path,
    review_repo_dir: Path,
) -> ProcessingRunOut:
    """Run one UI request's staged uploads and persist its result.

    Exactly one `run_document()`/`run_batch()` call is made regardless
    of file count (one file -> `run_document()`, two or more ->
    `run_batch()`) -- never one call per file, which would defeat the
    shared-extractor warm-up this function exists to provide.
    """

    if not _extractor_lock.acquire(blocking=False):
        raise ProcessorBusyError("Another document is currently being processed; try again shortly.")
    try:
        warmup_started = time.perf_counter()
        try:
            extractor = _get_shared_extractor()
        except Exception as exc:  # noqa: BLE001 - reported to the caller as a clean 502, not a crash.
            raise ProcessorUnavailableError(str(exc)) from exc
        # Real, measured cost of getting the shared backend ready for
        # *this* request: near-zero once another request has already
        # warmed it, the real cold-start cost (PaddleOCR model
        # construction) only the first time in this server process's
        # lifetime. `run_document()`/`run_batch()` below always see an
        # already-warm extractor by this point, so their own internal
        # `model_startup_seconds` would otherwise always read ~0 even on
        # a real cold first request -- this is measured here instead so
        # that cost is never silently dropped.
        shared_extractor_startup_seconds = time.perf_counter() - warmup_started

        output_dir = output_root / run_id
        filenames = {upload.document_id: upload.original_filename for upload in staged}

        if len(staged) == 1:
            upload = staged[0]
            result = run_document(
                upload.path,
                output_dir=output_dir,
                document_id=upload.document_id,
                review_repo_dir=review_repo_dir,
                extractor=extractor,
            )
            run_out = _single_document_run(run_id, result, filenames, shared_extractor_startup_seconds)
        else:
            batch_result = run_batch(
                [upload.path for upload in staged],
                output_dir=output_dir,
                review_repo_dir=review_repo_dir,
                extractor=extractor,
            )
            run_out = _batch_run(run_id, batch_result, filenames, shared_extractor_startup_seconds)

        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / _RUN_METADATA_FILENAME).write_text(run_out.model_dump_json(indent=2), encoding="utf-8")
        return run_out
    finally:
        _extractor_lock.release()


def get_run(run_id: str, output_root: Path) -> ProcessingRunOut | None:
    path = output_root / run_id / _RUN_METADATA_FILENAME
    if not path.exists():
        return None
    return ProcessingRunOut.model_validate_json(path.read_text(encoding="utf-8"))


def get_document_detail(run_id: str, document_id: str, output_root: Path) -> DocumentDetailOut | None:
    run_out = get_run(run_id, output_root)
    if run_out is None:
        return None
    doc_out = next((doc for doc in run_out.documents if doc.document_id == document_id), None)
    if doc_out is None:
        return None
    canonical = _read_canonical(output_root / run_id / document_id)
    return DocumentDetailOut(**doc_out.model_dump(), canonical=canonical)


def resolve_document_download(run_id: str, document_id: str, artifact: str, output_root: Path) -> Path | None:
    """Resolve a safe on-disk path for a document download, or `None`.

    Only ever serves the fixed `final.json`/`final.csv` filenames for a
    document ID already present in that run's own persisted manifest --
    the caller never supplies a raw filesystem path.
    """

    run_out = get_run(run_id, output_root)
    if run_out is None:
        return None
    doc_out = next((doc for doc in run_out.documents if doc.document_id == document_id), None)
    if doc_out is None or not doc_out.finalized:
        return None
    filename = {"json": "final.json", "csv": "final.csv"}.get(artifact)
    if filename is None:
        return None
    path = output_root / run_id / document_id / filename
    return path if path.exists() else None


def resolve_batch_csv(run_id: str, output_root: Path) -> Path | None:
    run_out = get_run(run_id, output_root)
    if run_out is None or not run_out.aggregate_csv_available:
        return None
    path = output_root / run_id / DEFAULT_AGGREGATE_CSV_NAME
    return path if path.exists() else None


def _read_canonical(document_output_dir: Path) -> dict | None:
    final_path = document_output_dir / "final.json"
    if final_path.exists():
        payload = json.loads(final_path.read_text(encoding="utf-8"))
        return payload.get("document")
    extracted_path = document_output_dir / "extracted.json"
    if extracted_path.exists():
        return json.loads(extracted_path.read_text(encoding="utf-8"))
    return None


def _downloads_for(run_id: str, result: DocumentRunResult) -> dict[str, str]:
    if not result.finalized:
        return {}
    return {
        "json": f"/api/runs/{run_id}/documents/{result.document_id}/final.json",
        "csv": f"/api/runs/{run_id}/documents/{result.document_id}/final.csv",
    }


def _to_document_out(run_id: str, result: DocumentRunResult, filename: str) -> DocumentResultOut:
    return DocumentResultOut(
        document_id=result.document_id,
        filename=filename,
        status=result.status.value,
        route=result.route,
        issue_codes=result.issue_codes,
        review_id=result.review_id,
        finalized=result.finalized,
        error_message=result.error_message,
        model_startup_seconds=result.model_startup_seconds,
        processing_latency_seconds=result.processing_latency_seconds,
        total_duration_seconds=result.total_duration_seconds,
        downloads=_downloads_for(run_id, result),
    )


def _single_document_run(
    run_id: str,
    result: DocumentRunResult,
    filenames: dict[str, str],
    shared_extractor_startup_seconds: float,
) -> ProcessingRunOut:
    doc_out = _to_document_out(run_id, result, filenames[result.document_id])
    return ProcessingRunOut(
        run_id=run_id,
        mode="single",
        documents_total=1,
        accepted=int(result.status is DocumentRunStatus.ACCEPTED),
        needs_review=int(result.status is DocumentRunStatus.NEEDS_REVIEW),
        failed=int(result.status is DocumentRunStatus.FAILED),
        model_startup_seconds=shared_extractor_startup_seconds,
        batch_processing_seconds=None,
        mean_document_latency_seconds=result.processing_latency_seconds,
        median_document_latency_seconds=result.processing_latency_seconds,
        total_duration_seconds=shared_extractor_startup_seconds + result.total_duration_seconds,
        aggregate_csv_available=False,
        aggregate_csv_url=None,
        documents=[doc_out],
    )


def _batch_run(
    run_id: str,
    batch_result: BatchRunResult,
    filenames: dict[str, str],
    shared_extractor_startup_seconds: float,
) -> ProcessingRunOut:
    documents = [_to_document_out(run_id, doc, filenames[doc.document_id]) for doc in batch_result.documents]
    aggregate_available = batch_result.aggregate_csv is not None
    return ProcessingRunOut(
        run_id=run_id,
        mode="batch",
        documents_total=batch_result.documents_total,
        accepted=batch_result.accepted,
        needs_review=batch_result.needs_review,
        failed=batch_result.failed,
        model_startup_seconds=shared_extractor_startup_seconds,
        batch_processing_seconds=batch_result.batch_processing_seconds,
        mean_document_latency_seconds=batch_result.mean_document_latency_seconds,
        median_document_latency_seconds=batch_result.median_document_latency_seconds,
        total_duration_seconds=shared_extractor_startup_seconds + batch_result.total_duration_seconds,
        aggregate_csv_available=aggregate_available,
        aggregate_csv_url=f"/api/runs/{run_id}/batch.csv" if aggregate_available else None,
        documents=documents,
    )
