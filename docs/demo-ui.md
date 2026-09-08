# Demo UI (Phase 8D.7)

A local, two-process demo interface over this project's existing
production pipeline: a Next.js/TypeScript frontend and a thin FastAPI
Python backend, both purely presentation/transport -- every actual
processing decision is made by the unmodified
`w2_pipeline.application.run_document.run_document()` /
`w2_pipeline.application.run_batch.run_batch()` application services
the CLIs (`docs/single-document-runner.md`, `docs/batch-runner.md`) and
the agent skill (`skills/run-w2-pipeline/`) already call.

```text
Browser
   |
   v (HTTP)
Next.js/TypeScript frontend  (frontend/)
   |
   v (HTTP, fetch)
FastAPI/Python API           (src/w2_pipeline/api/)
   |
   v (direct Python call)
run_document() / run_batch()  -- unmodified, Phase 8D.4/8D.5
   |
   v
Pipeline A / PaddleOCR -> validation -> accepted/needs_review
```

## Architecture

**Frontend responsibilities** (`frontend/`): file selection (drag/drop
+ picker), upload request, loading state, results table, status
badges, latency display, a document detail panel, review-issue display,
download links. It never interprets OCR/validation internals -- only
the JSON the API already returns.

**Backend responsibilities** (`src/w2_pipeline/api/`): stage uploads
safely, choose `run_document()` (one file) vs `run_batch()` (two or
more) -- always exactly one call per request, never one call per file,
so the shared PaddleOCR extractor's warm-up is never repeated per
document -- map the result to a frontend-oriented JSON shape, and serve
safe, run-scoped file downloads. Nothing here reimplements extraction,
validation, review, finalization, or CSV flattening.

```text
src/w2_pipeline/api/
  app.py       # FastAPI routes only
  service.py   # shared-extractor lifecycle + result mapping
  schemas.py   # response models
  uploads.py   # filename sanitization + safe staging
```

## Shared extractor lifecycle and concurrency

The FastAPI process holds one lazily-built, warmed-once
`PipelineAExtractor` (`service._get_shared_extractor()`), reused across
every request for the life of the process -- the same
build-once/warm-once/reuse pattern `run_batch()` already uses within a
single batch, extended across HTTP requests. A `threading.Lock`
(non-blocking `acquire`) both serializes access to it (only one
request processes at a time; a concurrent request gets `409 Processor
busy`) and gates warm-up (a warm-up failure returns `502 Processing
backend could not initialize` and leaves the extractor unset so a later
request can retry, rather than caching a broken extractor).

Because the shared extractor is already warm by the time
`run_document()`/`run_batch()` are called, *their own* internal
`model_startup_seconds` always reads near-zero from inside a request --
by design, matching Phase 8D.5's semantics. The real one-time cold-start
cost (the first request in a fresh server process) is measured
separately, around `_get_shared_extractor()` itself, and reported as
the *run-level* `model_startup_seconds` in the API response --
confirmed against a real server: first request `model_startup_seconds
≈ 5.6s`, every later request `≈ 0.00001s`, per-document
`processing_latency_seconds` staying in the same ~1.3-2.1s range both
times.

## Run isolation and upload staging

Every `POST /api/process` call gets a fresh `run_id`
(`uuid4().hex`, 32 hex characters). Uploaded files are staged to
`data/ui_uploads/<run_id>/` under a sanitized `document_id` (derived
from the original filename, restricted to `[A-Za-z0-9_-]` --
`w2_pipeline.api.uploads._safe_stem` strips any directory component and
special characters, so a filename like `../../etc/passwd.png` can never
influence the staged path). Uploads are deleted immediately after that
request finishes (success or failure) -- nothing downstream needs the
raw upload after processing.

Each run's outputs land under `output/ui/<run_id>/`, passed as
`output_dir` into `run_document()`/`run_batch()` unmodified, so the
per-document layout is identical to a CLI run
(`extracted.json`/`signals.json`/`validation.json`/`run_summary.json`/
`final.json`/`final.csv`) plus, for a batch, `batch_finalized.csv`. The
API additionally writes `output/ui/<run_id>/ui_run.json` -- the exact
`ProcessingRunOut` response, re-read by `GET /api/runs/{run_id}` and the
document-detail/download routes rather than re-deriving anything.
`data/review/` (the same canonical `FileReviewRepository` location
every other caller uses) holds review records; no second review store
was created.

## API routes

| Route | Purpose |
| --- | --- |
| `GET /api/health` | `{"status": "ok", "supported_extensions": [...]}` -- extensions come directly from `w2_pipeline.ingestion.service.SUPPORTED_EXTENSION_TYPES`, never a second hardcoded list. |
| `POST /api/process` | Multipart `files` field, one or more. One file -> `run_document()`; two or more -> `run_batch()`. Returns a `ProcessingRunOut` (below). |
| `GET /api/runs/{run_id}` | Re-reads that run's persisted `ProcessingRunOut`. |
| `GET /api/runs/{run_id}/documents/{document_id}` | Adds the document's canonical `W2Document` JSON (from `final.json` if finalized, else `extracted.json` if it exists, else `null`) to its `DocumentResultOut`. |
| `GET /api/runs/{run_id}/documents/{document_id}/final.json` / `.../final.csv` | Serves that document's own export file -- only if `finalized` is true for a document ID present in that run's manifest; `404` otherwise. |
| `GET /api/runs/{run_id}/batch.csv` | Serves the run's aggregate `batch_finalized.csv` -- only if at least one document was accepted; `404` otherwise. |

**Download safety**: `run_id` must match `^[0-9a-f]{32}$` and
`document_id` must match `^[A-Za-z0-9_-]{1,80}$` before either ever
reaches a filesystem path; a `document_id` must additionally already
exist in that run's own persisted manifest. Only the two fixed
filenames `final.json`/`final.csv` are ever served -- the client never
supplies a raw path or arbitrary artifact name.

### Response shape

Wire format is snake_case, matching this project's existing
`run_summary.json`/`batch_summary.json` convention (no camelCase
translation layer):

```json
{
  "run_id": "…",
  "mode": "batch",
  "documents_total": 6,
  "accepted": 4,
  "needs_review": 2,
  "failed": 0,
  "model_startup_seconds": 5.56,
  "batch_processing_seconds": 8.42,
  "mean_document_latency_seconds": 1.4,
  "median_document_latency_seconds": 1.36,
  "total_duration_seconds": 8.42,
  "aggregate_csv_available": true,
  "aggregate_csv_url": "/api/runs/…/batch.csv",
  "documents": [
    {
      "document_id": "…",
      "filename": "w2_001.png",
      "status": "accepted",
      "issue_codes": [],
      "review_id": null,
      "finalized": true,
      "model_startup_seconds": 0.00001,
      "processing_latency_seconds": 1.67,
      "total_duration_seconds": 1.67,
      "downloads": { "json": "/api/runs/…/documents/…/final.json", "csv": "…/final.csv" }
    }
  ]
}
```

For a single-document run, `documents_total` is `1` and
`mean_document_latency_seconds`/`median_document_latency_seconds` both
equal that one document's `processing_latency_seconds`;
`batch_processing_seconds` is `null`.

## Status and timing semantics

Exactly three statuses -- `accepted`, `needs_review`, `failed` -- never
presented as two (`needs_review` is a successful outcome: the system
correctly routed an ambiguous document to a human, not an error).
`StatusBadge` (frontend) pairs an icon with the label so status never
relies on color alone.

Timing fields keep the exact Phase 8D.5 names and meaning
(`docs/batch-runner.md`): `processing_latency_seconds` is "how long did
this document actually take," `model_startup_seconds` is backend
readiness cost, `total_duration_seconds` is wall time and is **never**
labeled "latency" anywhere in the UI.

## Review behavior

A `needs_review` document's row/detail view shows its issue codes,
review ID, and "Finalization blocked until review is resolved." No
correction UI exists -- the existing `review/cli.py` workflow
(`docs/operator-walkthrough.md`) remains the only way to correct and
resolve a review; building that into this UI was explicitly out of
scope for this phase (a correction form invites reimplementing
field-specific business logic in TypeScript, which the whole
architecture is designed to avoid).

## Running it locally

Two processes, from the repository root:

```bash
# Backend (needs the optional `api` extra: fastapi, uvicorn, python-multipart)
PYTHONPATH=src python3 -m uvicorn w2_pipeline.api.app:app --reload --port 8000

# Frontend
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
```

Open `http://localhost:3000`. FastAPI's CORS is configured for exactly
that origin (`http://localhost:3000`) -- not a wildcard.

## Known limitations

- Local two-process demo setup; no auth, no multi-tenant isolation, no
  production deployment story.
- Synchronous request/response processing -- a batch's full run time is
  one HTTP request; no progress streaming (acceptable for a demo; a
  large batch simply takes longer to respond).
- One shared extractor, sequential access -- concurrent UI requests
  queue via a `409`, never parallel GPU inference.
- Filesystem storage only (uploads, per-run output, review records) --
  no database.
- No in-UI review correction -- `review/cli.py` remains the correction
  path.
- Same synthetic Symage benchmark/demo documents as the rest of this
  project; no real taxpayer data.

None of these are extraction/validation defects -- they are this
phase's explicitly scoped demo/operator-interface boundaries, same
convention as `docs/known-limitations.md`.
