---
name: run-w2-pipeline
description: Use when the user asks to run, execute, or process one or more W-2 documents through this project's production pipeline agentically — e.g. "run the W-2 pipeline on this file", "run these six W-2s as a batch", "run a mixed demo batch", "run two known review cases", "run this with Tesseract instead of Paddle". Not for extraction/validation/parser development, benchmark experiments (see run-pipeline-a-extraction-experiment), or review correction workflows.
---

# Run W-2 Pipeline

Thin orchestration over this project's existing canonical entry points. This
skill contains **no extraction, validation, review, export, or benchmark
logic of its own** — it only selects input files, invokes
`w2_pipeline.cli.run_document` or `w2_pipeline.cli.run_batch`, reads the
machine-readable result those commands already produce, and summarizes it.

```text
agent request
    -> select files / execution mode
    -> canonical CLI (run_document or run_batch)
    -> run_summary.json / batch_summary.json
    -> summarize
```

Full contracts, if you need more than this skill provides:

- `docs/single-document-runner.md` — single-document contract, exit codes,
  `run_summary.json` schema, timing-field definitions.
- `docs/batch-runner.md` — batch contract, exit codes, `batch_summary.json`
  schema, aggregate CSV contract, shared-extractor lifecycle.
- `docs/operator-walkthrough.md` — the review-correction workflow (only
  relevant if the user separately asks to correct a `needs_review` document
  after this skill's run — see "Review behavior" below).

## Preconditions

Run every command from the repository root (`~/w2_pipeline`) with
`PYTHONPATH=src`:

```bash
PYTHONPATH=src python3 -m w2_pipeline.cli.run_document ...
PYTHONPATH=src python3 -m w2_pipeline.cli.run_batch ...
```

Do not `pip install`, do not touch the system/user Python environment, and do
not attempt to "fix" the environment as part of a normal run. If a command
fails to import the project (`ModuleNotFoundError: w2_pipeline...`), that
means `PYTHONPATH=src` was omitted or the command was run from the wrong
directory — report this plainly and stop; do not install packages to work
around it.

## Supported modes

**Mode A — single document.** The user names one explicit file.
**Mode B — explicit batch.** The user names multiple files or a directory.
**Mode C — benchmark demo selection.** The user asks for examples by outcome
("3 clean W-2s", "2 that needed review", "a mixed demo batch") rather than
naming files. This mode is for demonstration/workflow verification, never for
model tuning — never adjust thresholds, parser behavior, or OCR configuration
to change which documents land in which bucket.

Do not run six documents because the user asked for one, and do not invoke
the single-document CLI in a loop when the user asked for a batch — batch
mode exists specifically to reuse one warm PaddleOCR runtime across
documents; a shell loop around `run_document` defeats that entirely.

## Canonical commands

Single document (defaults: PaddleOCR, GPU, JSON+CSV — do not override unless
the user's request requires it):

```bash
PYTHONPATH=src python3 -m w2_pipeline.cli.run_document <INPUT_FILE>
```

Batch (positional files, and/or a directory):

```bash
PYTHONPATH=src python3 -m w2_pipeline.cli.run_batch <FILE_1> <FILE_2> ...
PYTHONPATH=src python3 -m w2_pipeline.cli.run_batch --input-dir <DIRECTORY>
```

Only pass `--ocr-backend`/`--device`/`--output-dir`/`--review-repo-dir` when
the user's request actually requires a non-default value (see "Optional
backend overrides" below). Never pass parser/validator tuning flags — none
exist on either CLI, and that is intentional (see `docs/batch-runner.md`
"Scope").

## Result interpretation — machine-readable output is authoritative

Never infer success/failure from terminal prose. Read the JSON artifact each
command already writes:

| Mode | Authoritative file |
| --- | --- |
| Single document | `output/<document_id>/run_summary.json` |
| Batch (aggregate) | `output/batch_summary.json` |
| Batch (per document, if more detail is needed) | `output/<document_id>/run_summary.json` |

Exit codes confirm *that* execution finished in a given state; they are not a
substitute for reading the JSON when you need issue codes, review IDs, or
timings.

**Single-document exit contract**: `0` accepted, `2` needs_review, `1`
runtime/configuration failure.
**Batch exit contract**: `0` = no document hit a runtime failure (a batch
containing `needs_review` documents can still exit `0`); `1` = at least one
document failed, or the shared OCR backend itself could not start.

`needs_review` is a **successful** pipeline outcome — the system correctly
routed an ambiguous document to a human. Never describe it as a crash,
extraction failure, or system failure. Say: "Processed successfully and
routed to human review," not "failed to process."

## Single-document workflow

1. Run the canonical command above.
2. Read `output/<document_id>/run_summary.json`.
3. Summarize:

```text
Document:          <document_id>
Status:             accepted | needs_review | failed
Pipeline/backend:   pipeline_a / <ocr_backend>
Issue codes:        <issue_codes, if any>
Review ID:          <review_id, if needs_review>
Model startup:      <model_startup_seconds>s
Document latency:   <processing_latency_seconds>s
Total wall time:    <total_duration_seconds>s
Final JSON:         <outputs.json, if accepted>
Final CSV:          <outputs.csv, if accepted>
```

For `needs_review`, add `Finalization: blocked` and do not mention
JSON/CSV output paths (`finalize_document` was never called — see
`docs/single-document-runner.md`). Do not print the full `extracted.json`/
`final.json` contents unless the user explicitly asks for the extracted
data.

## Batch workflow

1. Resolve input files (explicit paths, `--input-dir`, or Mode C selection
   below).
2. Run the canonical batch command.
3. Read `output/batch_summary.json`.
4. Summarize the aggregate first:

```text
Documents total:     <documents_total>
Accepted:             <accepted>
Needs review:          <needs_review>
Failed:                 <failed>

Model startup:           <model_startup_seconds>s
Mean doc latency:         <mean_document_latency_seconds>s
Median doc latency:        <median_document_latency_seconds>s
Batch processing:           <batch_processing_seconds>s
Total wall time:              <total_duration_seconds>s

Aggregate CSV:                  <aggregate_csv, or "none (0 accepted)">
```

5. Then a concise per-document line for each entry in `documents`:

```text
<document_id> | <status> | <processing_latency_seconds>s | <issue codes or review ID, if any>
```

Do not dump every field of every document's full `DocumentRunResult` unless
asked — the per-document JSON is already on disk at
`output/<document_id>/run_summary.json` for anyone who needs more.

## Timing semantics

Report the fields exactly as the application layer defines and names them —
never recompute timings from shell timestamps, and never call
`total_duration_seconds` "latency":

- `model_startup_seconds` — OCR backend readiness for that call (near-zero
  once an extractor is warm, as every document after the first is in a
  batch).
- `processing_latency_seconds` — the actual per-document throughput number
  (ingestion through validation and finalize/export or review persistence).
  This is what "document latency" means in this project.
- `total_duration_seconds` — full wall time; always >= the other two
  combined. This is wall time, not a per-document processing figure.

Batch adds `batch_processing_seconds` (the whole per-document loop) and
mean/median `processing_latency_seconds` across all attempted documents.

## Benchmark/demo selection rules (Mode C)

Selection must be deterministic and drawn from a **committed** result
artifact — never guessed from filenames, and never re-run against the
benchmark harness to manufacture a classification.

Authoritative source: `data/evaluation/results/phase8d1b_validator_rows.jsonl`
(the most recent full 600-document/variant validation-status result,
matching the current production `validate_w2_document` rules — same file
Phase 8D.1B's own validator-effectiveness work used). Each row has
`document_id`, `variant_id`, `validation_status` (`accepted`/`needs_review`).
Resolve a `(document_id, variant_id)` pair to an actual file path via
`data/evaluation/external/symage-synthetic-us-forms-preview-final/manifest.jsonl`
(its `sample_id`+`variant_id` join to `document_path`, relative to that
manifest's own directory) — do not hand-construct filenames.

Deterministic selection snippet (adjust `status`/`variant_id`/`n` per
request; never introduces randomness unless the user explicitly says
"random"):

```bash
PYTHONPATH=src python3 - <<'PY'
import json
from pathlib import Path

results = [json.loads(l) for l in open("data/evaluation/results/phase8d1b_validator_rows.jsonl")]
manifest_path = Path("data/evaluation/external/symage-synthetic-us-forms-preview-final/manifest.jsonl")
manifest = {(r["sample_id"], r["variant_id"]): r["document_path"] for r in (json.loads(l) for l in manifest_path.open())}

def select(status: str, variant_id: str, n: int) -> list[str]:
    ids = sorted({r["document_id"] for r in results if r["validation_status"] == status and r["variant_id"] == variant_id})
    return [str(manifest_path.parent / manifest[(doc_id, variant_id)]) for doc_id in ids[:n]]

for path in select("accepted", "external_clean_render", 4) + select("needs_review", "rotated_png", 2):
    print(path)
PY
```

Rules:

- Stable sort by `document_id`, take the first N — same selection every time
  for the same request.
- If the user explicitly says "random", use a logged seed, report the seed,
  and record the selected paths in your output so the run is reproducible
  after the fact.
- The committed row only reflects a **prior** benchmark run. Report the
  *current* run's actual outcome independently — if `run_summary.json` says
  something different from what the committed row predicted, report that
  discrepancy explicitly rather than silently trusting (or overriding
  toward) the historical label.

### Default mixed demo

When the user asks for "a demo batch," "a mixed example," or "a
representative workflow run" without more specifics, use this exact set
(the same six documents Phase 8D.5's own real batch smoke test used — 4
known accepted, 2 known needs_review):

```text
data/evaluation/external/symage-synthetic-us-forms-preview-final/documents/symage_900001-irs_w2_single_page_2026-p0_external_clean_render.png
data/evaluation/external/symage-synthetic-us-forms-preview-final/documents/symage_900002-irs_w2_single_page_2026-p0_external_clean_render.png
data/evaluation/external/symage-synthetic-us-forms-preview-final/documents/symage_900003-irs_w2_single_page_2026-p0_external_clean_render.png
data/evaluation/external/symage-synthetic-us-forms-preview-final/documents/symage_900004-irs_w2_single_page_2026-p0_external_clean_render.png
data/evaluation/external/symage-synthetic-us-forms-preview-final/documents/symage_900000-irs_w2_single_page_2026-p0_rotated.png
data/evaluation/external/symage-synthetic-us-forms-preview-final/documents/symage_900021-irs_w2_single_page_2026-p0_rotated.png
```

## Review behavior

When a document comes back `needs_review`: report issue codes, the review
ID, and that finalization is blocked. Stop there. Do **not** automatically
apply corrections, fabricate corrected values, or auto-resolve the review —
this skill only runs the pipeline, it does not perform review workflow. If
the user separately and explicitly asks to correct fields, that is a
different task using the documented `review/cli.py` workflow
(`docs/operator-walkthrough.md`), not this skill.

## Failure handling

On a runtime/configuration failure (`status: failed` / batch exit `1`),
report: which mode was used, which document(s) were affected, the exit
code, the `error_message` from the JSON, and — for a batch — which other
documents still completed successfully (failure isolation is a guaranteed
batch property; see `docs/batch-runner.md`).

Do not retry repeatedly, switch OCR backend, change device, or otherwise
alter configuration automatically to "fix" a failure. One retry is
acceptable only for an obviously transient issue (e.g. a filesystem hiccup)
and must be reported as a retry, not silently absorbed.

## Optional backend overrides

Only when the user explicitly asks (e.g. "run this with Tesseract", "run
Paddle on CPU"):

```text
--ocr-backend tesseract
--device cpu
```

Otherwise stay on the production defaults (PaddleOCR + GPU). Never
auto-select or cross-check between backends.

## Scope guardrails

Do not, as part of running this skill:

- Import parser internals, inspect OCR observations, call validation rules,
  build `FinalizedW2`, or flatten CSV output directly — always go through
  `run_document()`/`run_batch()`.
- Modify source code, validation thresholds, parser configuration, benchmark
  annotations, ground truth, or committed evaluation results.
- Delete or overwrite `output/`/`data/review/` contents (`rm -rf` or
  similar) — let the runner's existing deterministic per-document-ID
  overwrite behavior handle re-runs.
- Install packages or otherwise modify the Python environment.
- Auto-correct or auto-resolve a `needs_review` document.

This skill is operational, not developmental. If a request requires
changing pipeline behavior, stop and say this needs its own engineering
task, not a pipeline run.

## Example agent requests

```text
Run the W-2 pipeline on data/.../symage_900001-...png
```

```text
Run these four W-2s as a batch and summarize latency.
```

```text
Run a mixed demo batch using 3 previously accepted and 3 previously
needs-review benchmark documents.
```

```text
Run two known rotated review cases.
```

```text
Run this W-2 with Tesseract instead of Paddle.
```
