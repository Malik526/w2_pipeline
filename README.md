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

The project has completed Phase 2: Document Ingestion Boundary + Lightweight
PDF Inspection.

Phase 0 established the project vocabulary and boundaries. Phase 1 adds the
typed canonical W-2 structure every future extractor must produce. Phase 2 adds
the local document intake service that validates PDF/JPEG/PNG inputs, captures
file metadata, and inspects PDFs for routing metadata.

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

The expected next phase is:

```text
Phase 3 - Evaluation Dataset + Ground-Truth Harness
```

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
