# Single-Document Production Runner (Phase 8D.4)

The canonical way to run one arbitrary W-2 file through the complete
current backend workflow from the terminal, closing
[`docs/known-limitations.md` #6](known-limitations.md#6-no-single-document-pipeline-execution-cli).
This does not change extraction, validation, or export behavior -- it
orchestrates the exact same production components the rest of this
project already uses (`PipelineAExtractor`, `validate_w2_document`,
`finalize_document`, `export_json`/`export_csv`, `start_review`,
`FileReviewRepository`).

```text
W-2 file
  -> ingestion (IngestionService)
  -> Pipeline A extraction (PaddleOCR by default)
  -> canonical W2Document + extraction evidence (ExtractionResult)
  -> full-evidence ExtractionSignals (w2_pipeline.extraction.signals)
  -> validation (validate_w2_document)
  -> accepted -> finalize_document -> export_json / export_csv
     needs_review -> start_review -> FileReviewRepository
```

## Quick start

```bash
PYTHONPATH=src python3 -m w2_pipeline.cli.run_document path/to/w2.png
```

Defaults: `--ocr-backend paddleocr`, `--device gpu`, `--format both`,
`--output-dir output`, `--review-repo-dir data/review`, and
`--document-id` defaulting to the input file's stem (so output paths
are deterministic without having to pass an ID explicitly).

## Architecture

`w2_pipeline.application.run_document.run_document()` is the one
reusable service function -- all orchestration logic lives there, not
in the CLI. It returns a structured `DocumentRunResult`
(`accepted` / `needs_review` / `failed`), never raises for an
ingestion/extraction/OCR failure, and takes an optional `extractor=`
override used by tests (and available to any future caller) to swap in
a different `PipelineAExtractor`-shaped object without touching the
orchestration itself.

```text
run_document() (w2_pipeline.application.run_document)
       |
       +---- w2_pipeline.cli.run_document (this CLI; thin argparse wrapper)
       |
       +---- w2_pipeline.application.run_batch (Phase 8D.5 batch runner)
       |
       +---- future web API/UI
```

Nothing here is new pipeline logic:

- **Extractor construction**: `w2_pipeline.extraction.factory.build_pipeline_a_extractor`
  (extracted Phase 8D.4 from `run_pipeline_a.py`'s former private
  `_pipeline_a_extractor`/`_build_ocr_adapter`; `run_pipeline_a.py` now
  calls the same shared factory instead of keeping its own copy).
- **Extraction**: `PipelineAExtractor.extract_ingested`, unchanged.
- **Signal construction**: `w2_pipeline.extraction.signals.build_extraction_signals`
  (extracted Phase 8D.4 from
  `run_address_evidence_validator_effectiveness.py`'s former private
  `_signals_for_result` -- the exact full-evidence
  `ExtractionResult` -> `ExtractionSignals` mapping, now shared instead
  of duplicated).
- **Validation/finalize/export/review**: `validate_w2_document`,
  `finalize_document`, `export_json`, `export_csv`, `start_review`,
  `FileReviewRepository`, all unchanged.

## Accepted result

```bash
PYTHONPATH=src python3 -m w2_pipeline.cli.run_document \
  data/evaluation/external/symage-synthetic-us-forms-preview-final/documents/symage_900001-irs_w2_single_page_2026-p0_external_clean_render.png
```

```text
W-2 processing complete

Document: symage_900001-irs_w2_single_page_2026-p0_external_clean_render
Pipeline: Pipeline A / paddleocr
Validation: ACCEPTED
Issues: 0
JSON: output/symage_900001-.../final.json
CSV: output/symage_900001-.../final.csv

Model startup:   6.28s
Document latency: 1.79s
Total wall time: 8.07s
```

Exit code `0`. `final.json`/`final.csv` are written; `run_summary.json`
has `"finalized": true`.

## Needs-review result

```bash
PYTHONPATH=src python3 -m w2_pipeline.cli.run_document \
  data/evaluation/external/symage-synthetic-us-forms-preview-final/documents/symage_900021-irs_w2_single_page_2026-p0_rotated.png
```

```text
W-2 processing complete

Document: symage_900021-irs_w2_single_page_2026-p0_rotated
Pipeline: Pipeline A / paddleocr
Validation: NEEDS REVIEW

Issues:
- employer_address_extraction_incomplete
- employee_address_extraction_incomplete

Review ID: <uuid>
Finalization: BLOCKED

Model startup:   5.52s
Document latency: 1.38s
Total wall time: 6.90s
```

Exit code `2`. No `final.json`/`final.csv` is written -- `finalize_document`
is never called on a `needs_review` document, same invariant the rest
of this project already enforces. A `ReviewRecord` is persisted to
`--review-repo-dir` (default `data/review/<review_id>.json`) via the
same `FileReviewRepository`/`start_review` API `review/cli.py` uses; the
rest of the review workflow (`review-correct`, `review-revalidate`,
`export-review`) works exactly as documented in
[`docs/operator-walkthrough.md`](operator-walkthrough.md).

## Output directory structure

One subdirectory per document ID under `--output-dir` (default `output/`):

```text
output/
  <document_id>/
    extracted.json     # canonical W2Document (pre-validation)
    signals.json        # full-evidence ExtractionSignals actually used to validate
    validation.json     # ValidationResult
    run_summary.json     # machine-readable outcome (see below); always written
    final.json           # accepted only
    final.csv             # accepted only
```

`final.json`/`final.csv` are never written for a `needs_review` or
`failed` run. `run_summary.json` is always written once the document ID
is known (even on a runtime failure), so a caller can rely on its
presence.

`--document-id` defaults to the input file's stem, so re-running the
same file reuses the same subdirectory (idempotent overwrite of that
document's own files); a different input file gets a different
subdirectory, so unrelated runs never collide.

### `run_summary.json`

```json
{
  "status": "accepted",
  "document_id": "symage_900001-irs_w2_single_page_2026-p0_external_clean_render",
  "input_file": "data/evaluation/.../symage_900001-....png",
  "output_dir": "output/symage_900001-...",
  "pipeline_id": "pipeline_a",
  "ocr_backend": "paddleocr",
  "route": "ocr",
  "validation_status": "accepted",
  "issue_codes": [],
  "review_id": null,
  "finalized": true,
  "outputs": {
    "json": "output/symage_900001-.../final.json",
    "csv": "output/symage_900001-.../final.csv"
  },
  "model_startup_seconds": 6.28,
  "processing_latency_seconds": 1.79,
  "total_duration_seconds": 8.07,
  "error_message": null
}
```

For a needs-review run: `"status": "needs_review"`, `"finalized": false`,
`"outputs": {}`, `"review_id"` set, `"issue_codes"` populated. For a
runtime failure: `"status": "failed"`, `"validation_status": null`,
`"route": null`, `"error_message"` set, `"outputs": {}`.

### Timing fields (Phase 8D.5)

`model_startup_seconds` covers building/warming the OCR backend --
calling the extractor's `warm_up()`, which forces PaddleOCR's otherwise-
lazy client/model construction now instead of on the first real
prediction. It is near-zero when a caller passes in an already-warm
`extractor=` (as the batch runner's shared extractor is, after its own
one-time warm-up), since a repeat `warm_up()` call is cheap.
`processing_latency_seconds` covers everything after that: ingestion,
extraction/OCR, signal construction, validation, and review creation or
finalization/export -- the number that matters for steady-state
per-document throughput. `total_duration_seconds` is this call's full
wall time and is always >= the other two combined. This replaces the
single ambiguous `duration_seconds` this document previously described,
which conflated cold-start model loading with actual per-document work
(see [`docs/batch-runner.md`](batch-runner.md) for why that distinction
matters once documents are processed in a batch).

No confidence/accuracy value is ever fabricated into this file --
consistent with this project's existing "no global calibrated OCR
confidence" decision (`docs/known-limitations.md` #5).

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Accepted; requested downstream output (`--format`) was produced. |
| `2` | Processed successfully but needs human review -- **not** a failure. |
| `1` | Processing/runtime/configuration failure (bad input path, unsupported file type, an ingestion/OCR/parser exception). No trusted downstream output is produced. |

The distinction between `2` and `1` is deliberate: a document correctly
routed to a human is this system working as designed, not breaking. A
future batch runner or skill can and should treat `needs_review` and
`failed` differently based on the exit code alone.

## Evidence preservation (why this exists)

The runner must validate with the same real evidence the extraction
just produced -- never `route="ocr"` with the evidence left out, which
is exactly the gap Phase 8D.2 found and fixed in `review/cli.py` (see
[`docs/operator-walkthrough.md`](operator-walkthrough.md#the---signals-json-flag-phase-8d2-fix)).
`run_document()` never reconstructs `route`/evidence from scratch or
takes them as separate CLI flags -- it always builds `ExtractionSignals`
directly from the same `ExtractionResult` extraction just returned, via
`w2_pipeline.extraction.signals.build_extraction_signals`. See
`tests/application/test_run_document.py::test_regression_full_evidence_is_threaded_not_just_route`
for the regression test proving this (an OCR-route result with full
evidence is accepted; the identical route with the evidence stripped
out needs review).

## Optional OCR/device flags

```text
--output-dir PATH        default: output
--format json|csv|both    default: both
--document-id ID           default: input file's stem
--ocr-backend paddleocr|tesseract   default: paddleocr
--device gpu|cpu                     default: gpu (PaddleOCR only; ignored for tesseract)
--review-repo-dir PATH               default: data/review
```

No parser/validator internal tuning parameter is exposed -- this is an
operator interface, not an experiment CLI (see `run_pipeline_a.py` for
that).

## How to continue a review

A `needs_review` run's `review_id` (printed and in `run_summary.json`)
plugs directly into the existing review workflow CLI -- no new command
is needed:

```bash
PYTHONPATH=src python3 -m w2_pipeline.review.cli review-correct <review_id> \
  --repo-dir data/review --field-path employee.address.city --new-value '"Colorado Springs"'
PYTHONPATH=src python3 -m w2_pipeline.review.cli review-revalidate <review_id> --repo-dir data/review
PYTHONPATH=src python3 -m w2_pipeline.review.cli export-review <review_id> --repo-dir data/review --format both
```

See [`docs/operator-walkthrough.md`](operator-walkthrough.md) Path B for
the full worked example.

## Performance

Each CLI invocation is a fresh process, so PaddleOCR's model
initialization (~5-9s, one-time per process on this machine) is paid on
every run, reported explicitly as `model_startup_seconds` -- there is no
long-running server here to amortize it across documents by itself.
Once an extractor is warm -- inside this same process, via the batch
runner ([`docs/batch-runner.md`](batch-runner.md)), which builds one
extractor and warms it up once before reusing it for every document --
`model_startup_seconds` drops to near-zero for every document after the
first, and steady-state PaddleOCR GPU `processing_latency_seconds`
remains ~1.2-2.5s/document, unchanged by this phase -- this runner does
not introduce any additional per-document overhead beyond writing five
small JSON/CSV files.

## Scope

Not built in this phase (tracked as explicit follow-ups, same as
`docs/known-limitations.md`): a frontend/UI over the batch runner.
Batch execution over many files and a combined multi-document CSV were
Phase 8D.5's addition -- [`docs/batch-runner.md`](batch-runner.md); an
agent skill wrapping both CLIs was Phase 8D.6's addition --
[`skills/run-w2-pipeline/SKILL.md`](../skills/run-w2-pipeline/SKILL.md).
This CLI, `run_document()`, and the batch runner are designed so a
future UI can call `run_document()`/`run_batch()` directly (or, for a
CLI, drive them by exit code + `run_summary.json`/`batch_summary.json`
-- never by scraping terminal text) once built.
