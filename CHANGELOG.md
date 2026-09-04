# Changelog

## 2026-09-04

### Phase 4B - External OCR Benchmark Closure

- Added a concise human-readable Phase 4B benchmark report for Pipeline A
  external Symage clean and degraded OCR results.
- Updated README, project state, evaluation, extraction, and evaluation-data
  docs to replace stale missing-Tesseract benchmark notes with the completed
  150-document clean OCR and 600-document robustness results.
- Documented Phase 4B Tesseract/parser hardening already present in the prior
  implementation commit: full-page Tesseract segmentation, supplemental top
  identifier OCR, OCR word-row reconstruction, deterministic geometry/zone
  fallbacks, Box 13 layout detection, and per-field benchmark reporting.
- Recorded the verified committed result artifacts:
  `phase4b_external_clean_150.json` and
  `phase4b_external_all_variants_600.json`.
- Preserved the distinction between the internal generated clean-PDF smoke
  benchmark, the external Symage clean OCR realism benchmark, and the external
  degradation benchmark.

## 2026-09-03

### Phase 4 - Pipeline A Deterministic Extraction Baseline

- Added Pipeline A with a common text/layout observation model, route metadata,
  PyMuPDF native PDF text acquisition, Tesseract OCR acquisition, and explicit
  missing OCR runtime errors.
- Added a deterministic 2026 W-2 parser for employee/employer identity,
  federal Boxes 1-8, 10, and 11, repeated Box 12 entries, Box 13 flags, Box
  14a/14b values, and repeated state/local Boxes 15-20.
- Integrated Pipeline A with the existing evaluation runner, including typed
  extraction results and route-aware document evaluations.
- Added `python -m w2_pipeline.evaluation.run_pipeline_a` for benchmark runs
  with field accuracy, failure rate, average duration, accuracy by variant, and
  accuracy by route.
- Corrected internal synthetic 2026 fixtures so generated documents no longer
  invent Box 9 verification-code content and visible employer Address 2 aligns
  with ground truth.
- Added extraction tests for observations, native PDF acquisition, OCR TSV
  adaptation and missing-runtime handling, parser rules, monetary parsing,
  benchmark isolation, and evaluation integration.
- Recorded the initial Phase 4 baseline: internal clean PDFs reached `1.0`
  field accuracy on 5 documents via native PDF extraction; external Symage OCR
  execution was deferred until the Phase 4B Tesseract runtime/hardening pass.

### Phase 3B - External Synthetic W-2 Benchmark Isolation

- Fixed the Symage external adapter against the real dataset runtime schema:
  `funsd_json` now validates as a JSON-encoded FUNSD entity list, `coco_json`
  remains a JSON object, parquet ndarray token/bbox/tag values are coerced
  field-specifically, and pandas image bytes are supported.
- Added a Symage Hugging Face dataset adapter for
  `Symage/synthetic-us-forms-preview`, targeting only
  `irs_w2_single_page_2026` records as an external synthetic 2026 W-2
  benchmark source.
- Added strict `ExtractionInput` modeling so primary benchmark extractors
  receive document input and production-realistic metadata without annotation
  leakage from tokens, bounding boxes, NER tags, FUNSD, COCO, or YOLO data.
- Added evaluator-side external annotation storage, explicit FUNSD-to-canonical
  `W2Document` mapping for supported fields, partial ground-truth
  `evaluated_field_paths`, and external provenance fields in the manifest.
- Added an optional Hugging Face dataset preparation CLI and optional
  `external` dependency group for local retrieval without committing prepared
  external assets, with support for both Hugging Face `datasets` and pandas
  parquet loading.
- Added offline unit tests for external record mapping, unsupported/incomplete
  annotation handling, stable sample identity, manifest provenance, variant
  linkage, evaluator compatibility, and annotation isolation.
- Documented inspected external dataset properties, the primary end-to-end
  benchmark mode, and the future oracle/parser-isolation diagnostic boundary.

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
