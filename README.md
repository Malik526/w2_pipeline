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

The project is in Phase 0: domain contract, architecture contract, reference
form handling, and evaluation foundation.

Phase 0 intentionally does not implement document processing or application
functionality. It establishes the project vocabulary and boundaries that later
agents should follow.

The expected next phase is:

```text
Phase 1 - Canonical W-2 Data Contract / Pydantic Schema
```

Phase 1 must derive the initial field inventory from the official 2026 Form W-2
reference PDF.

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
