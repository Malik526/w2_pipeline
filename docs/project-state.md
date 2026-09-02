# Project State

Last updated: 2026-09-02

## Current Phase

Phase 0 is established: domain contract, architecture contract, official
reference-form handling, data separation, and evaluation foundation.

## Authoritative Reference

The initial target is Form W-2, tax year 2026.

Reference PDF:

```text
docs/references/irs/2026_W2.pdf
```

Phase 1 must use that PDF as the source of truth for the canonical W-2 field
inventory.

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
Phase 1 - Canonical W-2 Data Contract / Pydantic Schema
```

Phase 1 should derive the initial field inventory directly from the official
2026 Form W-2 PDF.

## Open Issues

- No project-local test/build harness exists yet.
- The project directory is not currently a Git repository, so Phase 0 changes
  could not be committed locally.
