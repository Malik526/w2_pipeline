# Changelog

## 2026-09-03

### Phase 3 - Evaluation Dataset And Ground-Truth Harness

- Added deterministic synthetic 2026 W-2 semantic generation using the canonical
  `W2Document` contract, with safe fake identifiers and schema variation across
  optional federal boxes, Box 12, Box 13, Box 14a/14b, and state/local entries.
- Added W-2-like development document rendering for clean PDF, clean PNG,
  modest rotation, JPEG compression, and blurred/lower-quality variants.
- Added JSONL dataset manifest contracts linking semantic samples, ground
  truth, document variants, tax year, source provenance, generator metadata,
  and transformation config.
- Added pipeline-independent canonical comparison, field flattening, field
  accuracy, explicit missing/mismatch/unexpected failure classifications,
  extractor failure handling, invalid canonical result handling, and latency
  capture support.
- Added `python -m w2_pipeline.evaluation.generate_dataset` for reproducible
  local dataset generation under ignored `data/evaluation/generated/` assets.
- Added Phase 3 tests for deterministic generation, ground-truth round trips,
  manifest loading, evaluator semantics, runner failure isolation, and Phase 2
  ingestion compatibility for generated PDF/PNG/JPEG examples.
- Updated README, project state, evaluation docs, and generated-data Git ignore
  policy.

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
