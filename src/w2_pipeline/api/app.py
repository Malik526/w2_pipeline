"""FastAPI transport layer for the Next.js demo UI (Phase 8D.7).

    PYTHONPATH=src python3 -m uvicorn w2_pipeline.api.app:app --reload --port 8000

A thin adapter over `w2_pipeline.application.run_document.run_document()`
and `w2_pipeline.application.run_batch.run_batch()` -- the same
application services the CLIs and the agent skill already call. This
module contains no extraction/validation/review/export logic: it stages
uploads (`w2_pipeline.api.uploads`), delegates processing and the
shared-extractor lifecycle to `w2_pipeline.api.service`, and exposes the
result as JSON plus a small set of safe file-download routes.

See `docs/demo-ui.md` for the full route/response contract.
"""

from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from w2_pipeline.api import service
from w2_pipeline.api.schemas import DocumentDetailOut, ErrorOut, ProcessingRunOut
from w2_pipeline.api.uploads import UnsupportedUploadError, stage_uploads, supported_extensions

UPLOADS_ROOT = Path("data/ui_uploads")
OUTPUT_ROOT = Path("output/ui")
REVIEW_REPO_DIR = Path("data/review")

_RUN_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_DOCUMENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")

app = FastAPI(title="W-2 Pipeline Demo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "supported_extensions": list(supported_extensions())}


@app.post(
    "/api/process",
    response_model=ProcessingRunOut,
    responses={400: {"model": ErrorOut}, 409: {"model": ErrorOut}, 502: {"model": ErrorOut}},
)
def process(files: list[UploadFile] = File(...)) -> ProcessingRunOut:
    """One file -> `run_document()`; two or more -> `run_batch()` -- never
    one request per file, so the shared extractor is only ever warmed
    once per call."""

    if not files:
        raise HTTPException(status_code=400, detail="No files were uploaded.")

    run_id = uuid.uuid4().hex
    uploads = [(file.filename or "upload", file.file.read()) for file in files]
    upload_dir = UPLOADS_ROOT / run_id

    try:
        staged = stage_uploads(uploads, destination_dir=upload_dir)
    except UnsupportedUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        return service.process_uploads(
            staged, run_id=run_id, output_root=OUTPUT_ROOT, review_repo_dir=REVIEW_REPO_DIR
        )
    except service.ProcessorBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except service.ProcessorUnavailableError:
        raise HTTPException(status_code=502, detail="Processing backend could not initialize.") from None
    finally:
        # Uploaded bytes are only ever needed for the duration of this
        # request -- everything downstream (extracted/validated/final
        # data) already lives under output_root, so staged uploads are
        # removed immediately rather than accumulating across requests.
        shutil.rmtree(upload_dir, ignore_errors=True)


@app.get("/api/runs/{run_id}", response_model=ProcessingRunOut, responses={404: {"model": ErrorOut}})
def get_run(run_id: str) -> ProcessingRunOut:
    _validate_run_id(run_id)
    run_out = service.get_run(run_id, OUTPUT_ROOT)
    if run_out is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    return run_out


@app.get(
    "/api/runs/{run_id}/documents/{document_id}",
    response_model=DocumentDetailOut,
    responses={404: {"model": ErrorOut}},
)
def get_document(run_id: str, document_id: str) -> DocumentDetailOut:
    _validate_run_id(run_id)
    _validate_document_id(document_id)
    detail = service.get_document_detail(run_id, document_id, OUTPUT_ROOT)
    if detail is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return detail


@app.get("/api/runs/{run_id}/documents/{document_id}/final.json")
def download_document_json(run_id: str, document_id: str) -> FileResponse:
    return _resolve_document_download(run_id, document_id, "json")


@app.get("/api/runs/{run_id}/documents/{document_id}/final.csv")
def download_document_csv(run_id: str, document_id: str) -> FileResponse:
    return _resolve_document_download(run_id, document_id, "csv")


@app.get("/api/runs/{run_id}/batch.csv")
def download_batch_csv(run_id: str) -> FileResponse:
    _validate_run_id(run_id)
    path = service.resolve_batch_csv(run_id, OUTPUT_ROOT)
    if path is None:
        raise HTTPException(status_code=404, detail="No finalized aggregate CSV is available for this run.")
    return FileResponse(path, filename="batch_finalized.csv")


def _resolve_document_download(run_id: str, document_id: str, artifact: str) -> FileResponse:
    _validate_run_id(run_id)
    _validate_document_id(document_id)
    path = service.resolve_document_download(run_id, document_id, artifact, OUTPUT_ROOT)
    if path is None:
        raise HTTPException(status_code=404, detail="Requested output is not available for this document.")
    return FileResponse(path, filename=path.name)


def _validate_run_id(run_id: str) -> None:
    if not _RUN_ID_RE.match(run_id):
        raise HTTPException(status_code=400, detail="Invalid run ID.")


def _validate_document_id(document_id: str) -> None:
    if not _DOCUMENT_ID_RE.match(document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID.")
