# Changelog

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
