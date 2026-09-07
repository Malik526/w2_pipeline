# Batch W-2 Runner (Phase 8D.5)

The canonical way to run many arbitrary W-2 files through the complete
current backend workflow from the terminal, reusing one initialized
Pipeline A extractor across the whole batch instead of paying OCR
backend startup (e.g. PaddleOCR model loading) once per file --
closing [`docs/known-limitations.md` #7](known-limitations.md#7-no-batch-export-command).
This does not change extraction, validation, or export behavior: it
builds one extractor, warms it up once, then calls the unmodified
`w2_pipeline.application.run_document.run_document()` once per input
file with that same extractor -- the same production sequence
[`docs/single-document-runner.md`](single-document-runner.md)
documents, run many times over a shared, already-warm backend.

```text
input files
  -> build one Pipeline A extractor (or reuse a caller-supplied one)
  -> extractor.warm_up()                          [once, measured]
  -> for each file: run_document(file, extractor=extractor)
       -> ingestion -> extraction -> validation -> accepted/needs_review/failed
  -> accepted-only aggregate CSV (from each document's own final.json)
  -> batch_summary.json
```

## Quick start

```bash
PYTHONPATH=src python3 -m w2_pipeline.cli.run_batch w2_1.png w2_2.png w2_3.png
PYTHONPATH=src python3 -m w2_pipeline.cli.run_batch --input-dir path/to/w2s/
```

Defaults: `--ocr-backend paddleocr`, `--device gpu`, `--output-dir
output`, `--review-repo-dir data/review`, `--aggregate-csv
batch_finalized.csv` (relative to `--output-dir`).

## Architecture

`w2_pipeline.application.run_batch.run_batch()` is the reusable service
function -- all batch orchestration logic lives there, not in the CLI.
It returns a structured `BatchRunResult` and never lets one document's
runtime failure stop the batch: `run_document()` already never raises
for an ingestion/extraction/OCR failure (it reports
`DocumentRunStatus.FAILED` instead), so failure isolation falls out of
reusing that existing contract rather than needing a second try/except
here. The one thing allowed to raise out of `run_batch()` is the shared
extractor's own `warm_up()`: if the OCR backend itself cannot become
ready, no document in the batch could have processed anyway, so that is
a runtime-unusable condition, not a per-document outcome (the CLI
catches it and exits `1` with a clean message).

```text
run_batch() (w2_pipeline.application.run_batch)
       |
       +---- builds/reuses one PipelineAExtractor, extractor.warm_up()
       |
       +---- run_document() once per input file (w2_pipeline.application.run_document, unmodified)
       |
       +---- w2_pipeline.cli.run_batch (this CLI; thin argparse wrapper)
       |
       +---- future demo/evaluation skill, future web API/UI
```

`extractor=`, when given, is used as-is (its own `warm_up()` is still
called, which is a cheap no-op if it is already warm) -- the seam tests
use to exercise this orchestration without a real OCR backend. Every
real caller (the CLI included) leaves this `None`, so `run_batch()`
builds one from `--ocr-backend`/`--device` via the same
`w2_pipeline.extraction.factory.build_pipeline_a_extractor` the
single-document runner uses.

Unlike `run_document()`, there is no `--format` choice at the batch
level: every document is run with `output_format="both"`, so an
accepted document's `final.json` is always on disk for the aggregate
CSV to read back.

## Shared model lifecycle

A `warm_up()` method was added to the `OcrAdapter` contract
(`w2_pipeline.extraction.ocr_backend`), both backends, and
`ObservationAcquirer`/`PipelineAExtractor` (both delegate down to the
adapter):

- **`PaddleOcrAdapter.warm_up()`** forces the otherwise-lazy
  `PaddleOCR(...)` client construction (which loads its detection/
  recognition models) right now, instead of waiting for the first real
  `extract_image`/`extract_pdf_pages` call. A repeat call is cheap --
  the adapter caches its client -- so calling it again per document
  inside `run_document()` never rebuilds anything.
- **`TesseractOcrAdapter.warm_up()`** only verifies the `tesseract`
  binary is on `PATH`; Tesseract has no persistent client/model to
  preload (each call shells out fresh), so this is a fast readiness
  check, not a real cold-start cost.

`run_batch()` calls `extractor.warm_up()` exactly once, before the
per-document loop, and measures it as `model_startup_seconds`. Every
per-document `run_document()` call inside that loop also calls
`extractor.warm_up()` (that call's own contract, unchanged from the
single-document path) -- but against an already-warm extractor this
costs effectively nothing, so each document's own
`model_startup_seconds` (see below) is near-zero after the first.

A real GPU smoke run's PaddleOCR "Creating model" construction log
appeared exactly twice total (one detection model, one recognition
model) across a six-document batch -- not once per document -- direct
evidence the shared extractor loaded once. See "Real batch smoke run"
in `docs/project-state.md`'s Phase 8D.5 entry for the full numbers.

## Per-document latency definition

Each document's own result (`DocumentRunResult`, also written to that
document's `run_summary.json`) carries three timing fields, defined
identically to the single-document runner
(`docs/single-document-runner.md`'s "Timing fields" section):

- **`model_startup_seconds`** -- OCR backend readiness for *this call*.
  For a batch document (an already-warm shared extractor), this is
  near-zero. For a document run standalone via `w2_pipeline.cli.run_document`,
  this is the real cold-start cost (extractor construction + model
  loading), since nothing warmed it beforehand.
- **`processing_latency_seconds`** -- ingestion through validation and
  either finalization/export or review persistence. This is the number
  that matters for steady-state per-document throughput, and the one a
  batch's `mean_document_latency_seconds`/`median_document_latency_seconds`
  are computed from.
- **`total_duration_seconds`** -- this call's full wall time; always
  >= the other two combined.

Do not read a batch document's `total_duration_seconds` as "how long
this document took to process" -- for the first document in a batch
whose extractor was cold before `run_batch()`'s own warm-up (there
isn't one, since `run_batch()` always warms up first), or for any
document run standalone, `total_duration_seconds` includes model
startup. `processing_latency_seconds` is always the correct per-document
throughput number.

## Batch timing definitions

`BatchRunResult` (also written to `batch_summary.json`) reports three
batch-level timings, each measured once around a distinct phase of
`run_batch()`, never fabricated or estimated:

- **`model_startup_seconds`** -- wall time of the single
  `extractor.warm_up()` call before the per-document loop starts.
- **`batch_processing_seconds`** -- wall time of the entire
  per-document loop (every `run_document()` call, in input order).
- **`total_duration_seconds`** -- this `run_batch()` call's full wall
  time (output directory setup through `batch_summary.json` written).

`mean_document_latency_seconds`/`median_document_latency_seconds` are
computed over every document's `processing_latency_seconds` --
accepted, needs_review, and failed alike, since each is still real
measured processing time for that attempt, not fabricated. A batch
containing an unusually fast failure (e.g. an immediately-missing input
file) will pull these down; that is an honest reflection of what was
measured, not a defect.

## Accepted vs needs-review behavior

Every document remains independently classified, exactly as
`run_document()` already classifies it standalone: `accepted`,
`needs_review`, or `failed`. The batch itself never fails merely
because some documents need review -- a `needs_review` document is this
system correctly routing a document to a human, not a batch error. One
document's runtime failure does not prevent subsequent documents from
being attempted (see "Architecture" above for why).

## Aggregate CSV contract

`output/<--aggregate-csv, default batch_finalized.csv>` contains
exactly one row per **accepted/finalized** document, in the order those
documents were processed -- never a `needs_review` or `failed`
document. Built by reading each accepted document's own already-written
`final.json` back and passing all of them to
`w2_pipeline.downstream.csv_output.export_csv_rows()` -- the same
row-flattening/column-ordering primitive `export_csv()` (the
single-document CSV export) is now built on, so:

- Aggregate CSV columns and per-cell encoding are identical to every
  individual `final.csv`.
- A given document's row in the aggregate CSV is byte-identical (as a
  parsed CSV row) to that same document's own `final.csv`.
- Running the same batch twice produces byte-identical aggregate CSV
  output.

If zero documents are accepted, no aggregate CSV file is written at all
(there is no schema-independent way to produce a header with no
finalized document to derive columns from) and `batch_summary.json`'s
`aggregate_csv` field is `null`.

## Output directory structure

Identical to the single-document runner's per-document layout, plus two
batch-level files directly under `--output-dir`:

```text
output/
  <document_id>/
    extracted.json       # per document, same as single-document runner
    signals.json
    validation.json
    run_summary.json
    final.json            # accepted only
    final.csv             # accepted only
  ...
  batch_finalized.csv     # accepted-only aggregate CSV; absent if zero accepted
  batch_summary.json      # always written
```

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Every document processed without a runtime failure. Accepted and needs_review are both valid outcomes. |
| `1` | At least one document hit a runtime/processing failure, or the shared OCR backend itself could not become ready (no document could have processed). |

Same reasoning as `w2_pipeline.cli.run_document`'s exit codes: a
document correctly routed to a human is this system working as
designed, not a failure, so `needs_review` documents never affect the
batch exit code. Per-document status remains available through
`batch_summary.json` and each document's own `run_summary.json`.

## Machine-readable batch summary

```json
{
  "pipeline_id": "pipeline_a",
  "ocr_backend": "paddleocr",
  "device": "gpu",
  "documents_total": 6,
  "accepted": 4,
  "needs_review": 2,
  "failed": 0,
  "model_startup_seconds": 6.28,
  "batch_processing_seconds": 9.82,
  "total_duration_seconds": 16.10,
  "mean_document_latency_seconds": 1.64,
  "median_document_latency_seconds": 1.42,
  "aggregate_csv": "output/batch_finalized.csv",
  "documents": [
    {
      "status": "accepted",
      "document_id": "...",
      "...": "...full DocumentRunResult, same shape as that document's own run_summary.json"
    }
  ]
}
```

`documents` is the full list of each input's own `DocumentRunResult` in
processing order -- a caller does not need to open every individual
`run_summary.json` separately, though each is still written (at
`output/<document_id>/run_summary.json`) for a caller that only has one
document's ID.

## Optional flags

```text
--input-dir PATH               non-recursive; .png/.jpg/.jpeg/.pdf only; combined with positional files if both given
--output-dir PATH              default: output
--ocr-backend paddleocr|tesseract   default: paddleocr
--device gpu|cpu               default: gpu (PaddleOCR only; ignored for tesseract)
--review-repo-dir PATH         default: data/review
--aggregate-csv NAME           default: batch_finalized.csv (relative to --output-dir)
```

No parser/validator internal tuning parameter is exposed, and no
`--format` flag exists at the batch level (see "Architecture" above) --
this is an operator interface, not an experiment CLI, same convention
`docs/single-document-runner.md` follows.

## Scope

Not built in this phase (tracked as explicit follow-ups, same as
`docs/known-limitations.md` and `docs/project-state.md`'s "Possible
future production work"): a Codex/Claude demo/evaluation skill wrapping
this CLI, and a lightweight frontend calling `run_batch()`/
`run_document()` directly. Both are designed to be buildable against
`run_batch()`, `batch_summary.json`, and each document's own
`run_summary.json` alone -- no private parser/pipeline imports needed.
Documents within one batch are processed sequentially through the one
warm extractor; concurrency/multiprocessing, parallelized Paddle
inference, queues/workers, database persistence, authentication, and a
review-reopen workflow are all explicitly out of scope here, same as
the single-document runner.
