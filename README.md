# W-2 Automation Platform

A prototype system that takes a W-2 tax form (PDF or image), extracts its
data into a structured, typed representation, automatically judges
whether the result is safe to trust, routes anything uncertain to a human
for a quick correction, and produces a clean downstream JSON/CSV artifact
-- end to end, with two extraction architectures evaluated head to head
along the way.

**Start here for the full engineering story**:
[`docs/architecture-decision-record.md`](docs/architecture-decision-record.md)
-- what was tested, what the evidence shows, what is recommended for
production, and what is explicitly left as a follow-up. This README is a
map to that document and to the rest of the repo, not a replacement for it.

## Problem

An accounting/tax-preparation firm receives many client W-2s and needs
their data (SSN, employer EIN, wages, withholding, etc.) turned into
structured records quickly and safely enough to use in downstream
tax-preparation workflows, without a human re-keying every field by hand
-- while still catching cases an automated system got wrong.

## Architecture

```text
W-2 PDF / image
        |
        v
Ingestion + rendering
        |
        v
Extraction  (Pipeline A: OCR + deterministic parser  |  Pipeline B: VLM)
        |
        v
Canonical W2Document
        |
        v
Production validation (no ground truth available here -- see below)
      /   \
 accepted   needs_review
    |            |
    v            v
 Finalize   ReviewRecord -> human correction -> re-validate (loops back up)
    |            |
    v            v
        JSON / CSV output
```

Full diagram (including both extraction architectures) and the reasoning
behind every arrow: `docs/architecture-decision-record.md` Sections 1-2.

## Quick Start

All commands below are run from the repository root. `pytest` finds the
`src/` layout automatically (`pyproject.toml` sets `pythonpath`), but a
direct `python3 -m w2_pipeline...` module invocation needs either a real
install or `PYTHONPATH=src` -- use whichever your environment supports;
both are shown once here, `PYTHONPATH=src` throughout the rest of this
README since it needs no install step at all:

```bash
python3 -m pytest                                    # full suite, no GPU/model download required
python3 -m pip install .                              # OR: prefix every command below with PYTHONPATH=src
```

Validate an existing canonical document and see the accept/review
decision:

```bash
PYTHONPATH=src python3 -m w2_pipeline.validation.validate_w2 data/evaluation/generated/ground_truth/w2_2026_0001.json
```

(If `data/evaluation/generated/` doesn't exist yet, generate it first --
see "End-to-End Workflow" below.)

Run the full review-and-export workflow demo (Flow B: a document that
needs review, gets corrected, and is exported) end to end:

```bash
PYTHONPATH=src python3 -m w2_pipeline.review.cli review-create <needs-review-w2.json> --repo-dir data/review
PYTHONPATH=src python3 -m w2_pipeline.review.cli review-correct <review_id> --repo-dir data/review --field-path employee.ssn --new-value '"123-45-6789"'
PYTHONPATH=src python3 -m w2_pipeline.review.cli review-revalidate <review_id> --repo-dir data/review
PYTHONPATH=src python3 -m w2_pipeline.review.cli export-review <review_id> --repo-dir data/review --format csv
```

No large downloads or a GPU are required for any of the above. Pipeline
A's OCR step needs the `tesseract` system binary (or the optional
PaddleOCR extra) installed; see "Extraction A/B Test" below.

## End-To-End Workflow

1. **Ingestion** (`src/w2_pipeline/ingestion/`) -- validates a local
   PDF/JPEG/PNG, records file metadata, and classifies PDF text routing.
2. **Extraction** (`src/w2_pipeline/extraction/`,
   `src/w2_pipeline/extraction/pipeline_b/`) -- produces a canonical
   `W2Document`. Two architectures exist; see the A/B section below.
3. **Validation** (`src/w2_pipeline/validation/`) -- judges the
   `W2Document` with no ground truth available (that's a benchmark-only
   concept) and returns `accepted` or `needs_review` with explainable
   issue codes.
4. **Review** (`src/w2_pipeline/review/`) -- `needs_review` documents get
   a durable `ReviewRecord`; a human applies an explicit correction by
   field path; the corrected document is re-validated through the exact
   same validator.
5. **Downstream output** (`src/w2_pipeline/downstream/`) -- only an
   `accepted` document (immediately, or after review resolves) is
   finalized into JSON or CSV.

Generate a small reproducible local dataset and run each stage against it:

```bash
PYTHONPATH=src python3 -m w2_pipeline.evaluation.generate_dataset
PYTHONPATH=src python3 -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/generated/manifest.jsonl --variant-id clean_pdf --limit 5
PYTHONPATH=src python3 -m w2_pipeline.validation.validate_w2 data/evaluation/generated/ground_truth/w2_2026_0001.json
PYTHONPATH=src python3 -m w2_pipeline.review.cli export-document data/evaluation/generated/ground_truth/w2_2026_0001.json --format json
```

## Extraction A/B Test

**Pipeline A** (`src/w2_pipeline/extraction/`) -- deterministic:
pixels -> OCR (Tesseract or PaddleOCR, selectable) -> rule-based parser
(with targeted visual fallbacks, e.g. pixel-based Box 13 checkbox
detection) -> `W2Document`.

```bash
PYTHONPATH=src python3 -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/generated/manifest.jsonl --variant-id clean_pdf --limit 5
```

**Pipeline B** (`src/w2_pipeline/extraction/pipeline_b/`) -- generative:
pixels -> `Qwen/Qwen3-VL-4B-Instruct` -> structured JSON -> `W2Document`.
No OCR or deterministic parsing anywhere in this path.

```bash
python3 -m pip install '.[vlm]'   # torch/transformers/torchvision; needs a real GPU for practical latency
PYTHONPATH=src python3 -m w2_pipeline.evaluation.run_pipeline_b data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl --variant-id external_clean_render --limit 5
```

(External Symage benchmark documents must be prepared first --
`python3 -m pip install '.[external]'` then
`PYTHONPATH=src python3 -m w2_pipeline.evaluation.prepare_external_dataset`;
see `data/evaluation/README.md`.)

**Result**: Pipeline A (OCR + deterministic parsing) is the selected
primary architecture. Full evidence and reasoning:
`docs/architecture-decision-record.md` Sections 2-4.

## Results

| Architecture | Hardware | Accuracy (clean / worst-condition) | Latency | Decision |
|---|---|---|---|---|
| Tesseract (Pipeline A) | CPU | 99.3% / 67.7% (blur) | 2.3s/doc | Cost-optimized alternative |
| PaddleOCR (Pipeline A) | GPU | **100.0%** / **100.0%** (blur) | **1.3-1.4s/doc** | **Selected primary** |
| Qwen3-VL-4B-Instruct (Pipeline B) | GPU (large) | 100% *conditional* on the 80% of documents that succeeded | 58-70s/doc | Not selected |

Every figure above is sourced from a committed, unmodified benchmark
artifact in `data/evaluation/results/` -- see
`docs/architecture-decision-record.md` Section 3-4 for the full table,
citations, and important scope caveats (in particular: do not read the
VLM's "100%" as an end-to-end accuracy claim -- see Section 4).

**Validation effectiveness, measured against real historical errors**
(`docs/experiments/phase8-validator-effectiveness.md`): the Phase 6
validator has a **0% false-review rate** in every condition analyzed (it
never sends a correctly-extracted document to review) and correctly
catches **88% of severe/missing-field errors** but only **9% of subtle,
plausible-looking value errors** (e.g. a checkbox read backwards) --
exactly the limitation described below, now quantified.

## Architecture Decision

**Selected**: PaddleOCR (GPU) + deterministic parsing, as Pipeline A.
**Cost-optimized alternative**: Tesseract (CPU), same pipeline.
**Not selected as primary**: Qwen3-VL-4B-Instruct (Pipeline B) -- far
higher latency and hardware cost for no accuracy advantage on this
already-well-suited-to-OCR document type.

Full reasoning, including production-economics discussion (GPU cost vs.
human-review cost is an open, not-yet-priced trade-off) and throughput's
connection to the actual business value:
`docs/architecture-decision-record.md` Sections 2, 5-6, 9, 16.

## Production Validation (No Ground Truth)

A benchmark can compare a prediction against a known correct answer.
Production cannot -- there is no answer key for a new customer's W-2. The
Phase 6 validator (`docs/contracts/validation-and-routing.md`) instead
checks what's checkable without one: required fields present, SSN/EIN
format, supported tax year, monetary sign/precision, and a few structural
sanity checks. **It cannot prove every accepted value is correct** -- a
plausible-but-wrong SSN passes format validation. This is stated
explicitly, not glossed over, and measured directly in
`docs/experiments/phase8-validator-effectiveness.md`.

A real, unplanned example of why this layer matters even alongside a
"complete" benchmark: `docs/architecture-decision-record.md` Section 10
(the employer-name benchmark blind spot) -- production validation caught
a real extraction gap that had been invisible to every accuracy number
this project had ever computed.

## Human Review

```bash
PYTHONPATH=src python3 -m w2_pipeline.review.cli review-create <needs-review-w2.json> --repo-dir data/review
PYTHONPATH=src python3 -m w2_pipeline.review.cli review-correct <review_id> --repo-dir data/review --field-path employee.ssn --new-value '"123-45-6789"'
PYTHONPATH=src python3 -m w2_pipeline.review.cli review-revalidate <review_id> --repo-dir data/review
```

A `needs_review` document gets a durable, auditable `ReviewRecord`
(`src/w2_pipeline/review/`). The original extraction is never mutated;
every correction is an explicit, human-supplied field/value pair,
recorded append-only; a correction is only "resolved" once the corrected
document passes the *same* Phase 6 validator again. No AI auto-correction
exists anywhere in this workflow. Full contract:
`docs/contracts/review-and-downstream-output.md`.

## Downstream Output

```bash
PYTHONPATH=src python3 -m w2_pipeline.review.cli export-document <w2.json> --format json
PYTHONPATH=src python3 -m w2_pipeline.review.cli export-review <review_id> --repo-dir data/review --format csv
```

Only an `accepted` document can be finalized (`FinalizedW2`,
`src/w2_pipeline/downstream/`) into JSON or CSV. The adapter boundary is
deliberately generic -- a future database, REST API, webhook, or
tax-prep/accounting-platform adapter could plug in without touching
extraction, validation, or review code. No vendor-specific integration
(e.g. QuickBooks) exists in this prototype.

## Security

W-2s carry SSNs, EINs, names, addresses, and wage/tax data.
**Implemented**: SSN/EIN masking and name/address redaction in validation
diagnostics; review records named only by an opaque ID, never PII;
PII-bearing local directories gitignored by policy
(`data/documents/README.md`, `data/review/README.md`); production
validation/review code structurally cannot see benchmark ground truth
(enforced by tests, not just convention).
**Not implemented -- explicit production follow-ups**: encryption at
rest/in transit, authentication/RBAC, multi-tenant isolation, durable
audit logging, a data retention policy, secrets management, and a managed
database/object-storage backend. Full list:
`docs/architecture-decision-record.md` Section 14.

## Known Limitations

Box 13's checkbox detector doesn't track rotation geometry; Tesseract has
residual accent-recognition and blur weaknesses; `employer.address` has
the same OCR-fallback gap `employer.name` had before it was fixed; the
Symage benchmark's field coverage excludes `employer.name`/`employer.address`;
deterministic validation can't catch a plausible-but-wrong value (measured
above); review persistence is filesystem-only with no reopen workflow; no
auth/multi-tenancy; the VLM evaluation is a 5-document spike, not a
statistically meaningful sample; no real cloud cost has been benchmarked.
Full list with context: `docs/architecture-decision-record.md` Section 15.

## What I Would Build Next

1. A real GPU-cost-vs-review-cost pricing study to close the outstanding
   Paddle-vs-Tesseract economics question (Section 9 of the ADR).
2. Extend the employer-name OCR fallback to `employer.address`, and
   extend the Symage benchmark adapter to score `employer.name` (both
   scoped, low-risk follow-ups already identified in Phase 6B).
3. A rotation-aware recalibration of the Box 13 checkbox detector -- the
   single largest remaining Pipeline A accuracy gap.
4. A larger, statistically meaningful Pipeline B benchmark (150+
   documents) before drawing any conclusion about VLM extraction beyond
   "feasible, not yet competitive on cost/latency for this workload."
5. A review front-end on top of the existing `ReviewRecord`/`review.cli`
   API -- the backend workflow is complete; only the UI layer is missing.
6. Production security hardening per the "Not implemented" list above,
   before handling real taxpayer data.

## Contracts And Deep-Dive Docs

- `docs/architecture-decision-record.md` -- the full engineering story (start here).
- `docs/contracts/system-contract.md`, `workflow-and-architecture.md`, `evaluation-plan.md` -- product/architecture scope.
- `docs/contracts/canonical-w2-schema.md` -- the typed `W2Document` contract.
- `docs/contracts/ingestion-contract.md` -- document intake.
- `docs/contracts/extraction-pipeline-a.md`, `extraction-pipeline-b.md` -- the two extraction architectures.
- `docs/contracts/validation-and-routing.md` -- production validation.
- `docs/contracts/review-and-downstream-output.md` -- human review and output.
- `docs/experiments/` -- what was tried and learned, phase by phase, including the full validator-effectiveness analysis and the employer-name investigation.
- `docs/project-state.md` -- current phase status and history.
- `data/evaluation/results/` -- every committed benchmark artifact cited above.

## Working Product Assumption

The primary assumed user is an accounting or tax-preparation firm
processing W-2s supplied by individual tax clients. This is a working
prototype assumption, not a claim about any specific company's internal
architecture -- the system is designed so this assumption can change
later without a redesign.
