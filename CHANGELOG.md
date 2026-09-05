# Changelog

## 2026-09-05

### Phase 8 - Final Architecture Decision, Economics, And Take-Home Delivery

- Added `docs/architecture-decision-record.md`: the final synthesized
  engineering decision record covering the full system architecture,
  the Pipeline A vs. Pipeline B decision, the PaddleOCR vs. Tesseract
  backend comparison (with exact figures sourced from already-committed
  `data/evaluation/results/*.json` artifacts, no new benchmark run),
  production economics (GPU vs. CPU cost, human-review cost, throughput
  and its connection to customer value), the benchmark-vs-production-
  validation distinction, the employer-name benchmark blind spot as an
  engineering lesson, security/PII posture, known limitations, and the
  final recommended architecture.
- Added `src/w2_pipeline/evaluation/validator_effectiveness.py`: an
  evaluation-side analysis (not a validation-side change) that measures
  how well Phase 6's validator detects real historical extraction errors,
  using two already-committed Pipeline A benchmark result artifacts with
  no new OCR/VLM inference run. Reconstructs each document's real
  historical prediction from ground truth plus the benchmark's own
  recorded field failures; the validator is called only with the
  reconstructed prediction, never ground truth (structurally enforced and
  tested). Result: 0% false-review rate in both analyzed conditions;
  error-detection recall is 9.2% on subtle plausible-value errors vs.
  88.1% on severe/missing-field corruption -- a direct, measured
  quantification of the "a plausible-but-wrong value can pass format
  validation" limitation. The analysis also reproduced the Phase 6B
  `employer.name` ground-truth gap at scale and reports both raw and
  adjusted numbers so that confound is visible rather than hidden. Full
  method and results: `docs/experiments/phase8-validator-effectiveness.md`;
  artifacts: `data/evaluation/results/phase8_validator_effectiveness_rotated_150.json`,
  `..._blurred_150.json`.
- Added 6 new tests (`tests/evaluation/test_validator_effectiveness.py`);
  full suite: 346 tests passing (340 + 6), zero regressions.
- Fully rewrote `README.md` as the take-home entry point: problem
  statement, architecture diagram (text and Mermaid), quick start,
  end-to-end workflow, the Pipeline A/B comparison, a results table, the
  architecture decision, production validation without ground truth,
  human review, downstream output, security, known limitations, and a
  "what I would build next" section. Every documented command was run
  against a freshly regenerated local dataset and confirmed to work
  exactly as written (including fixing two real reproducibility bugs
  found in the process: a stale non-editable package install missing the
  Phase 6/7/8 packages entirely, and every `python -m ...` example
  referencing a `python` binary that does not exist in this environment,
  only `python3` -- both are now `python3 -m ...` with a `PYTHONPATH=src`
  convention that needs no install step at all).
- No extraction, validation, or review behavior changed in this phase.

### Phase 7 - Human Review Workflow And Downstream Output

- Added `src/w2_pipeline/review/`: a backend-only human review workflow
  consuming Phase 6's `ValidationResult` without duplicating any rule. A
  `ReviewRecord` state machine (`pending -> in_review -> resolved`,
  `resolved` terminal) tracks an immutable `original_document`, an
  append-only `corrections` audit trail, and both the pre-review and
  post-correction `ValidationResult`s side by side. `field_paths.py`
  provides safe by-path get/set against the canonical schema's own
  structure (`get_field`/`set_field_value`), rejecting unknown paths and
  invalid new values explicitly. `workflow.py` provides
  `start_review`/`apply_correction`/`revalidate`; `revalidate` calls the
  unmodified Phase 6 `validate_w2_document` with fresh
  `ExtractionSignals` (the corrected content, not the original extraction
  attempt, is what is being judged). `repository.py` provides a
  `ReviewRepository` protocol plus a `FileReviewRepository`
  implementation (one JSON file per record, named by review ID only,
  never a document ID/name/SSN/EIN).
- Added `src/w2_pipeline/downstream/`: `FinalizedW2` +
  `finalize_document`, the single gate ensuring only an `accepted`
  document can become downstream output, plus `export_json`/`export_csv`
  adapters and an `OutputAdapter` protocol documenting where a future
  database/tax-software/REST/webhook/QuickBooks-style adapter would plug
  in (none implemented). CSV output flattens scalar fields into one row
  per document and JSON-string-encodes the four repeated structures
  (Box 12/14 entries, tipped occupation codes, state/local entries) into
  single cells.
- Added `src/w2_pipeline/review/cli.py`, one orchestrating CLI covering
  the full workflow: `validate`, `review-create`, `review-correct`,
  `review-revalidate`, `export-document`, `export-review`.
- Added `data/review/` (gitignored, `README.md` added) as the default
  `FileReviewRepository` location, matching the existing
  `data/documents/` PII-handling convention.
- Added 65 new tests (`tests/review/`, `tests/downstream/`) covering
  field-path get/set, state transitions, workflow orchestration
  (including the full review flow end to end), repository round-tripping
  and PII-safe filenames, `FinalizedW2` gating, both output adapters, the
  CLI driving both flows end to end, and structural AST-based isolation
  checks (no `w2_pipeline.evaluation`/`w2_pipeline.extraction`
  dependency). Full suite: 340 tests passing (275 + 65), zero
  regressions.
- Verified both required end-to-end flows as committed tests: Flow A (a
  known-good document validates `accepted` and finalizes directly) and
  Flow B (a document missing a required field validates `needs_review`,
  gets corrected through a `ReviewRecord`, revalidates to `accepted`, and
  exports) -- the latter both via the Python API and entirely through the
  CLI. See `docs/experiments/phase7-review-workflow.md`.

### Phase 6B - Fix Employer Name Extraction Gap

- Fixed `_parse_employer` (`src/w2_pipeline/extraction/parser_2026.py`):
  `employer.name` had no OCR zone-based fallback at all (unlike employee
  fields, which already had one), so it stayed `null` under OCR routing
  for every external Symage document -- a gap Phase 6 validation surfaced
  but did not cause. Root cause: the real 2026 W-2 form's Box c presents
  employer name/address/ZIP as one combined, unlabeled multi-line block
  that the primary label-based path (expecting a literal `"Name:"` line,
  matching only the internal synthetic generator's own rendering
  convention) can never match. Confirmed via direct PaddleOCR output that
  the text is recognized correctly and cleanly segmented -- this was a
  parser gap, not an OCR recognition failure, and confirmed
  backend-neutral (Tesseract exhibited the identical gap and fix).
- Added `_first_row_text_in_zone` (isolates the topmost printed line
  within a zone that may span multiple lines, needed because Box c's name
  and address lines are stacked vertically) and
  `_apply_ocr_employer_layout_fallbacks` (mirrors the existing employee
  equivalent; relocates the existing EIN fallback and adds the new name
  fallback), calibrated from real FUNSD answer boxes across 5 diagnostic
  documents. `employer.address` has the identical gap but is out of this
  fix's scope.
- Added 7 new focused tests (`tests/extraction/test_parser_2026.py`); full
  suite 275 tests passing (268 + 7), zero regressions. Verified against
  real Pipeline A extraction (both PaddleOCR and Tesseract) on all 5
  diagnostic documents: `employer.name` now recovers correctly on every
  one, matching FUNSD-confirmed expected values; `employer.ein` and
  `employer.address` unchanged.
- Investigated (not implemented) whether `employer.name` can be added to
  the Symage adapter's `evaluated_field_paths`: the FUNSD answer's
  structure is an authoritative, deterministic mapping independent of any
  Pipeline A prediction and would satisfy the criteria, but doing so is a
  separate benchmark-harness change
  (`src/w2_pipeline/evaluation/external_symage.py` plus dataset
  regeneration), left as a follow-up task. See
  `docs/experiments/phase6b-employer-name-investigation.md`.

### Phase 6 - Validation, Confidence Signals, And Human Review Routing

- Added `src/w2_pipeline/validation/`: a deterministic, backend-neutral
  validation layer that judges an already-extracted canonical `W2Document`
  (never ground truth) and routes it to `accepted` or `needs_review` with
  explainable, machine-readable `ValidationIssue` codes. Ten rule
  functions cover extraction signals, supported metadata, employee/employer
  identity required fields, SSN/EIN format, core wage/tax fields required
  (Boxes 1/2/5/6), monetary field validity (non-negative, <=2 decimal
  places), Box 12 code format, and empty state/local entries.
  Required-field decisions are evidence-based from
  `src/w2_pipeline/evaluation/synthetic.py`'s own generation logic, not
  invented. No ML/probabilistic confidence model was built:
  `ExtractionSignals` carries pipeline-agnostic quality metadata but
  deliberately no unified confidence score.
- Added `RoutingPolicy`/`decide_status` (`routing.py`), kept structurally
  separate from rule evaluation so a firm's throughput/conservativeness
  preference can change independently of what counts as an issue.
- Added `redaction.py`: SSN/EIN last-4-digit masking and full redaction
  for name/address fields before they reach a `ValidationIssue`.
- Added `src/w2_pipeline/validation/validate_w2.py`, a CLI
  (`python -m w2_pipeline.validation.validate_w2 <path>`) that validates
  one canonical W2Document JSON artifact and prints the result.
- Added 56 new unit tests (`tests/validation/`) covering redaction, every
  rule (happy path, each required-field/format/domain check, optional-field
  non-triggering, multi-issue non-short-circuiting), routing policy, the
  validator (including the `document is None` path and
  Pipeline-A/B-signal backend-neutrality), the CLI, and an AST-based
  structural test that no validation module imports
  `w2_pipeline.evaluation`/`w2_pipeline.extraction`/`w2_pipeline.ingestion`.
  Full suite: 268 tests passing (212 + 56), zero regressions.
- Small integration verification (existing fixtures only, no new
  inference run) passed: known-good documents accepted under both
  Pipeline-A-shaped and Pipeline-B-shaped signals; intentionally corrupted
  and intentionally-missing-critical-field documents routed to review.
  Manually checking real, already-on-disk fixtures additionally surfaced
  that Pipeline A currently returns `employer.name = null` for external
  Symage clean-render documents, a gap invisible to every benchmark result
  reported to date because that field has never been in any Symage
  record's `evaluated_field_paths`. Reported, not fixed -- Pipeline A
  extraction-behavior changes are out of Phase 6's scope. See
  `docs/experiments/phase6-validation-feasibility.md`.

### Phase 5A - Pipeline B (Qwen3-VL) Feasibility Spike

- Added `src/w2_pipeline/extraction/pipeline_b/`: a vision-language model
  extraction challenger (`Qwen/Qwen3-VL-4B-Instruct`) that reads the same
  rendered W-2 page image Pipeline A's OCR route uses and returns
  structured JSON, with no OCR or deterministic parser stage. Isolated
  from every Pipeline A extraction-logic module (Tesseract/PaddleOCR
  adapters, `acquisition.py`, `parser_2026.py`, `checkbox_vision.py`);
  shares only `pdf_rendering.py` (plain PyMuPDF page rasterization).
  Converges on the same canonical `W2Document` and the same
  pipeline-independent evaluator. See
  `docs/contracts/extraction-pipeline-b.md` for the full architecture.
- Added `src/w2_pipeline/evaluation/run_pipeline_b.py`, a benchmark CLI
  mirroring `run_pipeline_a.py`'s shape (manifest/variant/limit filtering,
  `--output-json` plus Markdown companion report).
- Added the `vlm` optional dependency group (`torch`, `torchvision`,
  `transformers`, `accelerate`, `jinja2`). `torchvision` and a `jinja2`
  upgrade were added after the first smoke attempt failed: Qwen3-VL's
  `AutoProcessor` requires `torchvision` for an internal video-processor
  component even for still-image use, and `apply_chat_template` requires
  `jinja2>=3.1`, newer than the reference machine's system-managed
  `Jinja2==3.0.3`.
- Added 53 new focused unit tests (`tests/extraction/pipeline_b/`) covering
  prompt construction/schema-shape alignment, JSON parsing, canonical
  mapping/validation (including a small `state_local_entries` key-alias
  normalization found during smoke testing), image preparation, GPU
  diagnostics, model runtime (all mocked -- no GPU or model download
  required), extractor orchestration, and structural checks that no
  Pipeline B module imports Pipeline A's OCR/parser code. Full suite: 212
  tests passing, zero regressions.
- Ran a 5-document smoke test (4 external clean-render + 1 rotated) against
  the prepared Symage manifest: 4/5 documents produced a valid canonical
  `W2Document` with `field_accuracy = 1.0` on every success (92/92 correct
  fields); 1/5 failed with a specific, understood `SchemaValidationError`
  (the model transcribed a Box 12 sub-row's printed line label instead of
  its actual code). Results:
  `data/evaluation/results/phase5a_pipeline_b_smoke_clean_4.json`,
  `..._rotated_1.json`. Full narrative in
  `docs/experiments/phase5a-pipeline-b-feasibility.md`.
- This is a feasibility spike only: no 150/600-document benchmark, prompt
  optimization, constrained decoding, fine-tuning, or Pipeline A/B
  comparison/promotion decision was made.

## 2026-09-04

### Phase 4E - Backend-Neutral Box 13 Checkbox Detection

- Added `src/w2_pipeline/extraction/checkbox_vision.py`: a pixel-based Box 13
  checkbox detector that reads dark-pixel ink coverage directly from the
  page image, independent of any OCR engine's text output. Directly
  addresses the root cause found in the preceding investigation (PaddleOCR's
  text detector never emits an observation for the checkbox glyph at all).
- Added `ObservationSet.box_13_visual_marks: dict[str, bool]`
  (`src/w2_pipeline/extraction/models.py`) as the typed channel for this
  non-OCR signal. `ObservationAcquirer` (`acquisition.py`) runs the detector
  on the same source image used for OCR, for every OCR-routed acquisition
  (plain image input, or rendered PDF pages for image-only/mixed routes),
  degrading to "no mark detected" plus a warning if detection fails rather
  than failing extraction. `parser_2026.py`'s
  `_apply_ocr_box_13_layout_fallbacks` ORs this signal in alongside the
  existing text-prefix and OCR-token mechanisms (kept, not removed, for
  defense in depth).
- Calibrated `RETIREMENT_PLAN_ZONE` against all 150 external Symage
  clean-render documents (pure pixel analysis of already-prepared local
  images, not an OCR run or scored benchmark): unchecked ink ratio `0.0787`,
  checked ratio `0.1000`, zero overlap across all 150 documents, threshold
  `0.09`.
- Scoped to `retirement_plan` only. `statutory_employee` and
  `third_party_sick_pay` have no ground-truth-positive example in current
  benchmark data to calibrate against; an analogy-based zone guess for them
  produced ambiguous ink ratios (`0.1134`, `0.0904`) rather than
  `retirement_plan`'s clean separation, so they were deliberately left on
  the unchanged existing fallback rather than risk a regression on fields
  that already score 100%.
- Added 9 new unit tests (`test_checkbox_vision.py`, `test_acquisition.py`,
  extensions to `test_parser_2026.py`); full suite: 130 tests passing.
- Verified with a 20-document real-pipeline smoke check (not a full
  150-document rerun): PaddleOCR GPU reached `1.0` field accuracy (20/20 on
  `box_13.retirement_plan`, previously the field's dominant failure mode);
  Tesseract was unaffected (still 20/20 on `retirement_plan`; its one
  remaining miss in that sample is the pre-existing, unrelated
  `employer.ein` failure on `symage_900021`).
- Updated `docs/contracts/extraction-pipeline-a.md`,
  `docs/experiments/pipeline-a-extraction-history.md`, and
  `docs/project-state.md` to record the fix and flag that the formal
  150-document (and 600-document) benchmark artifacts predate this change
  and have not been rerun — the next step is a full rerun to get corrected
  authoritative numbers, deliberately not performed as part of this
  implementation task.

### Phase 4E - Tesseract Incumbent 150-Document Rerun (Post Checkbox Vision)

- Reran the Tesseract incumbent's authoritative 150-document external
  clean-render benchmark (main PSM 3 + supplemental PSM 6, unchanged
  configuration) with the Box 13 visual checkbox detector in place, per the
  "Immediate Next Experiment" pointer left by the checkbox-vision
  implementation above.
- Added `data/evaluation/results/phase4e_tesseract_checkbox_vision_external_clean_150.json`
  and the matching `.md` report as new artifacts; the prior
  `phase4c_external_clean_150_name_semantics.json`/`.md` and all other
  historical result files were left unmodified.
- Result: `field_accuracy = 0.9927536231884058` (3,425/3,450 correct, up
  from 3,420/3,450), `failed_documents = 0`, average `2.330s`/document (up
  from `2.052s`, the added cost of the pixel-based checkbox pass). The only
  per-field change versus the prior Phase 4C result is
  `box_13.retirement_plan`, 96.67% -> 100.0% — every other field's
  correct/incorrect count is unchanged, confirming the fix is regression-free
  at full scale and matches the earlier 20-document smoke check exactly.
- This result now supersedes `phase4c_external_clean_150_name_semantics` as
  the authoritative Tesseract clean-150 number. The incumbent configuration
  itself is unchanged; no promotion decision was made or required. Updated
  `docs/experiments/pipeline-a-extraction-history.md` and
  `docs/project-state.md` accordingly. The equivalent PaddleOCR GPU
  150-document rerun and the 600-document robustness rerun remain
  outstanding.

### Phase 4E - PaddleOCR GPU 150-Document Rerun (Post Checkbox Vision)

- Reran PaddleOCR GPU's 150-document external clean-render benchmark
  (`--ocr-backend paddleocr --paddle-device gpu`, unchanged configuration)
  with the Box 13 visual checkbox detector in place, closing out the second
  half of the "Immediate Next Experiment" pointer (Tesseract's side was
  completed immediately prior, above).
- Added `data/evaluation/results/phase4e_paddleocr_gpu_checkbox_vision_external_clean_150.json`
  and the matching `.md` report as new artifacts; the prior
  `phase4e_paddleocr_gpu_external_clean_150.json`/`.md` and all other
  historical result files were left unmodified.
- Result: `field_accuracy = 1.0` (3,450/3,450 correct, up from
  3,360/3,450), `failed_documents = 0`, `field_failure_count = 0`, average
  `1.439s`/document (up from `1.349s`, the added cost of the pixel-based
  checkbox pass). The only field that changed versus the historical Phase 4E
  result is `box_13.retirement_plan`, 40.0% -> 100.0% — every one of the 90
  historical failures was this field, and all are now resolved with zero
  regressions elsewhere.
- **Versus the same-day Tesseract post-checkbox-vision result** (99.28% at
  `2.330s`/doc): PaddleOCR GPU now scores higher accuracy (100.0%) at lower
  latency (1.439s/doc, ~38% faster), including 100% on every field that
  remains Tesseract's weakest. This closes and inverts PaddleOCR GPU's
  historical headline weakness (lower accuracy than Tesseract) — it is now
  strictly ahead of the incumbent on this clean-150 benchmark on both
  accuracy and speed.
- This does **not** change the incumbent configuration by itself — no
  promotion decision was made as part of this rerun, per the experiment
  skill's boundaries. It substantially strengthens the case for that
  decision, which remains explicitly the user's to make. Updated
  `docs/experiments/pipeline-a-extraction-history.md` and
  `docs/project-state.md` accordingly (Immediate Next Experiment, Current
  Known Weaknesses, Current Pipeline A Configuration). The 600-document
  robustness rerun (either backend) was deliberately not run as part of this
  task.

### Phase 4E - Tesseract Incumbent 600-Document Robustness Rerun (Post Checkbox Vision)

- Reran the Tesseract incumbent's authoritative 600-document external
  robustness benchmark (all four variants: clean render, compressed JPEG,
  rotated PNG, blurred PNG; main PSM 3 + supplemental PSM 6, unchanged
  configuration) with the Box 13 visual checkbox detector in place.
  Tesseract-only by explicit task scope — no PaddleOCR run.
- Added `data/evaluation/results/phase4e_tesseract_checkbox_vision_external_all_variants_600.json`
  and the matching `.md` report as new artifacts; the prior
  `phase4c_external_all_variants_600_name_semantics.json`/`.md`,
  `phase4b_external_all_variants_600.json`, and all other historical result
  files were left unmodified.
- Result: `field_accuracy = 0.8897826086956522` (12,279/13,800 correct, up
  from 12,208/13,800), `failed_documents = 0`, average `2.319s`/document (up
  from `2.199s`). The only field that changed anywhere in the aggregate
  result is `box_13.retirement_plan` (66.83% -> 78.67% aggregate); every
  other field's correct/incorrect count is unchanged across all four
  variants — zero regressions.
- Per-variant `box_13.retirement_plan` breakdown resolves the open question
  left after the checkbox-vision implementation (the ink-coverage threshold
  was calibrated only against clean renders): clean render 96.67% -> 100.0%
  and compressed JPEG 82.67% -> 100.0% are **fully resolved**; rotated PNG
  48.0% -> 60.0% and blurred PNG 40.0% -> 54.67% are **improved but not
  fully resolved** — rotation shifts the checkbox's true-image position past
  the fixed calibration zone, and blur degrades the ink-coverage measurement
  near the `0.09` threshold.
- This result now supersedes `phase4c_external_all_variants_600_name_semantics`
  as the authoritative Tesseract 600-document robustness number. The
  incumbent configuration itself is unchanged; no promotion decision applies
  (Tesseract-only rerun). Updated
  `docs/experiments/pipeline-a-extraction-history.md` and
  `docs/project-state.md` accordingly (Immediate Next Experiment, Current
  Known Weaknesses, Current Pipeline A Configuration, authoritative-results
  section). Whether the residual rotated/blurred gap warrants a follow-up
  fix is left as an open decision. The equivalent PaddleOCR GPU
  600-document robustness rerun was not run and remains outstanding.

### Phase 4E - PaddleOCR GPU 600-Document Robustness Rerun (Post Checkbox Vision)

- Reran PaddleOCR GPU's 600-document external robustness benchmark (all
  four variants: clean render, compressed JPEG, rotated PNG, blurred PNG;
  `--ocr-backend paddleocr --paddle-device gpu`) with the Box 13 visual
  checkbox detector in place — PaddleOCR GPU's first-ever 600-document
  robustness data point, closing the last outstanding item from the
  checkbox-vision fix's rerun sequence.
- Added `data/evaluation/results/phase4e_paddleocr_gpu_checkbox_vision_external_all_variants_600.json`
  and the matching `.md` report as new artifacts; no prior PaddleOCR
  600-document result existed to preserve, and all other historical result
  files were left unmodified.
- Result: `field_accuracy = 0.976231884057971` (13,472/13,800 correct),
  `failed_documents = 0`, average `1.330s`/document. **Every one of the 328
  failures is on the `rotated_png` variant** — clean render, compressed
  JPEG, and blurred PNG are all perfect (`field_accuracy = 1.0`), including
  blur, which is Tesseract's worst variant (67.71%).
- `rotated_png` breakdown (90.49%): failures are concentrated in
  `employee.first_name` (0/150, complete failure), `employee.middle_initial`
  (32/150, 21.3%), and `box_13.retirement_plan` (90/150, 60.0%).
- **New finding, unrelated to checkbox vision:** every rotated
  `employee.first_name` failure shows the printed field-label text bled
  into the predicted name (e.g. expected `"Lori"`, predicted `"Lori e
  Employee's first name and initial"`) — a label-bleed artifact in
  PaddleOCR's rotated-image name-zone word reconstruction, newly surfaced
  by this rerun since no prior PaddleOCR robustness benchmark existed to
  catch it. Not yet investigated or fixed.
- **`box_13.retirement_plan` rotated failures are identical, document for
  document, to Tesseract's** (same exact 60 documents, confirmed by
  cross-checking `document_id` sets) — the visual checkbox detector runs
  identically regardless of backend, so this confirms its rotation
  weakness is a property of the fixed calibration zone, not either
  backend's OCR behavior.
- Versus Tesseract's 600-document result (88.98% aggregate, worst variant
  blurred at 67.71%): PaddleOCR GPU is substantially ahead overall (97.62%)
  and its worst variant (rotated, 90.49%) beats Tesseract's worst by a wide
  margin, while being comparable to (marginally better than) Tesseract's
  own rotated result (89.97%).
- This does **not** promote PaddleOCR GPU to incumbent or change the
  incumbent configuration — no promotion decision was made as part of this
  rerun, per the experiment skill's boundaries; that decision, along with
  whether the newly discovered rotation label-bleed artifact needs a fix,
  remains explicitly the user's to make. Updated
  `docs/experiments/pipeline-a-extraction-history.md` and
  `docs/project-state.md` accordingly (Immediate Next Experiment, Current
  Known Weaknesses, Current Pipeline A Configuration, Unimplemented
  Capabilities). No Tesseract PSM 11 or other configuration was run, per
  this task's explicit scope.

### Phase 4E - Targeted Supplemental PSM 11 Readiness (Implementation Only, No Experiment Run)

- Verified whether Pipeline A's existing config/CLI could express a
  Tesseract configuration adding PSM 11 as a *targeted* supplemental pass
  (main PSM 3 + supplemental PSM 6, unchanged, plus supplemental PSM 11
  restricted to only the fields the Phase 4D.1 main-PSM-11 experiment
  showed improve: `employee.first_name`, `employee.middle_initial`,
  `employer.ein`, and federal Boxes 3/5/6) without further implementation.
  Answer: **no** — the only existing supplemental mechanism was a single
  hardcoded zone+regex filter (the SSN top-identifier region), with no CLI
  exposure of supplemental modes at all, and merging an unfiltered PSM 11
  pass into the flat observation list would have risked corrupting
  already-correct primary-path Box 3/5/6 line parsing (those target zones
  physically overlap primary Box-line regions, unlike PSM 6's spatially
  isolated SSN zone).
- Implemented the smallest supporting extension rather than a broader
  redesign:
  - `TextObservation.is_supplemental: bool` (`models.py`) — tags whether an
    observation came from a targeted supplemental pass rather than the
    main pass. Backend-neutral: PaddleOCR observations are never tagged,
    so this is a no-op for that backend.
  - `SupplementalTargetZone` / `_SUPPLEMENTAL_TARGET_ZONES` (`ocr.py`) — a
    generalized per-PSM-mode table of approved zones (each mirroring its
    corresponding parser fallback zone), replacing the old
    single-zone-only `_top_identifier_observations` with
    `_targeted_supplemental_observations`. PSM 6's zone/behavior is
    unchanged; PSM 11 gets five new zones covering exactly the six
    approved fields, explicitly excluding Box 13 (owned by
    `checkbox_vision.py`) and SSN (owned by PSM 6). Added
    `SUPPORTED_SUPPLEMENTAL_PAGE_SEGMENTATION_MODES = (6, 11)` with
    `TesseractOcrConfig` validation.
  - `parser_2026.py` — supplemental observations are now excluded from
    primary row/line reconstruction (`_group_observation_rows`) and from
    page-extent computation (`_layout_extent`), so a supplemental pass can
    only ever reach the OCR zone-based fallback functions, which already
    fire solely when the primary path left a field `None`. This makes
    supplemental recovery structurally incapable of overriding or
    corrupting an already-correct primary value, on any current or future
    supplemental PSM. The parser gained no PSM-specific branching; it
    remains fully backend/PSM-agnostic.
  - `run_pipeline_a.py` — new `--tesseract-supplemental-psm` CLI flag
    (comma-separated, default `"6"`, unchanged incumbent behavior when
    omitted).
- 13 new focused tests: 7 in `test_ocr.py` (config validation, PSM 11 zone
  targeting including explicit Box 13 exclusion, PSM 6 behavior
  unchanged), 2 in `test_parser_2026.py` (row-grouping corruption
  protection; targeted recovery when the primary path is missing), 4 in
  `test_run_pipeline_a.py` (CLI parsing and threading). Full suite: 143
  tests passing, zero regressions.
- Updated `docs/contracts/extraction-pipeline-a.md` with a new "Targeted
  Supplemental OCR Passes" section and the exact command for the
  not-yet-run smoke experiment, and `docs/project-state.md` accordingly.
- **No experiment was run** — this was implementation/readiness work only,
  per explicit task scope. The incumbent configuration is unchanged; no
  promotion or default change was made. PaddleOCR and `checkbox_vision.py`
  were not touched.

### Phase 4E - Targeted Supplemental PSM 11 Smoke Test (Disqualifying Regression Found)

- Ran the readiness-unlocked configuration for the first time: main PSM 3 +
  targeted supplemental PSM 6 + targeted supplemental PSM 11
  (`--tesseract-supplemental-psm 6,11`), 5 external clean-render documents,
  checkbox vision enabled.
- Added `data/evaluation/results/phase4e_tesseract_supplemental_psm11_smoke_5.json`
  and the matching `.md` report; no historical artifacts were touched.
- Result: `field_accuracy = 0.9565217391304348` (110/115), average
  `3.528s`/document (+51% vs. the incumbent's `2.330s`). All 5 field
  failures are `employee.first_name` (0/5 correct). Cross-checked against
  the same 5 documents in the Tesseract 600-document robustness rerun: all
  5 were 100% correct under the PSM 3 + PSM 6 incumbent alone — a clean,
  unambiguous regression.
- Root cause: the employee-name OCR fallback (`_zone_text` in
  `parser_2026.py`) joins every observation in its target zone rather than
  picking one (unlike the first-match logic used for EIN/money fields).
  PSM 11's supplemental pass and PSM 3's main pass both land readings of
  the same name in the shared zone, so `_zone_text` concatenates both
  (e.g. expected `"Steven"`, predicted `"Steven Steven D"`).
- `employer.ein` and federal Boxes 3/5/6 (the other four approved target
  fields) all stayed 5/5 correct, and Box 13/SSN (non-target fields) also
  stayed 5/5 correct — confirming the readiness work's row-grouping
  isolation and zone-targeting protections performed exactly as designed;
  the regression is isolated to the name zone's join-based fallback logic.
- **This configuration is NOT marked eligible for the 150-document
  benchmark**, per this task's explicit stop-and-document instruction. Two
  candidate fixes were identified but not implemented: make `_zone_text`
  resilient to overlapping observation sources, or drop the name zone from
  PSM 11's target set. Updated
  `docs/experiments/pipeline-a-extraction-history.md` and
  `docs/project-state.md` (Immediate Next Experiment, Current Pipeline A
  Configuration, Current Known Weaknesses, Completed Phase History)
  accordingly. Did not run 150 or 600 documents, PaddleOCR, or any other
  configuration, per this task's explicit scope.

### Phase 4E - Targeted Supplemental PSM 11 Narrowed to Drop the Name Zone

- Applied the smaller of the two candidate fixes from the disqualified
  smoke above: removed the employee-name zone from
  `_SUPPLEMENTAL_TARGET_ZONES[11]` (`src/w2_pipeline/extraction/ocr.py`)
  rather than redesigning `_zone_text`. PSM 11 supplemental targeting is
  now `employer.ein` and federal Boxes 3/5/6 only — the four fields that
  use first-match fallback logic and were unaffected by the duplication
  bug. Updated the one affected unit test
  (`test_targeted_psm_11_supplemental_pass_is_scoped_to_approved_fields`);
  full suite 143 tests passing (unchanged count).
- Re-ran the identical 5-document clean-render smoke
  (`--tesseract-supplemental-psm 6,11`) with the narrowed config. Added
  `data/evaluation/results/phase4e_tesseract_supplemental_psm11_no_name_zone_smoke_5.json`
  and the matching `.md`; the disqualified smoke and all other historical
  artifacts were left untouched.
- Result: `field_accuracy = 1.0` (115/115), average `3.656s`/document
  (+56.9% vs. the incumbent). Same 5 documents as the disqualified smoke;
  cross-checked against the incumbent's result for these exact documents,
  all 115 fields were already 100% correct under PSM 3 + PSM 6 alone —
  **no regression**, but also **no primary-path failures to recover from**,
  so this sample cannot demonstrate a recovery benefit either way.
- Per the decision rule for this task ("no regression but no demonstrated
  recovery benefit -> do not automatically advance; document that the
  smoke did not prove value"), **this configuration is not marked eligible
  for the clean-150 benchmark.** The regression is fixed, but promotion
  would need a separate, explicit decision with a sample large enough to
  actually observe recovery on `employer.ein`/Box 3/5/6 (occurring at
  roughly a 1-1.3% document rate per the incumbent's 150-document numbers).
  Updated `docs/contracts/extraction-pipeline-a.md`,
  `docs/experiments/pipeline-a-extraction-history.md`, and
  `docs/project-state.md` accordingly. Did not run 150 or 600 documents,
  PaddleOCR, or any other configuration.

### Phase 4E - Targeted Supplemental PSM 11 Recovery Diagnostic (Meaningful Recovery Demonstrated)

- Ran a targeted diagnostic, not an accuracy benchmark: selected, from the
  150-document Tesseract incumbent result, every document where PSM 3 +
  PSM 6 failed at least one of PSM 11's four target fields
  (`employer.ein`, Boxes 3/5/6) — 6 known failures across 5 documents —
  and reran exactly those documents with PSM 11 enabled
  (`--tesseract-supplemental-psm 6,11`) via a temporary manifest (built
  and deleted for this run only).
- Added `data/evaluation/results/phase4e_tesseract_supplemental_psm11_recovery_diagnostic_5.json`
  and the matching `.md`; all historical artifacts, including both prior
  PSM 11 smokes, were left untouched.
- Result (aggregate `field_accuracy = 0.9652173913043478`, deliberately
  **not representative** of anything but this biased sample): **4 of 6
  (66.7%) known target-field failures recovered** — `employer.ein` on two
  documents and `box_5`/`box_6` on one document, all previously
  `"missing"`, all now exact matches. The 2 unrecovered failures were both
  `"mismatch"`-kind (the primary path already produced a wrong,
  non-`None` value), which the existing `None`-only fallback gate cannot
  address regardless of what PSM 11 reads — a clean, fully explained
  pattern: 100% recovery on `"missing"`-kind failures, 0% on
  `"mismatch"`-kind.
- Zero leakage confirmed under this harder sample: one document's two
  pre-existing, unrelated failures outside PSM 11's target set
  (`employee.first_name`/`middle_initial`) were bit-for-bit unchanged.
- Per the decision rule for this task, this is meaningful recovery.
  **Targeted supplemental PSM 11 (`employer.ein` + Boxes 3/5/6) is marked
  justified for a controlled clean-150 benchmark**, which was **not** run
  as part of this diagnostic task — it remains the mechanical next step.
  The incumbent configuration is unchanged; no promotion was made.
  Updated `docs/contracts/extraction-pipeline-a.md`,
  `docs/experiments/pipeline-a-extraction-history.md`, and
  `docs/project-state.md` accordingly. Did not run the full 150 or 600
  documents, PaddleOCR, or any other configuration.

### Phase 4E - Controlled Clean-150 Benchmark for Targeted Supplemental PSM 11 (Confirmed Gain, Not Promoted)

- Acted on the recovery diagnostic's justification: main PSM 3 + targeted
  supplemental PSM 6 + targeted supplemental PSM 11 (`employer.ein`/Box
  3/5/6 only), full 150-document external clean-render set, checkbox
  vision enabled.
- Added `data/evaluation/results/phase4e_tesseract_supplemental_psm11_external_clean_150.json`
  and the matching `.md`; the incumbent and all three prior PSM 11
  artifacts (both smokes and the diagnostic) were left untouched.
- Result: `field_accuracy = 0.9939130434782608` (3,429/3,450), up from the
  incumbent's `0.9927536231884058` (3,425/3,450), `failed_documents = 0`,
  average `3.541479775440033` seconds/document (**+51.98%** vs. the
  incumbent's `2.330s`).
- Per-field: `employer.ein` 98.67% -> **100.0%** (+2), `box_5` 99.33% ->
  **100.0%** (+1), `box_6` 98.67% -> 99.33% (+1), `box_3` unchanged
  (99.33%, its one failure is `"mismatch"`-kind and structurally
  unrecoverable by the existing `None`-only fallback gate). No other
  field changed.
- Document-level cross-check against the incumbent confirms exactly the
  4 recoveries the diagnostic predicted and **zero new failures anywhere**
  — the regressed-field set is empty, and all 21 remaining failures have
  bit-for-bit identical predictions to the incumbent.
- Conclusion: a real but narrow accuracy gain (0.116 percentage points, 3
  of 150 documents affected) at a substantial, universal latency cost
  (+52% per document, on every document regardless of benefit). Per the
  decision rule for this task, this is recorded as confirmed with zero
  regressions, **not automatically promoted** — the incumbent
  configuration is unchanged, and the accuracy/latency trade-off is left
  for the user to decide. Updated
  `docs/contracts/extraction-pipeline-a.md`,
  `docs/experiments/pipeline-a-extraction-history.md`, and
  `docs/project-state.md` accordingly. Did not run 600 documents,
  PaddleOCR, or any other configuration.

### Phase 4E - Rotated Employee-Name Label-Bleed Investigation (Diagnosis Only)

- Investigation only, per explicit task scope: no fix implemented, no
  150/600-document benchmark run, no incumbent change, no PaddleOCR
  settings/parser/adapter/checkbox-vision/ground-truth modification.
- Added `docs/experiments/phase4e-paddle-rotation-name-investigation.md`,
  a full diagnostic report tracing the `rotated_png`
  `employee.first_name` failure (0/150 correct, predicted values like
  `"Lori"` -> `"Lori e Employee's first name and initial"`) from raw
  PaddleOCR `predict()` output through the adapter to the parser, across
  3 representative documents.
- **Root cause: the shared, backend-neutral employee-name OCR fallback**
  (`_apply_ocr_employee_layout_fallbacks`/`_zone_text` in
  `parser_2026.py`) uses a fixed target zone normalized against
  detected-text extent rather than true image pixels. Under rotation, the
  printed Box e field label's normalized `y` position crosses the zone's
  `0.505` floor (clean: `0.4852`, outside; rotated: `0.5060`, inside —
  identical across 4 documents checked), so `_zone_text` joins the label
  into the name value. The missing middle initial follows mechanically:
  `split_first_name_and_initial` only checks the last whitespace-split
  token, which the merged label's trailing words push the true initial
  out of. PaddleOCR's raw output was verified correct before any
  adapter/parser code runs (label and name are separate, correctly-
  recognized, non-overlapping entries), ruling out Paddle's detection/
  recognition and the adapter's coordinate conversion.
- **Correction to prior documentation**: this was previously reported as
  PaddleOCR-specific ("Tesseract's rotated `employee.first_name` is
  53.67%, weak but not zeroed") — that figure was Tesseract's aggregate
  across all four variants, not rotated-only. Recomputed directly:
  Tesseract is also 0/150 (0%) on rotated `employee.first_name` and
  32/150 (21.33%) on rotated `employee.middle_initial`, identical to
  PaddleOCR — both backends share the identical bug, since it lives in
  shared parser code. Corrected `docs/project-state.md`'s "Current
  Phase," "Immediate Next Experiment," and "Current Known Weaknesses"
  sections, removing a caveat that had previously appeared to weigh
  specifically against PaddleOCR GPU in the incumbent-promotion
  comparison.
- Recommended fix (not implemented): filter the known, static Box e
  label text out of zone-filtered observations — backend-neutral, no
  ratio recalibration needed. Rejected as primary: renormalizing zone
  ratios against true image dimensions, which would require
  recalibrating every zone constant in the fallback system, not just this
  one. Updated `docs/experiments/pipeline-a-extraction-history.md` and
  `docs/project-state.md` accordingly.

### Phase 4E - Rotated Employee-Name Label-Bleed Fix (Implemented and Verified)

- Implemented the investigation's recommended fix in
  `src/w2_pipeline/extraction/parser_2026.py`: `_clean_layout_token`
  (shared by the employee first-name/middle-initial, last-name, and
  suffix OCR fallback zones) now filters Box e's known, static printed
  label vocabulary (`_BOX_E_LABEL_WORDS`) at the **word level** — matching
  words are stripped out of a multi-word observation and the survivors
  rejoined, rather than only exact-matching a token's whole string as
  before. Apostrophe variants (straight `'` vs. Tesseract's curly `’`)
  are normalized before comparison.
- Works identically whether the label arrives as one merged observation
  (PaddleOCR's line-level recognition, e.g. `"e Employee's first name and
  initial"`) or as several separate word tokens interleaved with the name
  by x-position (Tesseract's word-level recognition, e.g. `"Steven"`,
  `"Employee's"`, `"D"`, `"first"`, `"name"`, `"and"` as six distinct
  observations). No OCR-backend branching was added anywhere. No OCR
  settings, checkbox vision, ground truth, evaluator, or ratio-zone
  constant were changed — the smallest fix the investigation recommended.
- Added 6 focused tests to `tests/extraction/test_parser_2026.py`: a
  clean name unaffected by the filter; a PaddleOCR-style merged label
  with a middle initial (`"Steven D"` + `"e Employee's first name and
  initial"` -> `first_name="Steven"`, `middle_initial="D"`); the same
  without a middle initial (`"Lori"` -> `first_name="Lori"`); an accented
  name surviving the filter untouched (`"Jesús"`); a Tesseract-style
  fragmented/interleaved label recovering `"Steven"`/`"D"` correctly; and
  a regression check confirming last name and suffix zones are
  unaffected. Full suite: 149 tests passing (143 before this task, zero
  regressions).
- Real-pipeline smoke (not a benchmark): ran `PipelineAExtractor` directly
  against the actual rotated source images for 3 representative
  documents × 2 backends (`symage_900000` no-initial, `symage_900001`
  with-initial, `symage_900026` accented-with-initial). 5/6 exact
  matches. The one non-match (Tesseract on `symage_900026`, predicting
  `"Jesus"` instead of `"Jesús"`) is confirmed **not** a regression:
  Tesseract already misread the same accent on that document's clean
  render (a separate, pre-existing limitation); the middle initial was
  still correctly recovered on that document, confirming the label-bleed
  component is fully resolved.
- Per this task's explicit scope: no 150-document or 600-document
  benchmark was run, no PSM 11 experiments were touched, and no Pipeline
  B work was done. The historical 150/600-document benchmark artifacts
  for both backends now predate this fix for `employee.first_name`/
  `employee.middle_initial` — rerunning them to obtain corrected
  authoritative numbers is the natural next mechanical step. Updated
  `docs/experiments/pipeline-a-extraction-history.md` and
  `docs/project-state.md` accordingly (Current Phase, Immediate Next
  Experiment, Current Known Weaknesses, Completed Phase History).

### Phase 4E - PaddleOCR GPU 150-Document `rotated_png` Rerun (Confirms Box-e Fix, Finds a New Bug)

- Reran PaddleOCR GPU against the full 150-document `rotated_png`
  variant only (checkbox vision enabled, current parser including the
  Box e label fix) to confirm that fix at scale.
- Added `data/evaluation/results/phase4e_paddleocr_gpu_box_e_fix_rotated_150.json`
  and the matching `.md`; the historical 600-document PaddleOCR artifact
  was not modified.
- Result vs. the historical PaddleOCR GPU rotated subset (90.49%,
  3,122/3,450): `employee.first_name` **0/150 -> 150/150 (100%, fully
  resolved)**; `employee.middle_initial` 32/150 -> 144/150 (96.0%,
  substantially improved, not fully resolved);
  `box_13.retirement_plan` unchanged at 60.0% (a separate, already-
  documented limitation, correctly unaffected); overall
  `field_accuracy = 0.9808695652173913` (3,384/3,450), up from 90.49%,
  average `1.427s`/document, `failed_documents = 0`. Zero regressions
  anywhere, confirmed by an exhaustive document-and-field-level diff (262
  fields recovered, 0 newly failing).
- **New finding, reported plainly per this task's instruction not to hide
  or normalize evaluator differences: a real, narrow regression in the
  Box e label fix itself, not a pre-existing limitation.** All 6
  remaining `employee.middle_initial` failures share `expected: "E"` —
  confirmed to be exactly the 6 of 118 documents whose true middle
  initial is `"E"`, and no other letter. Root cause:
  `_is_box_e_label_word` lowercases its input before matching against
  `_BOX_E_LABEL_WORDS` (which includes lowercase `"e"`, the box-letter
  marker), so it also incorrectly discards a legitimate capital `"E"`
  initial. Not variant-specific — plausibly also affects
  clean/compressed/blurred documents with a `"E"` middle initial, not
  verified as part of this `rotated_png`-scoped task. Recommended fix
  (small, low-risk, **not implemented**, per this task's explicit scope):
  remove the redundant `"e"` entry from `_BOX_E_LABEL_WORDS`.
- No clean/compressed/blurred variant, no full 600-document benchmark, no
  Tesseract, no PSM 11, and no Pipeline B work were performed. Updated
  `docs/experiments/pipeline-a-extraction-history.md` and
  `docs/project-state.md` accordingly (Current Phase, Immediate Next
  Experiment, Current Known Weaknesses, Completed Phase History).

### Phase 4E - Box e Filter Capital-E Regression Fix (Implemented and Verified)

- Fixed the capital-`"E"` middle-initial regression found by the
  preceding `rotated_png` rerun: `src/w2_pipeline/extraction/parser_2026.py`
  no longer includes `"e"` in `_BOX_E_LABEL_WORDS`, so
  `_is_box_e_label_word` no longer lowercase-matches a legitimate capital
  `"E"` middle initial against the box-letter marker. The marker case
  remains correctly handled by the pre-existing, case-sensitive
  `_SINGLE_CHAR_JUNK` check alone. No other line changed; no OCR-backend
  branching, no OCR-settings change, no zone recalibration, no
  checkbox-vision change.
- Verified directly: `_clean_layout_token("E") -> "E"`,
  `_clean_layout_token("e") -> None`,
  `_clean_layout_token("e Employee's first name and initial") -> None`,
  `_clean_layout_token("Lori e Employee's first name and initial") ->
  "Lori"`, `_clean_layout_token("Steven E e Employee's first name and
  initial") -> "Steven E"`.
- Added 10 focused tests to `tests/extraction/test_parser_2026.py`:
  direct `_clean_layout_token` checks for `"E"` preservation and
  continued `"e"` filtering (standalone and merged-label); an end-to-end
  PaddleOCR-style merged-label case with a capital-E initial recovering
  `first_name="Steven"`/`middle_initial="E"`; a parametrized non-
  regression check across `"D"`/`"J"`/`"K"`/`"W"`/`"M"` initials; and two
  more non-regression checks reconfirming the original no-initial and
  Tesseract-fragmented cases from the prior fix task. Full suite: 159
  tests passing (149 before this task, zero regressions).
- Real-pipeline verification (not a benchmark): `symage_900023` (ground
  truth `first_name="James"`, `middle_initial="E"` — the exact bug case)
  via PaddleOCR GPU against the actual rotated source image now correctly
  extracts both fields; `symage_900001` (`"Steven"`/`"D"`) confirmed
  unaffected.
- Per this task's explicit scope: no 150-document or 600-document
  benchmark was run to requantify the `rotated_png` numbers with both Box
  e fixes in place — the prior rerun's `employee.middle_initial` figure
  (144/150, 96.0%) now undercounts by exactly the 6 documents this fix
  addresses; a rerun to confirm the corrected number is the natural next
  mechanical step. No Tesseract benchmark, no PSM 11 work, and no
  Pipeline B work were performed. Updated
  `docs/experiments/pipeline-a-extraction-history.md` and
  `docs/project-state.md` accordingly (Current Phase, Immediate Next
  Experiment, Current Known Weaknesses, Completed Phase History).

### Phase 4E - PaddleOCR GPU 150-Document `rotated_png` Rerun (Post Capital-E Fix, Fully Confirmed)

- Reran PaddleOCR GPU against the full 150-document `rotated_png`
  variant with both Box e fixes in place (label-bleed filter + capital-E
  denylist correction), closing out the reconfirmation the capital-E fix
  task flagged as outstanding.
- Added `data/evaluation/results/phase4e_paddleocr_gpu_capital_e_fix_rotated_150.json`
  and the matching `.md`; all prior `rotated_png` PaddleOCR artifacts
  (including the immediately preceding pre-capital-E-fix result) were
  left untouched.
- Result vs. the pre-capital-E-fix rerun (90.49% original, 98.09%
  post-label-bleed-fix, 3,384/3,450): `employee.middle_initial`
  **144/150 -> 150/150 (100%)**, all 6 capital-`"E"` failures recovered
  by exact document ID (`symage_900023`/`900028`/`900047`/`900063`/
  `900067`/`900080`, matching the 6 identified previously);
  `employee.first_name` unchanged at 150/150 (100%);
  `box_13.retirement_plan` unchanged at 90/150 (60.0%, a separate
  limitation, correctly unaffected); overall `field_accuracy =
  0.9826086956521739` (3,390/3,450), up exactly +6 fields; average
  `1.342s`/document (within normal GPU run-to-run variance).
  `failed_documents = 0`.
- Zero regressions, confirmed by an exhaustive document-and-field-level
  diff: exactly 6 fields recovered, 0 newly failing.
- Conclusion: both Box e fixes are now fully verified at 150-document
  scale on PaddleOCR GPU's `rotated_png` variant. The full 600-document
  benchmark and the equivalent Tesseract rerun remain outstanding and
  were not run, per this task's explicit scope; no PSM 11 work and no
  Pipeline B work were performed. Updated
  `docs/experiments/pipeline-a-extraction-history.md` and
  `docs/project-state.md` accordingly (Current Phase, Immediate Next
  Experiment, Current Known Weaknesses, Completed Phase History).

### Phase 4E - Tesseract Incumbent 150-Document `rotated_png` Rerun (Post Both Box e Fixes, Confirms Backend-Neutrality)

- Reran the Tesseract incumbent (main PSM 3 + supplemental PSM 6,
  unchanged) against the full 150-document `rotated_png` variant with
  both Box e fixes in place, confirming the fix on the second backend to
  match the two PaddleOCR GPU `rotated_png` reruns.
- Added `data/evaluation/results/phase4e_tesseract_capital_e_fix_rotated_150.json`
  and the matching `.md`; the historical 600-document Tesseract artifact
  and all other historical results were left untouched.
- Result vs. the historical Tesseract rotated subset (89.97%,
  3,104/3,450): `employee.first_name` 0/150 -> **146/150 (97.33%)**;
  `employee.middle_initial` 32/150 -> **147/150 (98.0%)**;
  `box_13.retirement_plan` unchanged at 90/150 (60.0%, correctly
  unaffected); overall `field_accuracy = 0.9753623188405797`
  (3,365/3,450), up +7.6 percentage points, closely matching PaddleOCR's
  own gain; average `2.361s`/document, essentially unchanged from the
  historical aggregate rate (no latency regression). Zero regressions
  (261 fields recovered, 0 newly failing, confirmed by exhaustive diff).
- **The small remaining gap is fully explained and confirmed pre-existing,
  not new**: 3 of 4 remaining `first_name` failures are Tesseract's
  well-documented accent-recognition limitation (`"Jesús"` ->
  `"Jesus"`, etc., already present on these documents' clean renders); the
  4th (`"Logan"`) improved from label-bleed garbage to a clean `None` but
  Tesseract's OCR still never detects the name in that document under
  rotation. All 3 remaining `middle_initial` failures are bit-for-bit
  unchanged `"missing"`-kind failures already present before either fix.
- Conclusion: both Box e fixes are confirmed genuinely backend-neutral —
  Tesseract and PaddleOCR GPU share the identical bug via
  `_clean_layout_token` and both benefit substantially; Tesseract's
  remaining gap versus PaddleOCR's clean 150/150 is separate,
  pre-existing OCR quality, not a fix limitation. The full 600-document
  benchmark for either backend remains outstanding and was not run, per
  this task's explicit scope; no PaddleOCR run, no PSM 11 work, and no
  Pipeline B work were performed. Updated
  `docs/experiments/pipeline-a-extraction-history.md` and
  `docs/project-state.md` accordingly (Current Phase, Immediate Next
  Experiment, Completed Phase History).

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
