# Project State

Last updated: 2026-09-04

## Current Phase

Phase 4 is established: Pipeline A Deterministic Native Text/OCR Extraction
Baseline. Phase 4B external benchmark hardening and result reconciliation are
complete. A post-Phase 4B correction now aligns employee Box e name semantics
with the official form split between first name, middle initial, last name, and
suffix.

Phase 0 established the domain contract, architecture contract, official
reference-form handling, data separation, and evaluation foundation. Phase 1
added the typed canonical W-2 contract that future extractors must produce.
Phase 2 added local source-file intake, SHA-256 file metadata, MIME/type
reconciliation, lightweight PyMuPDF PDF inspection, and JPEG/PNG readability
checks before extraction. Phase 3 added deterministic synthetic canonical W-2
generation, W-2-like document rendering, document variants, a JSONL manifest,
and a pipeline-independent field-accuracy evaluator. Phase 3B added an
external Hugging Face synthetic 2026 W-2 adapter and an explicit extraction
input boundary that prevents answer-bearing annotation leakage.
Phase 4 added the first deterministic extraction pipeline with common
text/layout observations, PyMuPDF native PDF acquisition, Tesseract OCR
fallback, deterministic 2026 W-2 parsing rules, route-aware benchmark
integration, and baseline benchmark commands. Phase 4B installed and exercised
the OCR route end to end, hardened Tesseract/parser behavior against external
W-2 images, added per-field benchmark reporting, and recorded external clean
and degraded benchmark result artifacts.

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

Evaluation harness:

```text
src/w2_pipeline/evaluation/
docs/contracts/evaluation-plan.md
data/evaluation/README.md
```

Pipeline A:

```text
src/w2_pipeline/extraction/
docs/contracts/extraction-pipeline-a.md
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
- The Phase 3 evaluator compares canonical `W2Document` predictions to
  canonical ground truth, independent of OCR, vision models, regex extraction,
  or future pipeline internals.
- Phase 3 repeated-field comparison is deterministic and index-sensitive.
- The Phase 3B external benchmark source is kept distinct from the internal
  synthetic benchmark in manifest provenance.
- Primary end-to-end benchmark extractors receive only `ExtractionInput`; FUNSD,
  COCO, YOLO, token, bounding-box, and NER annotations remain evaluator-side.
- Pipeline A uses PyMuPDF native text for text PDFs and Tesseract OCR for image
  inputs or image-only PDF pages.
- Tesseract is a system runtime dependency; when absent, OCR documents fail
  explicitly and benchmark failure isolation records the failure.
- In the completed Phase 4B benchmark environment, Tesseract was present and
  Pipeline A completed external OCR runs with 0 document failures.
- Pipeline A is strong on clean and compressed external W-2 images, degrades
  moderately under rotation, and degrades substantially under blur.
- Employee Box e `Employee's first name and initial` maps to
  `employee.first_name` plus `employee.middle_initial`; last name and suffix
  remain independent canonical fields.
- Evaluation compares employee-name strings exactly. Accents are not folded or
  transliterated during field accuracy scoring.
- Confidence scores remain exploratory.
- Real taxpayer data must not be committed.

## Next Phase

```text
Phase 5 - Pipeline B: Document Vision / Schema-Constrained Extraction
```

Phase 5 should implement a model-based challenger that produces the same
canonical `W2Document` and runs against the existing evaluator without changing
ground truth or exposing annotations.

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

Completed Phase 3 implementation:

```text
src/w2_pipeline/evaluation/
tests/evaluation/
data/evaluation/README.md
```

The Phase 3 implementation created deterministic synthetic 2026 W-2 semantic
samples, ground-truth serialization, W-2-like PDF/PNG/JPEG document rendering,
clean/rotated/compressed/blurred variants, JSONL manifest contracts, canonical
field flattening, field accuracy, explicit missing/mismatch/unexpected failure
classifications, extractor failure handling, invalid canonical result handling,
and latency capture support.

Completed Phase 3B implementation:

```text
src/w2_pipeline/evaluation/external_symage.py
src/w2_pipeline/evaluation/inputs.py
src/w2_pipeline/evaluation/prepare_external_dataset.py
tests/evaluation/test_external_symage.py
```

The Phase 3B implementation added a Symage Hugging Face adapter for
`Symage/synthetic-us-forms-preview`, filters records to
`irs_w2_single_page_2026`, stores answer-bearing annotations evaluator-side,
maps supported FUNSD key-value annotations into canonical `W2Document` ground
truth, records external provenance and evaluated field coverage in the
manifest, prepares external clean-render PNGs and derived variants, and keeps
extractor inputs isolated from tokens, bounding boxes, NER tags, FUNSD, COCO,
and YOLO annotations.

Completed Phase 4 implementation:

```text
src/w2_pipeline/extraction/
src/w2_pipeline/evaluation/run_pipeline_a.py
tests/extraction/
docs/contracts/extraction-pipeline-a.md
```

The Phase 4 implementation added route-aware common observations, native PDF
text acquisition, Tesseract OCR integration with explicit missing-runtime
errors, deterministic parsing for identity fields, federal boxes, Box 12, Box
13, Box 14a/14b, and state/local rows, Pipeline A evaluation integration, and a
benchmark CLI. It also corrected internal synthetic fixtures so 2026 generated
documents no longer invent Box 9 verification-code content.

Baseline on 2026-09-03:

- internal generated clean PDFs, first 5 documents: `field_accuracy = 1.0`,
  `failure_rate = 0.0`, route `native_pdf`

Completed Phase 4B benchmark hardening and results:

```text
src/w2_pipeline/extraction/ocr.py
src/w2_pipeline/extraction/parser_2026.py
src/w2_pipeline/evaluation/run_pipeline_a.py
src/w2_pipeline/evaluation/reporting.py
tests/extraction/
tests/evaluation/test_reporting.py
data/evaluation/results/
data/evaluation/results/phase4b_external_clean_150.md
```

The Phase 4B work changed Tesseract OCR to use full-page segmentation by
default, added a supplemental targeted OCR pass for the top identifier region,
added OCR word-row reconstruction, deterministic full-page geometry/zone
fallbacks for key 2026 W-2 fields, Box 13 layout detection, and per-field
benchmark summary output. The follow-up reporting layer added structured
field-failure serialization and same-base Markdown companion reports for saved
benchmark JSON results.

Verified Phase 4B external results:

- external Symage clean renders, 150 documents: `field_accuracy =
  0.9887878787878788`, `failure_rate = 0.0`, average 2.223 seconds/document,
  route `ocr`, with 37 structured incorrect field records
- all prepared external variants, 600 documents: `field_accuracy =
  0.8926515151515152`, `failure_rate = 0.0`, average 2.131 seconds/document,
  route `ocr`
- variant accuracy: clean 98.88%, compressed JPEG 97.97%, rotated PNG 92.45%,
  blurred PNG 67.76%

Major known weaknesses are employee first-name extraction, Box 13 retirement
plan checkbox detection, and blur sensitivity. The next extraction experiment
has not been finalized; possible next work includes a targeted PaddleOCR
comparison or a Pipeline B document-vision challenger.

Post-Phase 4B employee-name correction:

- Symage external ground truth now splits `Employee's first name and initial`
  into `employee.first_name` and `employee.middle_initial`.
- Pipeline A OCR Box e fallback now orders name-zone words left-to-right,
  splits trailing uppercase initials, and filters tiny one- to three-character
  OCR fragments only when normal-size neighboring name tokens are present.
- Benchmark reports now include metadata for run timestamp, source datasets,
  variant scope, schema version, Git commit, and OCR configuration.
- Historical Phase 4B result artifacts predate this semantic correction. Any
  name-accuracy claim based on the external Symage benchmark should use a
  freshly regenerated ground-truth dataset and rerun result.

## Open Issues

- Review routing, confidence calibration, additional OCR optimization, model extraction,
  validation engines, persistence, frontend, export, and cost tracking remain
  unimplemented future-phase work.
