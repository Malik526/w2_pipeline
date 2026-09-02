# Project State

Last updated: 2026-09-02

## Current Phase

Phase 2 is established: Document Ingestion Boundary + Lightweight PDF
Inspection.

Phase 0 established the domain contract, architecture contract, official
reference-form handling, data separation, and evaluation foundation. Phase 1
added the typed canonical W-2 contract that future extractors must produce.
Phase 2 added local source-file intake, SHA-256 file metadata, MIME/type
reconciliation, lightweight PyMuPDF PDF inspection, and JPEG/PNG readability
checks before extraction.

## Authoritative Reference

The initial target is Form W-2, tax year 2026.

Reference PDF:

```text
docs/references/irs/2026_W2.pdf
```

Phase 1 used that PDF as the source of truth for the canonical W-2 field
inventory.

Canonical schema:

```text
src/w2_pipeline/contracts/w2.py
docs/contracts/canonical-w2-schema.md
```

Ingestion boundary:

```text
src/w2_pipeline/ingestion/
docs/contracts/ingestion-contract.md
```

## Encoded Assumptions

- The working user is an accounting or tax-preparation firm processing W-2s
  supplied by individual tax clients.
- The only required initial production schema is 2026.
- The architecture is tax-year aware but does not implement multi-year support.
- Inputs are PDF, JPEG, and PNG.
- The system ends with validated canonical W-2 data suitable for downstream
  JSON or CSV output.
- RAG is excluded from core extraction architecture.
- Extraction pipelines are replaceable and must converge on one canonical
  representation.
- Evaluation uses common ground truth and reports by tax year where applicable.
- Confidence scores remain exploratory.
- Real taxpayer data must not be committed.

## Next Phase

```text
Phase 3 - Evaluation Dataset + Ground-Truth Harness
```

Phase 3 should establish safe evaluation documents and ground truth for
benchmarking extraction pipelines. It should not use real taxpayer PII.

Completed Phase 1 brief:

```text
docs/briefs/phase-1-canonical-w2-schema.md
```

The Phase 1 implementation created the Pydantic contract layer, package
structure, tests, and schema documentation without adding extraction, validation
engines, export, persistence, or UI.

Completed Phase 2 implementation:

```text
src/w2_pipeline/ingestion/
tests/ingestion/
docs/contracts/ingestion-contract.md
```

The Phase 2 implementation created the ingestion service, typed intake result,
explicit ingestion errors, PyMuPDF PDF inspection, image readability checks,
and tests without adding OCR, field extraction, tax-year inference, validation
engines, export, persistence, UI, or RAG.

## Open Issues

- No evaluation dataset or ground-truth harness exists yet.
