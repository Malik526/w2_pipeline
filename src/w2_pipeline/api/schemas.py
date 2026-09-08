"""Response models for the demo UI API.

These are deliberately a thinner, frontend-oriented view over
`DocumentRunResult`/`BatchRunResult` (`w2_pipeline.application.*`) --
never a second implementation of what those already compute. Wire
casing matches this project's existing `run_summary.json`/
`batch_summary.json` convention (snake_case) rather than introducing a
camelCase translation layer solely for the frontend.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DocumentResultOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    filename: str
    status: str
    route: str | None = None
    issue_codes: list[str] = []
    review_id: str | None = None
    finalized: bool
    error_message: str | None = None
    model_startup_seconds: float
    processing_latency_seconds: float
    total_duration_seconds: float
    downloads: dict[str, str] = {}


class DocumentDetailOut(DocumentResultOut):
    canonical: dict | None = None


class ProcessingRunOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    mode: str
    documents_total: int
    accepted: int
    needs_review: int
    failed: int
    model_startup_seconds: float
    batch_processing_seconds: float | None = None
    mean_document_latency_seconds: float
    median_document_latency_seconds: float
    total_duration_seconds: float
    aggregate_csv_available: bool
    aggregate_csv_url: str | None = None
    documents: list[DocumentResultOut]


class ErrorOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str
