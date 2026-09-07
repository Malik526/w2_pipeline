# W-2 Automation Platform

A backend system that takes a completed individual W-2 tax form (PDF or
image), extracts its data into a structured, typed representation,
automatically judges whether the result is safe to trust, routes
anything uncertain to a human for a quick correction, and produces a
clean downstream JSON/CSV artifact -- end to end, proven by running two
real documents through the entire pipeline with the actual operator
commands.

**Status: backend complete and frozen for take-home delivery (Phase 8D.3).**
See [`docs/project-state.md`](docs/project-state.md) for the full phase
history.

## What it does

An accounting/tax-preparation firm receives many client W-2s and needs
their data (SSN, employer EIN, wages, withholding, etc.) turned into
structured records quickly and safely enough to use in downstream
tax-preparation workflows, without a human re-keying every field by
hand -- while still catching cases an automated system got wrong.

```text
INPUT:  one completed individual W-2 document (PDF or image)
SYSTEM: ingestion -> extraction -> canonical W2Document -> validation
        -> accepted OR needs_review -> human correction if needed ->
        revalidation -> finalization -> JSON/CSV downstream output
OUTPUT: validated canonical W-2 data ready for downstream
        tax-preparation systems
```

Explicitly **not** built: payroll/W-2 generation, tax calculation, Form
1040 preparation, IRS e-file transmission, a production GUI, or a
broad document-type platform beyond the 2026 W-2. Full boundary:
[`docs/final-architecture.md`](docs/final-architecture.md).

## Architecture

```text
W-2 PDF / image
        |
        v
Ingestion + route classification
        |
        v
Extraction  (Pipeline A: OCR + deterministic parser  |  Pipeline B: VLM, evaluated, not selected)
        |
        v
Canonical W2Document  +  extraction evidence (checkbox/address signals)
        |
        v
Validation (16 rules: structural, format, consistency, evidence-based, routing)
      /   \
 accepted   needs_review
    |            |
    v            v
 Finalize   ReviewRecord -> human correction -> revalidate (loops back up)
    |            |
    v            v
        JSON / CSV output
```

Full diagram, component-by-component detail, and current production
defaults: [`docs/final-architecture.md`](docs/final-architecture.md).

## Why this design

- **Deterministic OCR + rule-based parsing over a generative VLM** --
  Pipeline A (OCR + parser) reached 100% accuracy on the clean benchmark
  at 1.2-1.4s/doc; Pipeline B (Qwen3-VL-4B-Instruct) needed 58-70s/doc
  and a large GPU for no accuracy advantage on a document type OCR
  already handles well.
- **PaddleOCR over Tesseract as the production OCR backend** -- 100%
  vs. 99.3% on the same clean benchmark, and 100% vs. 67.7% under blur,
  at lower latency; Tesseract is retained as a documented CPU-only
  cost-optimized alternative, not removed.
- **Evidence-based validation, never a single confidence score** -- a
  boolean or an address can be *structurally valid and still wrong*.
  Dedicated evidence signals (checkbox detector quality, OCR address
  region completeness) catch this, threaded from extraction through to
  validation as explicit primitives -- never a collapsed probability.
- **Human review is mandatory, never bypassable** -- finalization
  raises an error for any non-`accepted` document; the only way to
  output a `needs_review` document is through the real review ->
  correction -> revalidation workflow.
- **No global deskew, no OCR-confidence-based routing, no dual-engine
  voting** -- each was considered and rejected on measured evidence, not
  by default.

Every decision above, with the rejected alternative and the evidence
behind it: [`docs/final-decisions.md`](docs/final-decisions.md).

## Evaluation results

| Benchmark | Scope | Result |
|---|---|---|
| Extraction accuracy (expanded, 600 docs, PaddleOCR GPU) | employee/employer identity+address, federal boxes, Box 12, state/local | **99.649%** overall (100% clean, 98.627% rotated) |
| Validator unsafe-acceptance rate | same 600 docs, 16-rule validator | **0.33%** overall, **0%** on rotated |
| Validator error-detection recall | same | **88.2%** overall, **100%** on rotated |
| Validator false-review rate | same | **0%** (never flags a correct document) |
| Steady-state latency | PaddleOCR GPU | **~1.2-1.35s/doc** |
| Tests | full suite | **620 passing** |

Every figure is sourced from a committed, unmodified benchmark artifact
in `data/evaluation/results/`. Full tables, the historical 24-field
benchmark, the Pipeline B feasibility numbers, and the field-coverage
breakdown: [`docs/final-evaluation-summary.md`](docs/final-evaluation-summary.md).

**These numbers are synthetic-benchmark-specific, not a universal
production accuracy claim** -- see
[`docs/known-limitations.md`](docs/known-limitations.md).

## Run locally

All commands run from the repository root. `pytest` finds the `src/`
layout automatically (`pyproject.toml` sets `pythonpath`); a direct
`python3 -m w2_pipeline...` module invocation needs either a real
install or `PYTHONPATH=src`:

```bash
python3 -m pytest                     # full suite, no GPU/model download required -- 600 passing
python3 -m pip install .              # OR: prefix every command below with PYTHONPATH=src
```

Generate a small reproducible local dataset and run each stage against it:

```bash
PYTHONPATH=src python3 -m w2_pipeline.evaluation.generate_dataset
PYTHONPATH=src python3 -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/generated/manifest.jsonl --variant-id clean_pdf --limit 5
PYTHONPATH=src python3 -m w2_pipeline.review.cli validate data/evaluation/generated/ground_truth/w2_2026_0001.json
PYTHONPATH=src python3 -m w2_pipeline.review.cli export-document data/evaluation/generated/ground_truth/w2_2026_0001.json --format json
```

No large downloads or a GPU are required for any of the above. Pipeline
A's OCR step needs the `tesseract` system binary (or the optional
PaddleOCR extra) installed to run OCR itself; validation/review/export
commands against an already-extracted document need neither.

**Pipeline A** (`src/w2_pipeline/extraction/`) -- deterministic:
pixels -> OCR (Tesseract or PaddleOCR, selectable via `--ocr-backend`)
-> rule-based parser (with targeted visual fallbacks, e.g. the
anchor-relative Box 13 checkbox detector) -> `W2Document`.

**Pipeline B** (`src/w2_pipeline/extraction/pipeline_b/`) -- generative:
pixels -> `Qwen/Qwen3-VL-4B-Instruct` -> structured JSON -> `W2Document`.
Evaluated, not selected as primary (see Why this design, above).

```bash
python3 -m pip install '.[vlm]'   # torch/transformers/torchvision; needs a real GPU for practical latency
PYTHONPATH=src python3 -m w2_pipeline.evaluation.run_pipeline_b data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl --variant-id external_clean_render --limit 5
```

(External Symage benchmark documents must be prepared first --
`python3 -m pip install '.[external]'` then
`PYTHONPATH=src python3 -m w2_pipeline.evaluation.prepare_external_dataset`;
see `data/evaluation/README.md`.)

## Run one W-2

The canonical single-document entry point (Phase 8D.4): ingestion ->
Pipeline A (PaddleOCR by default) extraction -> evidence-preserving
validation -> accepted export or a persisted review record, in one
command:

```bash
PYTHONPATH=src python3 -m w2_pipeline.cli.run_document path/to/w2.png
```

Exit codes: `0` accepted (JSON/CSV written), `2` needs human review (not
a failure -- a `ReviewRecord` is persisted, nothing is finalized), `1`
processing failure. Full contract, output layout, and flags:
[`docs/single-document-runner.md`](docs/single-document-runner.md).
`run_document()` (`w2_pipeline.application.run_document`) is the
reusable service function behind it -- the CLI is a thin wrapper, so the
batch runner below (or a future API) can call it directly.

## Run multiple W-2s

The batch entry point (Phase 8D.5): builds one Pipeline A/PaddleOCR
extractor, warms it up once, then runs every file through the exact
same workflow as above -- reusing that one warmed extractor instead of
paying OCR-backend startup per file:

```bash
PYTHONPATH=src python3 -m w2_pipeline.cli.run_batch w2_1.png w2_2.png w2_3.png
PYTHONPATH=src python3 -m w2_pipeline.cli.run_batch --input-dir path/to/w2s/
```

Each document gets its own output subdirectory and `run_summary.json`,
exactly as above; accepted documents additionally land as one row each
in an aggregate `batch_finalized.csv`. Exit code `0` unless at least one
document hit a runtime failure -- `needs_review` is never a batch
failure, same reasoning as the exit codes above. A machine-readable
`batch_summary.json` (counts, model-startup vs. per-document processing
latency, aggregate CSV path) is always written. Full contract:
[`docs/batch-runner.md`](docs/batch-runner.md).
`run_batch()` (`w2_pipeline.application.run_batch`) is the reusable
service function behind it, callable directly by a future skill or UI.

## Operator flow

The full copy/paste runbook, run for real against two documents (one
that sails straight through, one that needs a correction), including
proof that finalization is actually blocked before correction and that
JSON/CSV export is byte-deterministic:
[`docs/operator-walkthrough.md`](docs/operator-walkthrough.md). (That
walkthrough predates the single-document runner above and documents the
review/export commands in isolation from a pre-existing `document.json`;
the runner above is the current recommended way to go from a raw file
to that same point.)

Happy path:

```bash
PYTHONPATH=src python3 -m w2_pipeline.review.cli validate <w2.json> --pipeline-id pipeline_a --route ocr --signals-json <signals.json>
PYTHONPATH=src python3 -m w2_pipeline.review.cli export-document <w2.json> --pipeline-id pipeline_a --route ocr --signals-json <signals.json> --format json
```

Review path:

```bash
PYTHONPATH=src python3 -m w2_pipeline.review.cli review-create <w2.json> --repo-dir data/review --pipeline-id pipeline_a --route ocr --signals-json <signals.json>
PYTHONPATH=src python3 -m w2_pipeline.review.cli review-correct <review_id> --repo-dir data/review --field-path employee.address.city --new-value '"Colorado Springs"'
PYTHONPATH=src python3 -m w2_pipeline.review.cli review-revalidate <review_id> --repo-dir data/review
PYTHONPATH=src python3 -m w2_pipeline.review.cli export-review <review_id> --repo-dir data/review --format csv
```

`--signals-json` (Phase 8D.2) lets a real extraction's checkbox/address
evidence reach the validator through the CLI; `--pipeline-id`/`--route`
alone still work for simpler cases.

## Repository structure

```text
src/w2_pipeline/
  ingestion/     file intake, route classification
  extraction/    Pipeline A (OCR + deterministic parser) and pipeline_b/ (VLM)
  contracts/     canonical W2Document schema (Pydantic, extra="forbid")
  validation/    16-rule validator, backend-neutral, evidence-based
  review/        ReviewRecord workflow + review/cli.py (operator CLI)
  downstream/    FinalizedW2, JSON/CSV export
  evaluation/    benchmark harnesses, dataset generation, ground truth
  application/   run_document() -- the single-document service function (Phase 8D.4)
  cli/           run_document CLI -- thin wrapper over application/ (Phase 8D.4)
docs/
  final-architecture.md, final-decisions.md,
  final-evaluation-summary.md, known-limitations.md   current state (start here)
  single-document-runner.md                            single-document CLI/service contract
  operator-walkthrough.md                             operational proof
  architecture-decision-record.md                      full historical narrative through Phase 8C
  experiments/                                         phase-by-phase experiment history
  contracts/                                            per-component design contracts
  project-state.md                                      phase-by-phase status log
data/evaluation/results/   every committed benchmark artifact cited in the docs above
```

## Known limitations

Synthetic benchmark (not real taxpayer data); 2 of 600 documents still
unsafely accept an OCR character-misread address; several optional
canonical fields (Box 14, local tax rows, address line 2) are
schema-complete but have no populated benchmark example; no global
calibrated OCR confidence (a deliberate decision, not a gap); no
frontend/GUI.

Full list, with impact and correctness-criticality for each item:
[`docs/known-limitations.md`](docs/known-limitations.md).

## Security

W-2s carry SSNs, EINs, names, addresses, and wage/tax data.
**Implemented**: SSN/EIN masking and name/address redaction in
validation diagnostics; review records named only by an opaque ID,
never PII; PII-bearing local directories gitignored by policy
(`data/documents/README.md`, `data/review/README.md`); production
validation/review code structurally cannot see benchmark ground truth
(enforced by tests, not just convention).
**Not implemented -- explicit production follow-ups**: encryption at
rest/in transit, authentication/RBAC, multi-tenant isolation, durable
audit logging, a data retention policy, secrets management, and a
managed database/object-storage backend.

## Design / experiment history

- [`docs/architecture-decision-record.md`](docs/architecture-decision-record.md)
  -- the full engineering narrative through Phase 8C: what was tested,
  what the evidence showed, what was recommended at that point.
- [`docs/experiments/`](docs/experiments/) -- every phase's experiment
  writeup, preserved as run (rejected approaches marked, not deleted).
- [`docs/contracts/`](docs/contracts/) -- per-component design contracts
  (`system-contract.md`, `canonical-w2-schema.md`, `ingestion-contract.md`,
  `extraction-pipeline-a.md`/`extraction-pipeline-b.md`,
  `validation-and-routing.md`, `review-and-downstream-output.md`).
- [`docs/project-state.md`](docs/project-state.md) -- phase-by-phase
  status log, current phase first.
- [`CHANGELOG.md`](CHANGELOG.md) -- dated, per-phase change history.

## Working Product Assumption

The primary assumed user is an accounting or tax-preparation firm
processing W-2s supplied by individual tax clients. This is a working
prototype assumption, not a claim about any specific company's internal
architecture -- the system is designed so this assumption can change
later without a redesign.
