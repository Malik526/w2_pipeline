# Changelog

## 2026-09-02

### Phase 2 - Document Ingestion

- Implemented local PDF/JPEG/PNG ingestion with type reconciliation,
  generated document IDs, file size, MIME type, and SHA-256 metadata.
- Added PyMuPDF PDF inspection for page count and embedded-text routing
  classification, plus Pillow image readability checks and dimensions.
- Added explicit ingestion errors, ingestion contract documentation, and
  generated-fixture tests.
- Verified with `python3 -m pytest` and package install/import checks.

### Phase 1 - Canonical W-2 Schema

- Implemented the Phase 1 canonical 2026 W-2 Pydantic schema contract with
  structural tests and schema documentation.

### Phase 1 - Implementation Brief

- Added a deterministic Phase 1 Codex implementation brief for the canonical
  W-2 Pydantic schema contract.

### Phase 0 - Project Foundation

- Established Phase 0 project contracts for W-2 Pipeline.
- Added the official IRS 2026 Form W-2 PDF as an authoritative reference
  artifact under `docs/references/irs/`.
- Documented tax-year-aware architecture, reference/evaluation data separation,
  replaceable extraction pipeline expectations, evaluation metrics, RAG
  non-goals, and PII handling constraints.
