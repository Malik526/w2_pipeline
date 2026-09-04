# Changelog

## 2026-09-04

### Phase 4E - PaddleOCR `box_13.retirement_plan` Failure Investigation

- Investigated why PaddleOCR GPU's entire 90-field failure surface in the
  150-document benchmark is `box_13.retirement_plan`. Diagnostic only: no
  parser logic, Paddle configuration, or accuracy settings were changed, and
  no new benchmark was run.
- First established from the existing result that PaddleOCR predicted
  `retirement_plan = false` on all 150 documents with zero exceptions —
  exactly the 90 ground-truth-`true` documents failed, none of the 60
  "correct" predictions come from a `true`-labeled document. 0% recall on
  the positive class, not scattered recognition noise.
- Captured raw, unmodified `extract_image()` observations (no ground truth
  or annotations passed to the extractor) for both backends on three
  representative documents (`symage_900001`, `symage_900002`: ground truth
  `true`; `symage_900003`: ground truth `false`, for contrast). Found that
  Tesseract detects a small, template-fixed-position observation inside the
  checkbox geometry zone and garbles it into stray text (`"[V"`, `"4"`),
  while PaddleOCR detects **zero observations anywhere in or near that
  zone** on either `true`-labeled document — the checkbox glyph is entirely
  absent from PaddleOCR's output, not merged, misrecognized, or mispositioned.
- Ruled out coordinate/geometry conversion bugs, observation-ordering/
  word-row-reconstruction bugs, and adapter conversion bugs by comparing
  label positions and reconstructed lines between backends, which agree
  closely.
- Root cause: PaddleOCR's PP-OCRv6 text **detection** model correctly (by
  design) does not treat a small non-linguistic checkbox glyph as a text
  region worth recognizing, while Tesseract's classical connected-component
  segmentation is far less selective and happens to garble the same glyph
  into some token. The parser's `_has_checkbox_mark` fallback
  (`src/w2_pipeline/extraction/parser_2026.py`) is not the backend-neutral
  geometric signal it's framed as — its `mark_tokens` allow-list was
  evidently reverse-engineered from Tesseract's specific misreadings of this
  glyph (`"[v"` and `"4"` both appear in the allow-list and were both
  observed verbatim). No token-list adjustment can fix this: Paddle places
  zero observations in the zone to match against.
- Updated `docs/experiments/pipeline-a-extraction-history.md` with the full
  investigation and `docs/project-state.md`'s known-weaknesses and
  immediate-next-experiment sections to record the finding and its
  implications for a possible future hybrid strategy, without implementing
  one.

### Phase 4E - PaddleOCR GPU 150-Document Benchmark

- Ran the Phase 4E PaddleOCR backend with `--paddle-device gpu` against the
  full 150-document external Symage clean-render set, holding dataset,
  ground truth, parser, evaluator, and schema constant — the same set used
  for the Phase 4C Tesseract incumbent result. Pure experiment execution: no
  Paddle implementation, parser, or accuracy-tuning changes were made.
- Result: `field_accuracy = 0.9739130434782609` (3,360/3,450 correct),
  `failed_documents = 0`, `field_failure_count = 90`, average
  `1.349492507300068` seconds/document. All 90 failures are the same field,
  `box_13.retirement_plan` (60/150 correct, 40.0% accuracy); every other
  field is 100% correct across all 150 documents. Result artifacts:
  `data/evaluation/results/phase4e_paddleocr_gpu_external_clean_150.json`
  and `.md`.
- Compared directly against the Tesseract incumbent on the identical set:
  PaddleOCR GPU's overall accuracy is lower (97.39% vs. Tesseract's 99.13%,
  90 vs. 30 field failures) so it was **not** promoted to incumbent, but it
  is ~34% faster (`1.35s` vs. `2.05s`/document) and its entire error surface
  is one systematic field rather than Tesseract's spread across seven
  fields, including 100% accuracy on the employee-name and EIN fields where
  Tesseract is weakest.
- Updated `docs/experiments/pipeline-a-extraction-history.md` and
  `docs/project-state.md` with the full comparison and per-field breakdown,
  and reframed "Immediate Next Experiment" as an open decision (whether to
  run the 600-document PaddleOCR GPU robustness set, investigate the
  `box_13.retirement_plan` failure specifically, consider a future hybrid
  approach, or stop Paddle investment here) rather than a mechanical next
  benchmark, since this task's scope was execution and comparison, not
  deciding Pipeline A's future direction.
- Removed the completed 150-document run's local `.pid`/`.log` run-control
  files (log held no unique warnings beyond the already-documented ccache
  notice).
- The Tesseract incumbent and all PaddleOCR defaults are unchanged.

### Phase 4E - PaddleOCR GPU 5-Document Smoke

- Ran the Phase 4E PaddleOCR backend with `--paddle-device gpu` against the
  same 5-document external Symage clean-render subset used for the CPU
  smoke, holding dataset, ground truth, parser, evaluator, and schema
  constant. Pure experiment execution: no Paddle implementation changes were
  needed or made.
- Result: `field_accuracy = 0.9826086956521739` (113/115 correct),
  `failed_documents = 0`, average `2.1144952545990234` seconds/document —
  identical accuracy and failure profile to the CPU smoke (same two
  documents failing `box_13.retirement_plan`), but roughly 35.2x faster
  (`74.3s` -> `2.11s`/document), within ~3% of the Tesseract incumbent's
  150-document average duration (`2.0517s`/document). Result artifacts:
  `data/evaluation/results/phase4e_paddleocr_gpu_smoke_5.json` and `.md`.
- Based on this result, launched the full 150-document PaddleOCR GPU
  benchmark (`phase4e_paddleocr_gpu_external_clean_150`, detached); its
  result is not yet included in this entry.
- Updated `docs/experiments/pipeline-a-extraction-history.md` and
  `docs/project-state.md` with the comparison against the CPU smoke and
  Tesseract incumbent, and to record the 150-document GPU run as in
  progress. Removed the completed 5-document GPU smoke's local `.pid`/`.log`
  run-control files (log duplicated the JSON already saved, no unique
  warnings beyond the already-documented ccache notice).
- The Tesseract incumbent and all PaddleOCR defaults (`device="cpu"` in
  `PaddleOcrConfig`) remain unchanged; no incumbent decision was made from
  this 5-document result.

### Phase 4E - GPU Enablement for PaddleOCR

- Installed `paddlepaddle-gpu==3.3.1` (replacing CPU `paddlepaddle==3.3.1`,
  same version, from Paddle's `cu126` CUDA index matched to the reference
  development machine's NVIDIA driver 610.43.02 on WSL2) alongside unchanged
  `paddleocr==3.7.0`. Verified via `importlib.metadata` that neither
  `paddleocr` nor `paddlex` declares its own `paddlepaddle` dependency, so a
  new `paddle-gpu` optional dependency group in `pyproject.toml` (containing
  only `paddleocr`) cannot silently reinstall or conflict with an
  already-installed GPU runtime.
- Added `--paddle-device` to the `run_pipeline_a` benchmark CLI (default
  `cpu`, unchanged; used only with `--ocr-backend paddleocr`) and
  `describe_paddle_gpu_availability()`
  (`src/w2_pipeline/extraction/ocr_paddle.py`) as a reusable, testable,
  non-benchmark diagnostic for confirming GPU visibility.
- Verified GPU availability (`compiled_with_cuda: true`, `cuda_device_count:
  1`, `cuda_device_names: ["NVIDIA GeForce RTX 3060"]`) and ran a minimal
  single-image `extract_image(device="gpu")` sanity check (not a benchmark)
  that correctly recognized the sample text in 5.96 seconds, confirming
  end-to-end GPU inference works.
- Added 8 new unit tests covering explicit device selection and the GPU
  diagnostic (mocked; none require a real GPU or PaddlePaddle installed).
  Full suite: 121 tests passing.
- Per this task's explicit scope, did **not** run the Phase 4E 5-document or
  150-document PaddleOCR benchmark on GPU (or re-run it on CPU); updated
  `docs/project-state.md` and `docs/experiments/pipeline-a-extraction-history.md`
  to record GPU as installed/verified/selectable but not yet benchmarked at
  any scale, leaving that as a separate follow-up task.
- The Tesseract incumbent, `PaddleOcrConfig`'s default `device="cpu"`, and
  the `enable_mkldnn=False` CPU correctness fix are all unchanged.

### Phase 4E - PaddleOCR Backend Implementation

- Added a structural `OcrAdapter` contract
  (`src/w2_pipeline/extraction/ocr_backend.py`) so Pipeline A's
  `ObservationAcquirer` depends on any backend implementing
  `extract_image`/`extract_pdf_pages` instead of `TesseractOcrAdapter`
  directly. Both Tesseract and the new PaddleOCR adapter satisfy it.
- Extracted PDF-page-to-image rendering out of the Tesseract adapter into a
  shared helper (`src/w2_pipeline/extraction/pdf_rendering.py`) so both OCR
  backends use identical PyMuPDF rendering instead of duplicating it.
- Added `PaddleOcrAdapter`/`PaddleOcrConfig`
  (`src/w2_pipeline/extraction/ocr_paddle.py`), calling PaddleOCR 3.7.0's
  `predict()` pipeline and mapping `rec_texts`/`rec_boxes` into the common
  `TextObservation` representation. Defaults to `enable_mkldnn=False` because
  PaddlePaddle's own default crashed CPU inference with a PIR
  attribute-conversion error on the reference development machine.
- Added `--ocr-backend {tesseract, paddleocr}` to the `run_pipeline_a`
  benchmark CLI (default `tesseract`, unchanged) and a `paddle` optional
  dependency group in `pyproject.toml`.
- Added 11 new unit tests (`tests/extraction/test_ocr_paddle.py`,
  `tests/extraction/test_pdf_rendering.py`, and additions to
  `tests/evaluation/test_run_pipeline_a.py`) using canned payloads/fake
  clients; none require PaddleOCR installed. Full suite: 111 tests passing.
- Ran a 5-document PaddleOCR smoke benchmark against the external Symage
  clean-render set per the implementation task's explicit requirement to
  validate before any larger run: `field_accuracy = 0.9826086956521739`
  (113/115 correct), 0 document failures, average `74.3`
  seconds/document (~35-37x slower than the Tesseract incumbent's
  ~2.1s/document). Result artifacts:
  `data/evaluation/results/phase4e_paddleocr_smoke_5.json` and `.md`.
- Did **not** run the full 150-document PaddleOCR benchmark, per the task's
  explicit scope; updated `docs/project-state.md` and
  `docs/experiments/pipeline-a-extraction-history.md` to record that as the
  immediate next step, with an explicit multi-hour runtime warning.
- Tesseract remains the unchanged incumbent OCR backend and default.

### Phase 4D.2 - Tesseract PSM 12 Results

- Added completed Phase 4D.2 PSM 12 clean-render benchmark artifacts:
  `phase4d_psm12_external_clean_150.json` and `.md`.
- Recorded main PSM 12 with targeted supplemental PSM 6 on the same 150
  external clean Symage documents, producing 150 successful documents, 0
  document failures, 1,742 / 3,450 correct fields, and `0.504927536231884`
  field accuracy.
- Documented the key result: PSM 12 is a broad regression, zeroing employee
  first name, employee last name, employee SSN, employer EIN, and all of
  federal Boxes 1-6, performing worse overall than both the PSM 3 incumbent
  and the previously rejected PSM 11 experiment.
- Updated `docs/experiments/pipeline-a-extraction-history.md` and
  `docs/project-state.md` to record Phase 4D as complete, confirm PSM 3 as
  the incumbent, and identify Phase 4E (PaddleOCR) as the next planned
  experiment.
- Removed the completed run's local `.pid`/`.log` run-control files per the
  long-running benchmark cleanup policy; the `.log` duplicated the JSON
  already saved and held no unique warnings or errors.

### Harness - Pipeline A Extraction Experiment Skill

- Added the first project-local skill,
  `skills/run-pipeline-a-extraction-experiment/SKILL.md`, encoding the
  recurring workflow for launching a Pipeline A Tesseract OCR extraction
  experiment: translating a request (named phase, PSM, dataset/variant,
  document limit) into a `run_pipeline_a` invocation, naming result artifacts
  without overwriting history, choosing foreground vs. detached/backgrounded
  execution per the long-running command policy, and the post-run checklist
  (experiment history, project state, changelog, run-control cleanup).
- Scoped the skill to Pipeline A only; Pipeline B has no defined execution
  workflow yet and is explicitly out of scope.
- Wired `AGENTS.md` with a new "Skills" section referencing the skill, and
  corrected the "Scope Guard" section, which still described the project as
  stopped at Phase 2 ingestion despite Phase 4D being underway, so it no
  longer contradicts the newly wired skill.
- No extraction, evaluator, or schema code changed; no benchmark was run as
  part of this task.

### Docs - Project State Reconciliation

- Updated `docs/project-state.md` so the current-state framing reflects Phase
  4D as the active phase instead of stopping the narrative at Phase 4B.
- Added explicit "Current Pipeline A Configuration," "Immediate Next
  Experiment," "Future Phases," "Current Known Weaknesses," and "Unimplemented
  Capabilities" sections answering where the project stands today.
- Recorded the Phase 4C corrected clean-150 (`0.991304347826087`) and
  robustness-600 (`0.8846376811594203`) benchmark results as the current
  authoritative external Pipeline A numbers, and marked the pre-correction
  Phase 4B numbers as historical/superseded for name-accuracy claims.
- Recorded the Phase 4D.1 PSM 11 result and conclusion (rejected as incumbent
  due to total Box 1/Box 2 regression) in the current-state summary.
- Corrected the "Next Phase" pointer, which previously jumped straight to
  Phase 5, to identify Phase 4D.2 (PSM 12) as the immediate next experiment,
  with Phase 4E (PaddleOCR) and Phase 5 (Pipeline B) as later future phases.
- No code changes; no benchmarks were run as part of this reconciliation.

### Phase 4D.1 - Tesseract PSM 11 Results

- Added completed Phase 4D.1 PSM 11 clean-render benchmark artifacts:
  `phase4d_psm11_external_clean_150.json` and `.md`.
- Recorded main PSM 11 with targeted supplemental PSM 6 on the same 150
  external clean Symage documents, producing 150 successful documents, 0
  document failures, 3,141 / 3,450 correct fields, and `0.9104347826086957`
  field accuracy.
- Documented the key result: PSM 11 improved several weak fields but missed
  federal Boxes 1 and 2 on all 150 clean documents, so it should not replace
  the incumbent main PSM 3 configuration.

### Phase 4C - Corrected Robustness Benchmark Results

- Added the completed 600-document Phase 4C robustness artifacts for the
  corrected Box e employee-name semantics benchmark:
  `phase4c_external_all_variants_600_name_semantics.json` and `.md`.
- Recorded `0.8846376811594203` aggregate field accuracy with 600 successful
  documents, 0 document failures, 12,208 / 13,800 correct fields, and 1,592
  structured field failures.
- Documented variant accuracy after the semantic correction: clean render
  `0.991304347826087`, compressed JPEG `0.9820289855072464`, rotated PNG
  `0.8944927536231884`, and blurred PNG `0.6707246376811594`.

### Phase 4D - Tesseract PSM Experiment Preparation

- Added Pipeline A OCR configuration support for controlled main Tesseract PSM
  selection, preserving PSM 3 as the default and allowing PSM 11 and PSM 12
  experiments.
- Extended the Pipeline A benchmark CLI with `--tesseract-psm` while preserving
  targeted supplemental PSM 6 SSN recovery for all supported main modes.
- Updated benchmark metadata so saved Pipeline A results record the selected
  main page segmentation mode and supplemental PSM list.
- Documented pending Phase 4D PSM 11/12 benchmark commands and noted that full
  150-document experiment runs must wait for the active Phase 4C 600-document
  benchmark to finish.

### Evaluation - Employee Name Semantics

- Corrected Symage external ground truth mapping for Box e so
  `Employee's first name and initial` is split into `employee.first_name` and
  `employee.middle_initial` instead of storing the initial inside first name.
- Updated Pipeline A OCR employee-name parsing to order Box e words
  left-to-right, split trailing uppercase initials, keep last name and suffix
  independent, and filter tiny OCR artifacts in name zones.
- Added benchmark metadata to saved Pipeline A summaries, including run
  timestamp, schema version, source datasets, variant scope, Git commit, and
  OCR configuration.
- Documented that employee-name accents are compared exactly and that
  historical Phase 4B benchmarks should be rerun before making corrected
  Box e name-accuracy claims.

### Harness - Long-Running Benchmark Policy

- Added project-local guidance requiring long-running deterministic tests,
  OCR/evaluation benchmarks, model comparisons, and similar commands to be
  launched detached/backgrounded with persisted log, PID, and intended result
  paths instead of interactive repeated polling.
- Documented the benchmark command pattern in the evaluation data workflow and
  clarified that local `.log` and `.pid` run-control files are ignored while
  intentional JSON/Markdown benchmark artifacts remain trackable.

### Evaluation - Human-Readable Benchmark Reports

- Added reusable benchmark reporting utilities that serialize structured
  field failures from existing evaluator comparisons and render Markdown
  companion reports from benchmark JSON.
- Updated the Pipeline A benchmark CLI so `--output-json` also writes the
  matching `.md` report by default, with `--no-markdown-report` available for
  JSON-only runs.
- Enriched `phase4b_external_clean_150.json` with exact synthetic
  expected-vs-predicted field failures and generated
  `phase4b_external_clean_150.md` from that JSON.
- Added reporting tests for percentage formatting, single- and multi-variant
  reports, per-field tables, field failure serialization, mismatch rendering,
  failure truncation, zero-failure reports, and JSON-to-Markdown filename
  pairing.

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
