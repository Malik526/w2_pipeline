# W-2 Pipeline

W-2 Pipeline is a take-home prototype for automating W-2 document processing.
The long-term flow is:

```text
W-2 ingestion
-> extraction
-> canonicalization
-> validation
-> human review when required
-> downstream output
```

## Current Phase

The project has completed Phase 4: Pipeline A Deterministic Native Text/OCR
Extraction Baseline, including Phase 4B external OCR benchmark hardening and
result reconciliation.

Phase 0 established the project vocabulary and boundaries. Phase 1 adds the
typed canonical W-2 structure every future extractor must produce. Phase 2 adds
the local document intake service that validates PDF/JPEG/PNG inputs, captures
file metadata, and inspects PDFs for routing metadata. Phase 3 adds
deterministic synthetic 2026 W-2 ground truth, W-2-like evaluation document
rendering, a JSONL manifest, and a pipeline-independent field-accuracy
evaluator. Phase 3B extends that harness with an external synthetic Hugging
Face benchmark adapter while enforcing annotation leakage prevention. Phase 4
adds Pipeline A, the first deterministic extractor, with PyMuPDF native text
acquisition, a Tesseract OCR baseline, common text/layout observations, and
rule-based 2026 W-2 parsing. Phase 4B exercises the OCR route end to end
against external Symage W-2 images and records clean and degraded benchmark
results.

The current schema contract lives at:

```text
src/w2_pipeline/contracts/w2.py
```

Import it with:

```python
from w2_pipeline.contracts.w2 import W2Document
```

The ingestion boundary lives at:

```text
src/w2_pipeline/ingestion/
```

Use it with:

```python
from w2_pipeline.ingestion import ingest_document
```

The evaluation harness lives at:

```text
src/w2_pipeline/evaluation/
```

Generate the reproducible local evaluation dataset with:

```bash
python -m w2_pipeline.evaluation.generate_dataset
```

By default this writes ignored generated assets to:

```text
data/evaluation/generated/
```

The generated documents are synthetic development artifacts, not official IRS
forms. Ground truth is serialized from the canonical `W2Document` model.

Pipeline A lives at:

```text
src/w2_pipeline/extraction/
```

Run Pipeline A against an evaluation manifest with:

```bash
python -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/generated/manifest.jsonl --variant-id clean_pdf --limit 5
```

When `--output-json` is supplied, the runner writes the JSON benchmark result
and a matching human-readable Markdown report with the same base filename.

Pipeline A uses native PDF text when Phase 2 identifies usable embedded text.
Images and image-only PDF pages route to Tesseract OCR. If the `tesseract`
system binary is missing, OCR documents fail with an explicit
`MissingOcrDependencyError` instead of silently producing empty predictions.
In the completed Phase 4B environment, Tesseract was installed and exercised
end to end for the external Symage benchmark.

Prepare the external Symage Hugging Face 2026 W-2 subset with:

```bash
python3 -m pip install '.[external]'
python -m w2_pipeline.evaluation.prepare_external_dataset
```

The external command uses Hugging Face `datasets` to load
`Symage/synthetic-us-forms-preview` and filters to
`irs_w2_single_page_2026`. Downloaded/prepared external assets are ignored
under `data/evaluation/external/`. The command can also use the dataset's
pandas parquet route with `--loader pandas`.

Pipeline B (Phase 5A feasibility spike) lives at:

```text
src/w2_pipeline/extraction/pipeline_b/
```

It is a genuinely different extraction architecture: a vision-language model
(`Qwen/Qwen3-VL-4B-Instruct`) reads the same rendered W-2 page image directly
and returns structured JSON, with no OCR or deterministic parsing stage. It
shares only page-image rendering with Pipeline A and converges on the same
canonical `W2Document`. Install its dependencies and run a small smoke check
with:

```bash
python3 -m pip install '.[vlm]'
python -m w2_pipeline.evaluation.run_pipeline_b data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl --variant-id external_clean_render --limit 5
```

See `docs/contracts/extraction-pipeline-b.md` for the architecture contract
and `docs/project-state.md` for current Phase 5A status. Phase 5A is a
feasibility spike only -- no 150/600-document benchmark or Pipeline A/B
promotion decision has been made.

Validation and human-review routing (Phase 6) lives at:

```text
src/w2_pipeline/validation/
```

It judges an already-extracted canonical `W2Document` -- never ground
truth -- and routes it to `accepted` or `needs_review` with explainable,
machine-readable issue codes. It is backend-neutral: Pipeline A and
Pipeline B call the same function on their own output. Run it against a
canonical W2Document JSON file with:

```bash
python -m w2_pipeline.validation.validate_w2 data/evaluation/generated/ground_truth/w2_2026_0001.json
```

See `docs/contracts/validation-and-routing.md` for the architecture
contract. Phase 6 does not implement an ML/statistical confidence model or
a review UI.

The human review workflow and downstream output (Phase 7) live at:

```text
src/w2_pipeline/review/
src/w2_pipeline/downstream/
```

`needs_review` documents get a durable, auditable `ReviewRecord`: a human
applies explicit corrections by canonical field path, and the corrected
document is revalidated through the same unmodified Phase 6 validator.
Only an `accepted` document (whether immediately, or after a review
resolves) can be finalized into downstream JSON or CSV output. One
orchestrating CLI demonstrates the whole workflow without a frontend:

```bash
python -m w2_pipeline.review.cli export-document data/evaluation/generated/ground_truth/w2_2026_0001.json --format json
python -m w2_pipeline.review.cli review-create <needs-review-w2.json> --repo-dir data/review
python -m w2_pipeline.review.cli review-correct <review_id> --repo-dir data/review --field-path employee.ssn --new-value '"123-45-6789"'
python -m w2_pipeline.review.cli review-revalidate <review_id> --repo-dir data/review
python -m w2_pipeline.review.cli export-review <review_id> --repo-dir data/review --format csv
```

See `docs/contracts/review-and-downstream-output.md` for the full
lifecycle contract. Phase 7 does not implement a frontend, authentication,
a production database, or any vendor-specific (e.g. QuickBooks)
integration.

## Working Product Assumption

The primary assumed user is an accounting or tax-preparation firm processing
W-2 documents supplied by individual tax clients for individual tax-return
preparation.

This is a working assumption for the prototype, not a claim about Rational's
internal product architecture. The architecture should allow this assumption to
change later without redesigning the whole system.

## Initial Target

The only required initial production target is:

```text
document_type: W-2
tax_year: 2026
schema_version: 2026
```

The official IRS 2026 Form W-2 PDF is stored at:

```text
docs/references/irs/2026_W2.pdf
```

That PDF is a reference/specification artifact, not taxpayer data, benchmark
data, training data, or ground truth.

The canonical schema was derived from this reference and is summarized in:

```text
docs/contracts/canonical-w2-schema.md
```

## System Boundary

The system begins when a W-2 document enters the application. Initial intended
input types are PDF, JPEG, and PNG.

The system ends when it has produced validated canonical W-2 data suitable for
downstream use. Initial planned downstream output forms are canonical JSON and
CSV.

## Architecture Direction

The conceptual architecture is:

```text
Next.js / React UI
-> FastAPI
-> Ingestion
-> Tax-year detection/configuration
-> Replaceable extraction pipeline
-> Canonical W-2
-> Tax-year-aware validation
-> validated / needs_review / failed
-> JSON / CSV
```

The planned stack is Python for processing, FastAPI for the API layer, Pydantic
for schemas, PyMuPDF for PDF processing, pandas for offline evaluation, local
filesystem storage for prototype documents, SQLite for local metadata when
needed, and Next.js / React / TypeScript for a future UI.

## Evaluation Direction

Future extraction approaches should be evaluated offline against common ground
truth. The primary benchmark is 2026-style W-2 documents. Historical W-2 forms
may later be used for compatibility or robustness testing, with results reported
by tax year rather than blended into one opaque score.

Core metrics are field accuracy, review rate, processing latency, failure rate,
and cost per document where paid APIs or models are used. Extractor confidence
scores are exploratory and must not be treated as correctness.

Phase 3 implements field accuracy, failure classification, and latency capture
support. Review routing, confidence thresholds, cost tracking, and model
extraction remain future work.

Phase 4 implements Pipeline A benchmark execution and route-aware evaluation
metadata. Phase 4B adds per-field benchmark reporting and records completed
external OCR benchmarks. The internal generated clean-PDF smoke benchmark
reached `1.0` field accuracy through the native PDF route. The external Symage
clean-render benchmark reached 98.88% field accuracy across 150 OCR documents.
The 600-variant external robustness benchmark reached 89.27% aggregate field
accuracy with 0 document failures, with strong clean/compressed performance,
moderate rotation degradation, and substantial blur degradation.

The enriched human-readable clean Phase 4B report is:

```text
data/evaluation/results/phase4b_external_clean_150.md
```

Machine-readable result artifacts remain canonical:

```text
data/evaluation/results/phase4b_external_clean_150.json
data/evaluation/results/phase4b_external_all_variants_600.json
```

Benchmark isolation is explicit: primary end-to-end extractors receive only the
document image/path and production-realistic non-answer metadata. Dataset
annotations such as tokens, bounding boxes, NER tags, FUNSD, COCO, and YOLO
remain evaluator-side ground-truth material and are not passed to Pipeline A or
Pipeline B.

## Security

Real taxpayer W-2 data must not be committed or casually used as development
fixtures. Future fixtures should use synthetic names, fake SSNs, fake EINs,
fake addresses, public blank IRS forms, or appropriately licensed open datasets
without sensitive taxpayer information.

## Contracts

Detailed Phase 0 contracts live in:

- `docs/contracts/system-contract.md`
- `docs/contracts/workflow-and-architecture.md`
- `docs/contracts/evaluation-plan.md`
- `docs/references/irs/README.md`

Implementation briefs live in:

- `docs/briefs/phase-1-canonical-w2-schema.md`

Current schema contract:

- `docs/contracts/canonical-w2-schema.md`
- `src/w2_pipeline/contracts/w2.py`

Current ingestion contract:

- `docs/contracts/ingestion-contract.md`
- `src/w2_pipeline/ingestion/`

Current evaluation contract:

- `docs/contracts/evaluation-plan.md`
- `src/w2_pipeline/evaluation/`

Current extraction contract:

- `docs/contracts/extraction-pipeline-a.md`
- `src/w2_pipeline/extraction/`
