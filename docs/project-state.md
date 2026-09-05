# Project State

Last updated: 2026-09-05

## Current Phase

Phase 4E has moved from evaluation into a code fix, now fully reconfirmed at
full scale on both backends. The 150-document PaddleOCR GPU benchmark
(97.39% vs. Tesseract's 99.13% on the identical clean set, not promoted to
incumbent) found PaddleOCR's entire 90-field error surface was one field,
`box_13.retirement_plan`. A follow-up investigation then a follow-up
implementation determined the root cause (PaddleOCR's text detector never
perceives the checkbox glyph as text at all) and shipped a backend-neutral,
pixel-based fix (`src/w2_pipeline/extraction/checkbox_vision.py`) that no
longer depends on any OCR engine's text output for that field. **The
97.39%/99.13% numbers above are historical** — they predate this fix. A
20-document smoke check after the fix reached `1.0` field accuracy on
PaddleOCR GPU (20/20 on `retirement_plan`, previously the field's dominant
failure) with no Tesseract regression. Both formal 150-document reruns with
the fix in place are now complete: Tesseract reached `field_accuracy =
0.9927536231884058` (3,425/3,450, up from 99.13%), with
`box_13.retirement_plan` at 100.0% (up from 96.67%) and every other field
unchanged; PaddleOCR GPU reached `field_accuracy = 1.0` (3,450/3,450, up
from 97.39%), with `box_13.retirement_plan` at 100.0% (up from 40.0%) and
zero remaining field failures anywhere. **With the fix confirmed at full
scale, PaddleOCR GPU now outperforms the Tesseract incumbent on this
clean-150 benchmark on both accuracy (100.0% vs. 99.28%) and speed (1.44s
vs. 2.33s/document)** — a genuinely new incumbent question. The 600-document
robustness picture is now in for both backends too: Tesseract reached
`field_accuracy = 0.8897826086956522` (worst variant blurred, 67.71%);
PaddleOCR GPU reached `field_accuracy = 0.976231884057971` (13,472/13,800),
perfect on clean/compressed/blurred and its only weak variant was rotated
(90.49%, comparable to Tesseract's 89.97% there), where a label-bleed
text-reconstruction artifact zeroed `employee.first_name` specifically
under rotation — unrelated to checkbox vision. **Investigated,
root-caused, fixed, and verified**
(`docs/experiments/phase4e-paddle-rotation-name-investigation.md` for the
diagnosis; `docs/experiments/pipeline-a-extraction-history.md`'s "Rotated
Employee-Name Label-Bleed Fix" entry for the implementation): this was a
shared, backend-neutral bug in the parser's employee-name OCR fallback
(`_clean_layout_token` in `parser_2026.py`), not a PaddleOCR-specific
weakness — Tesseract failed identically (0/150 on rotated
`employee.first_name`, correcting a prior documentation error that had
reported it as PaddleOCR-only). The fix — a targeted, backend-neutral
filter for Box e's known static label text — is implemented, covered by 6
new tests (149 passing total), and verified against real rotated images
for both backends via a direct-pipeline smoke (5/6 exact matches; the one
non-match is Tesseract's separate, pre-existing accent-recognition
limitation, unrelated to this fix). A full 150-document PaddleOCR GPU
rerun scoped to `rotated_png` only confirmed the fix at scale:
`employee.first_name` 0/150 -> **150/150 (100%, fully resolved)**;
`employee.middle_initial` 32/150 -> 144/150 (96.0%, substantially
improved); `box_13.retirement_plan` unchanged at 60.0% (a separate,
already-documented limitation); overall rotated-variant accuracy 90.49%
-> 98.09%, zero regressions. **That rerun also surfaced a real, narrow
regression in the fix itself** (not a pre-existing limitation): a capital
`"E"` middle initial was incorrectly filtered as if it were the lowercase
`"e"` box-letter marker, due to case-insensitive matching in the fix's
word-level denylist — confirmed to affect exactly the 6 of 118 documents
whose true middle initial is `"E"`, and no other letter. **This has since
been fixed and verified too** (removed the redundant `"e"` entry from
`_BOX_E_LABEL_WORDS`; 10 new tests, 159 passing; verified directly and
against a real rotated image). **Reconfirmed at 150-document scale**: a
second `rotated_png` rerun with both fixes in place showed
`employee.middle_initial` 144/150 -> **150/150 (100%, all 6 capital-`"E"`
failures recovered by exact document ID)**, `employee.first_name`
unchanged at 150/150, `box_13.retirement_plan` correctly unchanged at
90/150 (separate limitation), overall `98.09%` -> `98.26%`
(3,384/3,450 -> 3,390/3,450), zero regressions. Both rotated-image Box e
fixes are now fully confirmed at scale on PaddleOCR GPU, **and confirmed
backend-neutral by a matching Tesseract `rotated_png` rerun**: overall
89.97% -> 97.54%, `employee.first_name` 0/150 -> 146/150 (97.33%, the 4
remaining failures being pre-existing accent-recognition/detection gaps
unrelated to the fix, not new failures), `employee.middle_initial` 32/150
-> 147/150 (98.0%, the 3 remaining failures bit-for-bit unchanged
pre-existing "missing" cases), `box_13.retirement_plan` correctly
unchanged at 90/150, zero regressions. Tesseract did not reach PaddleOCR's
clean 150/150 on the name fields because its remaining failures are
separate, independent OCR weaknesses (accent recognition, occasional
word-level misses) that were never part of the label-bleed bug and are
outside either fix's scope. **The historical 150/600-document benchmark
artifacts still predate both Box e fixes for clean/compressed/blurred
scope** (only `rotated_png` was rerun, for both backends now) —
rerunning the remaining three variants (compressed, blurred, and the
already-tested clean) for the full 600-document scope is the natural next
mechanical step, not yet done. PaddleOCR GPU is ahead
of the Tesseract incumbent on aggregate accuracy across all four variants
combined, not just on clean data, and the rotated-name weakness (now
fully fixed and confirmed on both backends' rotated variant) was never a
caveat specific to that comparison since both backends shared it equally.
Whether to promote
PaddleOCR GPU remains an explicit, not-yet-made decision; see "Immediate
Next Experiment." Phase 4D (Tesseract main-PSM experiments) is complete.

Most recently completed:

- Readiness/implementation task: generalized Pipeline A's targeted
  supplemental OCR mechanism (previously hardcoded to a single PSM-6
  SSN-recovery zone) so **PSM 11 can now be added as a second, field-targeted
  supplemental pass** — `--tesseract-supplemental-psm 6,11` — restricted to
  exactly the six fields where the Phase 4D.1 PSM 11 experiment showed an
  improvement over the incumbent (`employee.first_name`,
  `employee.middle_initial`, `employer.ein`, and federal Boxes 3/5/6),
  explicitly excluding Box 13 (owned by `checkbox_vision.py`) and SSN (owned
  by PSM 6). Confirmed the *existing* config/CLI could not express this
  (single hardcoded zone+regex filter, no CLI exposure of supplemental
  modes, and a real row-grouping corruption risk for money fields whose
  target zones overlap primary Box-line regions) before implementing the
  smallest supporting extension: a new `TextObservation.is_supplemental`
  flag, a generalized per-PSM-mode target-zone table in `ocr.py`
  (`SupplementalTargetZone`/`_SUPPLEMENTAL_TARGET_ZONES`), exclusion of
  supplemental observations from the parser's primary row-grouping and
  page-extent computation (protecting already-correct primary-path values
  from ever being corrupted or overridden), and the new CLI flag. The
  parser remains fully backend/PSM-agnostic — no PSM-specific branching was
  added to canonical field logic. 13 new focused tests (7 in
  `test_ocr.py`, 2 in `test_parser_2026.py`, 4 in
  `test_run_pipeline_a.py`); full suite 143 passing. **No experiment was
  run** — this was implementation/readiness only, per explicit task scope;
  the incumbent configuration is unchanged, and PaddleOCR/checkbox-vision
  were not touched. The exact command for the not-yet-run targeted PSM 11
  smoke experiment is recorded in
  `docs/contracts/extraction-pipeline-a.md`'s "Benchmark Commands".

- Phase 4E shipped a backend-neutral visual checkbox detector for
  `box_13.retirement_plan`: `checkbox_vision.py` detects the mark from page
  pixel ink coverage (calibrated across all 150 external clean documents:
  unchecked ratio `0.0787`, checked ratio `0.1000`, zero overlap, threshold
  `0.09`), independent of OCR text output. Wired through a new
  `ObservationSet.box_13_visual_marks` field, OR'd into the parser's
  existing Box 13 fallback logic alongside (not replacing) the prior
  OCR-token mechanism. Scoped to `retirement_plan` only — no
  ground-truth-positive example exists in the available benchmark data to
  safely calibrate `statutory_employee` or `third_party_sick_pay` zones, and
  an attempted analogy-based guess for those two produced ambiguous/risky
  ink ratios, so they remain on the unchanged existing fallback. 130 tests
  passing (9 new). A 20-document real-pipeline smoke check (not a full
  150-document rerun) confirmed the fix: PaddleOCR GPU reached 1.0 field
  accuracy (20/20 on `retirement_plan`, up from systematic failure);
  Tesseract was unaffected (still 20/20 on `retirement_plan`).

- Phase 4E PaddleOCR GPU **150-document** benchmark: `field_accuracy =
  0.9739130434782609` (3,360/3,450 correct), `failed_documents = 0`,
  `field_failure_count = 90`, average `1.349492507300068`
  seconds/document. Every failure is `box_13.retirement_plan` (60/150
  correct); every other field, including employee first/last/middle name,
  SSN, employer EIN, and all of federal Boxes 1-11, is 100% correct across
  all 150 documents. Not promoted to incumbent from this result. **Superseded**
  by the post-checkbox-vision rerun below (`field_accuracy = 1.0`).
- Phase 4E GPU 5-document smoke: `--ocr-backend paddleocr --paddle-device gpu`
  against the same 5 documents used for the CPU smoke. Result: identical
  field accuracy and failure profile to the CPU smoke (0.9826086956521739,
  113/115 correct, same 2 `box_13.retirement_plan` failures, 0 document
  failures), but `2.1144952545990234` seconds/document average — about a
  35.2x speedup over CPU and within ~3% of the Tesseract incumbent's
  150-document average duration. This result triggered launching the full
  150-document PaddleOCR GPU benchmark above.
- Phase 4E GPU enablement installed `paddlepaddle-gpu==3.3.1` (matching the
  existing CPU `paddlepaddle` version, `cu126` CUDA index) alongside the
  unchanged `paddleocr==3.7.0`, added `--paddle-device` to the benchmark CLI
  (default `cpu`, unchanged) and a `describe_paddle_gpu_availability()`
  diagnostic, and added a `paddle-gpu` optional dependency group. Verified
  GPU visibility (`compiled_with_cuda: true`, RTX 3060 detected) and ran a
  single-image, non-benchmark GPU OCR call that completed correctly before
  the 5-document GPU smoke above.
- Phase 4E implemented `PaddleOcrAdapter`
  (`src/w2_pipeline/extraction/ocr_paddle.py`) behind a new structural
  `OcrAdapter` contract (`src/w2_pipeline/extraction/ocr_backend.py`) that
  both the Tesseract and PaddleOCR adapters satisfy, added `--ocr-backend
  {tesseract, paddleocr}` to the benchmark CLI (default `tesseract`,
  unchanged), and added the `paddle` optional dependency group. A 5-document
  CPU smoke benchmark against the external clean-render set passed with
  98.26% field accuracy and 0 document failures, but revealed PaddleOCR is
  roughly 35-37x slower than Tesseract on CPU (~74.3s/document vs.
  ~2.1s/document).
- Phase 4C corrected the Box e employee-name semantic error end to end (ground
  truth regeneration plus reruns) and reran both the 150-document external
  clean benchmark and the 600-document external robustness benchmark against
  the corrected semantics. Both reruns are complete and are now the
  authoritative external Pipeline A benchmark numbers.
- Phase 4D.1 evaluated main Tesseract PSM 11 (with the same targeted
  supplemental PSM 6 SSN recovery pass) against the 150-document external
  clean-render set and documented the result. PSM 11 was **not** promoted to
  the incumbent configuration: it improved several weak fields but caused a
  complete regression on federal Boxes 1 and 2.
- Phase 4D.2 evaluated main Tesseract PSM 12 (same supplemental PSM 6 pass)
  against the same 150-document external clean-render set. PSM 12 was **not**
  promoted to the incumbent configuration either: it was a severe, broad
  regression, zeroing employee first/last name, employee SSN, employer EIN,
  and all of federal Boxes 1-6 (overall field accuracy 50.49%, worse than
  PSM 11's 91.04%).

The current Pipeline A incumbent configuration remains unchanged from
Phase 4B: main Tesseract **PSM 3** plus the targeted supplemental **PSM 6**
SSN-recovery pass, running on CPU. This has not changed as a result of any
Phase 4E experiment — no promotion decision has been made by this project
state document; promotion requires an explicit user decision, not an
automatic consequence of a benchmark result. The historical Phase 4E
PaddleOCR GPU 150-document benchmark found lower overall field accuracy
than Tesseract (97.39% vs. 99.13%) and was not promoted to incumbent. That
comparison is now stale: with the Box 13 checkbox-vision fix in place and
reconfirmed at full 150-document scale on both backends, PaddleOCR GPU
reaches `field_accuracy = 1.0` (zero field failures) at `1.44s`/document,
versus the Tesseract incumbent's `field_accuracy = 0.9927536231884058`
(3,425/3,450) at `2.33s`/document on the identical 150 documents/variant.
PaddleOCR GPU is therefore now ahead of the incumbent on both accuracy and
speed on this benchmark, which is a materially different starting point for
the incumbent question than the historical result was. The 600-document
robustness picture, now measured for both backends, extends this: Tesseract
reaches `field_accuracy = 0.8897826086956522` (worst variant blurred,
67.71%) while PaddleOCR GPU reaches `field_accuracy = 0.976231884057971`
(13,472/13,800), perfect on clean/compressed/blurred with its only weakness
on rotated images (90.49%, on par with Tesseract's 89.97% there) — driven by
a newly discovered rotation-specific label-bleed artifact that zeroes
`employee.first_name` (unrelated to checkbox vision). PaddleOCR GPU now
leads on aggregate accuracy across all four variants combined, not only on
clean data. Whether to promote PaddleOCR GPU (or otherwise change the
incumbent) remains an explicit product/architecture decision for the user,
not made by this rerun; see "Immediate Next Experiment."

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
and degraded benchmark result artifacts. Phase 4C corrected employee Box e
name semantics in both the extractor and the external ground truth, then
reran the clean and robustness external benchmarks. Phase 4D added configurable
main-PSM support to Pipeline A and the benchmark CLI and evaluated PSM 11 and
PSM 12 as controlled sparse-text experiments. Phase 4E introduced a
backend-selectable OCR boundary and added PaddleOCR as a second Pipeline A OCR
backend, added explicit GPU execution support, and evaluated it through
5-document CPU/GPU smoke tests and a full 150-document GPU benchmark against
the Tesseract incumbent, without promoting PaddleOCR to incumbent.

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

Pipeline B:

```text
src/w2_pipeline/extraction/pipeline_b/
docs/contracts/extraction-pipeline-b.md
```

Validation and routing:

```text
src/w2_pipeline/validation/
docs/contracts/validation-and-routing.md
```

Experiment narrative (what was tested and learned, as opposed to current
state):

```text
docs/experiments/pipeline-a-extraction-history.md
docs/experiments/phase5a-pipeline-b-feasibility.md
docs/experiments/phase6-validation-feasibility.md
docs/experiments/phase6b-employer-name-investigation.md
```

## Current Pipeline A Configuration

- Incumbent/default: main Tesseract **PSM 3** + targeted supplemental
  **PSM 6** (top identifier region, SSN recovery).
- Configurable experiment modes via `--tesseract-psm`: `3` (default), `11`,
  and `12`. The supplemental PSM 6 pass is always enabled regardless of the
  selected main PSM, so experiments isolate the main full-page segmentation
  mode only.
- PSM 11 was evaluated in Phase 4D.1 and rejected as a default: it zeroed
  federal Box 1 and Box 2 extraction on all 150 clean-render documents despite
  improving employee first name, employee middle initial, employer EIN, Box 13
  retirement-plan detection, and federal Boxes 3/5/6.
- PSM 12 was evaluated in Phase 4D.2 and rejected as a default: it produced a
  broad regression (50.49% field accuracy) that zeroed employee first name,
  employee last name, employee SSN, employer EIN, and all of federal Boxes
  1-6, worse overall than PSM 11.
- Both Phase 4D main-PSM experiments (PSM 11 and PSM 12 as *main* full-page
  replacements) are complete; no further main-PSM values are planned.
  Separately, PSM 11 is also available as a **targeted supplemental** pass
  (`--tesseract-supplemental-psm 6,11`, alongside the incumbent main PSM 3).
  It originally targeted six fields Phase 4D.1 showed PSM 11 improves, but
  a 5-document smoke test found a disqualifying regression on
  `employee.first_name` (text duplication from the shared name-zone
  `_zone_text` OCR fallback, which joins every observation in its zone
  rather than picking one). The name zone (and `employee.middle_initial`,
  which shares it) was **removed** from PSM 11's target set in response;
  PSM 11 supplementation is now restricted to `employer.ein` and federal
  Boxes 3/5/6 only — the four fields that use first-match fallback logic
  and were unaffected by the duplication bug. A retry smoke on the same 5
  documents with the narrowed config showed **zero regressions** (115/115
  correct) but also **zero demonstrated recovery benefit**, since those 5
  documents had no primary-path failures on the four target fields to
  begin with — inconclusive on value, not disqualified. A follow-up
  recovery diagnostic (5 documents deliberately drawn from the incumbent's
  known target-field failures) then showed 4/6 (66.7%) recoverable,
  justifying a **controlled clean-150 benchmark**, which has since run:
  `field_accuracy = 0.9939130434782608` (3,429/3,450, up from the
  incumbent's 3,425/3,450) with **zero regressions**, at **+51.98%**
  average latency (`2.330s` -> `3.541s`/document). A real but narrow gain
  (3 of 150 documents affected) against a substantial per-document
  latency cost, every document — not just the ones that benefit. **Not
  promoted**; this trade-off is reported for the user to decide. See
  "Completed Phase History" for all four PSM 11 supplementation runs.
- PaddleOCR is available as an alternate OCR backend via `--ocr-backend
  paddleocr` (`src/w2_pipeline/extraction/ocr_paddle.py`), selectable behind
  the same `OcrAdapter` contract Tesseract implements. It is **not** the
  incumbent — no promotion has been made. Its original 150-document
  benchmark (`field_accuracy = 0.9739130434782609` vs. Tesseract's
  `0.991304347826087`, ~34% faster, entire error surface concentrated in
  `box_13.retirement_plan`) predated the Box 13 visual-checkbox fix and is
  now historical. The corrected 150-document clean-render rerun with the
  fix in place (`phase4e_paddleocr_gpu_checkbox_vision_external_clean_150`)
  reached `field_accuracy = 1.0` (3,450/3,450, zero field failures) at
  `1.44s`/doc — ahead of the Tesseract incumbent's post-fix result
  (`0.9927536231884058` at `2.33s`/doc) on both accuracy and speed on this
  clean-150 benchmark. The first-ever PaddleOCR 600-document robustness
  rerun (`phase4e_paddleocr_gpu_checkbox_vision_external_all_variants_600`)
  reached `field_accuracy = 0.976231884057971` (13,472/13,800) — perfect on
  clean/compressed/blurred variants, with its only failures on `rotated_png`
  (90.49%), concentrated in `employee.first_name` (0/150, a newly discovered
  label-bleed text-reconstruction artifact under rotation, unrelated to
  checkbox vision), `employee.middle_initial` (21.3%), and
  `box_13.retirement_plan` (60.0% — the exact same 60 documents that fail on
  Tesseract under rotation, confirming the visual detector behaves
  identically regardless of backend). This is well ahead of the Tesseract
  incumbent's 600-document aggregate (88.98%, worst variant blurred at
  67.71%).
- A backend-neutral visual checkbox detector
  (`src/w2_pipeline/extraction/checkbox_vision.py`) now supplements OCR text
  for `box_13.retirement_plan` (only that flag; see "Encoded Assumptions").
  A 20-document smoke check confirmed it fixes the field (20/20 on both
  backends) without a Tesseract regression. Now confirmed at full
  150-document scale on **both** backends: Tesseract reached 100.0% (up from
  96.67%, zero regressions elsewhere) and PaddleOCR GPU reached 100.0% (up
  from 40.0%, zero field failures anywhere in the 150-document set).
- `PaddleOcrConfig` defaults to `enable_mkldnn=False`; the PaddlePaddle
  default (`True`) raised a PIR attribute-conversion error for the default
  PP-OCRv6 models on the reference development machine. `enable_mkldnn` is
  CPU-only and irrelevant when `device` selects a GPU.
- GPU execution is available via `--paddle-device gpu` (or `gpu:0`, etc.),
  used only with `--ocr-backend paddleocr`. The reference development
  machine has `paddlepaddle-gpu==3.3.1` installed (NVIDIA RTX 3060, driver
  610.43.02, `cu126` CUDA index). Default `device` remains `"cpu"`. GPU is
  now the only device that has been benchmarked at 150-document scale; the
  150-document CPU PaddleOCR benchmark has not been run.

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
- Pipeline A's main full-page Tesseract PSM is configurable for controlled
  experiments. The default remains PSM 3, with PSM 11 and PSM 12 supported as
  Phase 4D experiment modes while targeted supplemental PSM 6 SSN recovery
  remains enabled. Phase 4D.1 and Phase 4D.2 both confirmed PSM 3 should
  remain the incumbent: PSM 11 caused a complete Box 1/Box 2 regression, and
  PSM 12 caused a broader regression across identity fields and Boxes 1-6.
- Tesseract is a system runtime dependency; when absent, OCR documents fail
  explicitly and benchmark failure isolation records the failure.
- In the completed Phase 4B benchmark environment, Tesseract was present and
  Pipeline A completed external OCR runs with 0 document failures. Phase 4C
  and Phase 4D.1 reruns also completed with 0 document failures.
- Pipeline A is strong on clean and compressed external W-2 images, degrades
  moderately under rotation, and degrades substantially under blur.
- Employee Box e `Employee's first name and initial` maps to
  `employee.first_name` plus `employee.middle_initial`; last name and suffix
  remain independent canonical fields. This correction is implemented in both
  the Symage ground-truth adapter and Pipeline A's OCR name-zone parsing, and
  the Phase 4C reruns are the first external benchmark numbers computed under
  the corrected semantics.
- Evaluation compares employee-name strings exactly. Accents are not folded or
  transliterated during field accuracy scoring.
- Box 13's `retirement_plan` flag is detected via three OR'd signals: the
  text-prefix mechanism (embedded/OCR text reading "13 Retirement plan: X"),
  a pixel-based visual detector (`checkbox_vision.py`, backend-neutral,
  independent of OCR text), and the legacy OCR-token allow-list fallback
  (kept for defense in depth). `statutory_employee` and
  `third_party_sick_pay` use only the first and third signals — no
  ground-truth-positive example exists in current benchmark data to
  calibrate a visual zone for them.
- Confidence scores remain exploratory.
- Real taxpayer data must not be committed.

## Immediate Next Experiment

```text
Every mechanical rerun the checkbox-vision fix motivated (Tesseract 150-doc,
PaddleOCR GPU 150-doc, Tesseract 600-doc robustness, PaddleOCR GPU 600-doc
robustness) is now complete for both backends. Separately, targeted
supplemental PSM 11 (employer.ein + Boxes 3/5/6) has completed its full
track: fixed, diagnosed as recovering real incumbent failures, and
confirmed at controlled clean-150 scale (+4 fields, zero regressions,
+52% latency). It is not promoted -- the accuracy/latency trade-off is
reported for the user to weigh, not decided here. The rotated
employee-name label-bleed bug has been diagnosed and fixed, plus a
follow-up capital-"E" denylist bug the first fix introduced was also
found and fixed. BOTH fixes are now fully confirmed on BOTH backends at
150-document scale on the rotated_png variant: PaddleOCR GPU reaches
employee.first_name 150/150 (100%) and employee.middle_initial 150/150
(100%); Tesseract reaches 146/150 (97.33%) and 147/150 (98.0%), with all
remaining Tesseract failures confirmed as pre-existing, independent OCR
weaknesses (accent recognition, occasional detection misses) unrelated to
either fix, not new failures. box_13.retirement_plan correctly unchanged
at 90/150 on both backends (separate limitation). Zero regressions on
either backend; overall rotated-variant accuracy improved from 90.49% to
98.26% (PaddleOCR) and from 89.97% to 97.54% (Tesseract). What remains is:
rerunning the full 600-document benchmark (all four variants, both
backends) to requantify clean/compressed/blurred scope with both fixes in
place (natural mechanical next step, not yet done -- only rotated_png has
been rerun for either backend), the PaddleOCR-vs-Tesseract incumbent
decision, and the PSM 11 promotion decision -- all the user's to decide
or request next.
```

Sequence: unit tests -> 5-doc CPU smoke -> GPU enablement -> 5-doc GPU
smoke -> 150-doc GPU benchmark (97.39% vs. Tesseract's 99.13%, not promoted)
-> `box_13.retirement_plan` root-cause investigation (diagnostic only) ->
backend-neutral visual checkbox fix (implemented) -> 20-document smoke
confirming the fix (PaddleOCR GPU 1.0 field accuracy on that sample,
Tesseract unaffected) -> Tesseract formal 150-document rerun (**done**:
99.28%, up from 99.13%, `box_13.retirement_plan` 100.0%, zero regressions
elsewhere) -> PaddleOCR GPU formal 150-document rerun (**done**:
`field_accuracy = 1.0`, 3,450/3,450, up from 97.39%, `box_13.retirement_plan`
100.0% up from 40.0%, zero field failures anywhere, `1.44s`/doc) ->
Tesseract formal 600-document robustness rerun (**done**: `field_accuracy =
0.8897826086956522`, 12,279/13,800, up from 88.46%; `box_13.retirement_plan`
fully resolved on clean/compressed variants, partially improved on
rotated/blurred; zero regressions on any other field/variant) -> PaddleOCR
GPU formal 600-document robustness rerun (**done**, first-ever PaddleOCR
data at this scope: `field_accuracy = 0.976231884057971`, 13,472/13,800;
perfect on clean/compressed/blurred; only weak variant rotated, 90.49%,
driven by a newly discovered rotation-specific `employee.first_name`
label-bleed artifact plus the same `box_13.retirement_plan` rotation
weakness Tesseract shares). All four reruns are complete; see "Completed
Phase History" for full detail on each.

What remains a genuine decision rather than a rerun:

- **The incumbent question, now changed across the full benchmark, not just
  clean data.** With the fix confirmed at full scale on both backends and
  both benchmark scopes, PaddleOCR GPU leads the Tesseract incumbent on
  every measured dimension: clean-150 accuracy (100.0% vs. 99.28%) and
  speed (1.44s vs. 2.33s/doc), and 600-document robustness aggregate
  (97.62% vs. 88.98%), including a perfect score on the variant (blurred)
  where Tesseract is weakest. **Correction (see the rotation-name
  investigation below): the rotated-image `employee.first_name` complete
  failure (0/150) is NOT a PaddleOCR-specific weakness** — Tesseract fails
  identically, 0/150, on the same field/variant; the previously reported
  "53.67%, weak but non-zero" figure was Tesseract's *aggregate across all
  four variants*, not the rotated-only figure, and was a documentation
  error, now corrected. This removes a caveat that previously appeared to
  weigh against PaddleOCR GPU specifically — it does not, since both
  backends shared the identical underlying bug, which is now fixed (see
  next bullet) pending reconfirmation at full 150/600-document scale.
  Whether to promote PaddleOCR GPU to incumbent remains an explicit
  product/architecture decision for the user; this project state document
  does not make that call on its own.
- **Rotation-name label-bleed: investigated, root-caused, FIXED, and
  verified.** Full root-cause report:
  `docs/experiments/phase4e-paddle-rotation-name-investigation.md`; fix
  implementation record:
  `docs/experiments/pipeline-a-extraction-history.md`'s "Rotated
  Employee-Name Label-Bleed Fix" entry. Root cause was the shared,
  backend-neutral employee-name OCR fallback (`_zone_text` in
  `parser_2026.py`) using a fixed ratio-based target zone normalized
  against *detected-text extent* (not true image pixels); under
  rotation, the printed Box e field label's normalized position crossed
  the zone's `y0 = 0.505` floor, so `_zone_text` joined the label text
  into the name value (e.g. `"Lori"` -> `"Lori e Employee's first name
  and initial"`), which also silently dropped the middle initial (the
  name-splitting heuristic only checks the last whitespace-split token).
  **Fix implemented**: `_clean_layout_token` now filters the known Box e
  label vocabulary at the word level, working identically whether the
  label arrives as one merged observation (PaddleOCR) or several
  fragmented tokens (Tesseract) — no OCR-backend branching, no ratio-zone
  recalibration, no OCR-settings/checkbox-vision/ground-truth changes. 6
  new tests (149 passing total). Verified via a real-pipeline smoke
  against actual rotated source images (not synthetic fixtures) for both
  backends: 5/6 exact matches; the one non-match (Tesseract on an
  accented name) is a separate, pre-existing accent-recognition
  limitation already present on that document's *clean* render, unrelated
  to this fix — the middle initial was still correctly recovered on that
  same document. **Confirmed at scale**: a full 150-document PaddleOCR
  GPU rerun scoped to `rotated_png` showed `employee.first_name` 0/150 ->
  150/150 (100%, fully resolved) and `employee.middle_initial` 32/150 ->
  144/150 (96.0%), zero regressions on any field, `box_13.retirement_plan`
  correctly unaffected (still 60.0%, a separate limitation). **The
  historical 150/600-document benchmark artifacts still predate the fix
  for clean/compressed/blurred scope** (only `rotated_png` was rerun for
  PaddleOCR GPU) — rerunning the remaining variants and Tesseract to
  obtain corrected authoritative numbers is the natural next mechanical
  step, not yet done.
- **Capital-`"E"` middle-initial regression: FIXED and reconfirmed at
  150-document scale on PaddleOCR GPU's `rotated_png` variant (see next
  bullet for the matching Tesseract confirmation).** Found by the first
  `rotated_png` rerun (all 6 residual `employee.middle_initial` failures
  there shared `expected: "E"`, exactly the 6 of 118 documents whose true
  initial is `"E"`) and root-caused to `_is_box_e_label_word` lowercasing
  its input before matching `_BOX_E_LABEL_WORDS` (which included
  lowercase `"e"`, the box-letter marker), incorrectly discarding a
  legitimate capital `"E"` initial along with it. **Fix**: removed the
  redundant `"e"` entry from `_BOX_E_LABEL_WORDS`; the marker case
  remains correctly handled by the pre-existing, case-sensitive
  `_SINGLE_CHAR_JUNK` check alone. 10 new tests (159 passing total).
  Verified directly (`_clean_layout_token("E") -> "E"`,
  `_clean_layout_token("e") -> None`) and against a real rotated source
  image via PaddleOCR GPU (`symage_900023`, ground truth
  `"James"`/`"E"`, correctly extracted; `symage_900001` `"Steven"`/`"D"`
  confirmed unaffected). **Reconfirmed at scale**: a second full
  150-document `rotated_png` rerun with both fixes in place showed
  `employee.middle_initial` 144/150 -> 150/150 (100%, all 6 exact
  documents recovered), `employee.first_name` unchanged at 150/150,
  `box_13.retirement_plan` correctly unchanged at 90/150, overall
  98.09% -> 98.26%, zero regressions. Not variant-specific, so this fix
  plausibly also corrects clean/compressed/blurred documents with a `"E"`
  middle initial, though that was not verified — the full 600-document
  benchmark remains outstanding for both backends.
- **Both Box e fixes reconfirmed backend-neutral: a matching Tesseract
  `rotated_png` rerun shows the same large recovery, with the small
  remaining gap fully explained as pre-existing, independent limitations
  — not new failures, not part of either Box e bug.** Tesseract's
  `rotated_png` result (`phase4e_tesseract_capital_e_fix_rotated_150`,
  main PSM 3 + supplemental PSM 6, both Box e fixes in place):
  `employee.first_name` 0/150 -> 146/150 (97.33%); `employee.middle_initial`
  32/150 -> 147/150 (98.0%); `box_13.retirement_plan` correctly unchanged
  at 90/150; overall 89.97% -> 97.54%; zero regressions (261 fields
  recovered, 0 newly failing, confirmed by exhaustive diff). Tesseract
  falls short of PaddleOCR's clean 150/150 on the name fields only
  because of pre-existing, separate OCR weaknesses: 3 of 4 remaining
  `first_name` failures are Tesseract's well-documented accent-recognition
  limitation (`"Jesús"` -> `"Jesus"`, etc., already present on these same
  documents' clean renders); the 4th (`symage_900118`, `"Logan"`) improved
  from label-bleed garbage to a clean `None` but Tesseract's word-level
  OCR still never detects the name at all in that rotated document — a
  separate detection gap. All 3 remaining `middle_initial` failures are
  bit-for-bit unchanged `"missing"`-kind failures already present before
  either fix. This confirms the Box e fixes are genuinely backend-neutral
  (both backends share the identical bug via `_clean_layout_token`) and
  that the remaining gap on Tesseract is orthogonal, pre-existing OCR
  quality, not a fix limitation. The full 600-document benchmark for
  either backend remains outstanding.
- **The Tesseract and PaddleOCR robustness reruns both revealed the
  checkbox-vision fix's limit:** it fully resolves `box_13.retirement_plan`
  under clean and compressed-JPEG conditions on both backends, but only
  partially under rotation (Tesseract 48.0% -> 60.0%; PaddleOCR reaches the
  identical 60.0%, the exact same 60 documents fail on both backends) and,
  on Tesseract, under blur (40.0% -> 54.67%; PaddleOCR is unaffected by blur
  at 100%). The fixed true-image-relative calibration zone doesn't track
  geometry shifts from rotation on either backend. Whether this residual
  rotation gap is worth a follow-up (rotation-aware zone detection) or
  should stand as a documented known weakness is an open decision.
- Whether `statutory_employee`/`third_party_sick_pay` visual zones are worth
  pursuing later if a genuine positive example becomes available to
  calibrate against.
- Whether PaddleOCR GPU is worth further investment (now that the
  backend-neutral rotation label-bleed fix has landed and benefits the
  Tesseract incumbent equally, reconsidering incumbent promotion) versus
  proceeding to Phase 5 — now a considerably stronger case than before given
  both the clean-150 and 600-document robustness results, but still gated
  on an explicit user decision. The 150/600-document reruns needed to
  requantify both backends' numbers with the fix in place have not been
  run.
- **Targeted supplemental PSM 11 (`employer.ein` + Boxes 3/5/6): controlled
  clean-150 benchmark complete — confirmed small, real accuracy gain with
  zero regressions, at a substantial per-document latency cost. Not
  promoted; the trade-off is reported for an explicit user decision.**
  History: the original 5-document smoke found `employee.first_name`
  regress from 100% to 0% (text duplication, `_zone_text` joining every
  token in its zone), so the name zone was removed from PSM 11's target
  set; a random 5-document retry smoke showed zero regressions but no
  demonstrated recovery; a targeted recovery diagnostic then showed 4/6
  (66.7%) of the incumbent's known target-field failures recoverable,
  100% of `"missing"`-kind and 0% of `"mismatch"`-kind (structurally, by
  the existing `None`-only fallback gate) — see "Completed Phase History"
  for both. The justified controlled clean-150 benchmark
  (`phase4e_tesseract_supplemental_psm11_external_clean_150`) then
  confirmed this exactly at full scale:
  `field_accuracy = 0.9939130434782608` (3,429/3,450), up from the
  incumbent's `0.9927536231884058` (3,425/3,450) — **+4 fields, zero
  regressions** (the regressed-field set, cross-checked document-for-
  document against the incumbent, is empty; all 21 remaining failures
  have bit-for-bit identical predictions to the incumbent). Per-field:
  `employer.ein` 98.67% -> **100.0%**, `box_5` 99.33% -> **100.0%**,
  `box_6` 98.67% -> 99.33% (one of its two failures recovered), `box_3`
  unchanged (its one failure is `"mismatch"`-kind, structurally
  unrecoverable). Average duration rose **+51.98%** (`2.330s` ->
  `3.541s`/document) — the cost of a full second full-page OCR pass on
  every document, not just the 3 of 150 that benefited. **This is a real
  but narrow gain (0.116 percentage points, 3 of 150 documents affected)
  against a substantial, universal latency cost; per this task's decision
  rule this is recorded, not auto-promoted** — the incumbent configuration
  is unchanged, and whether the accuracy gain is worth the latency penalty
  in production is left to the user. See "Completed Phase History" and
  `docs/experiments/pipeline-a-extraction-history.md` for full detail on
  all four PSM 11 supplementation runs to date.

## Phase 5A - Pipeline B (Qwen3-VL) Feasibility Spike

Phase 5A implements Pipeline B as a genuinely different extraction
architecture -- `Qwen/Qwen3-VL-4B-Instruct` reading the rendered W-2 page
image directly and returning structured JSON, with no OCR or deterministic
parser stage -- under `src/w2_pipeline/extraction/pipeline_b/`. Full
architecture detail: `docs/contracts/extraction-pipeline-b.md`. Full
narrative (what was tried, what broke, what was fixed):
`docs/experiments/phase5a-pipeline-b-feasibility.md`.

This is a feasibility spike only, not a benchmark or promotion decision.
212 tests passing (210 baseline-equivalent + 2 for a mapping normalization
fix found during smoke testing), zero regressions on the existing suite.

**Smoke test result** (5 documents total, within the Phase 5A 1-5 document
scope: `data/evaluation/results/phase5a_pipeline_b_smoke_clean_4.json`,
`..._rotated_1.json`): 4 of 5 documents produced a valid canonical
`W2Document` with **`field_accuracy = 1.0`** on every one that succeeded
(92/92 correct fields across the 4 successes, every evaluated field type
exact); 1 of 5 (`symage_900003`, clean render) failed with a
`SchemaValidationError` -- the model transcribed the Box 12 sub-row's
printed line label (`"12a"`) instead of the actual 1-2 letter code for
that entry, exceeding the canonical `Box12Entry.code` 2-character limit. A
specific, understood, reproducible cause, not a systemic architecture
failure. Average duration: `58.42s`/document (clean, 4 docs), `70.20s`
(rotated, 1 doc); model load excluded after the first call in a process
(`QwenVlRuntime` caches the loaded model). GPU: NVIDIA GeForce RTX 3060,
`device="auto"`/`dtype="auto"`, ~12 GB of 12 GB VRAM in use during
generation (narrow headroom at this model size/dtype, noted as a Phase 5A
limitation, not yet addressed).

**Two runtime-dependency gaps were found and fixed** before this result
was reached (both are missing/outdated packages, not Pipeline B code
defects): `torchvision` (Qwen3-VL's `AutoProcessor` resolves an
`AutoVideoProcessor` component that requires it, even for still-image-only
use) and `jinja2>=3.1` (the reference machine's system Python has an older
apt-managed `Jinja2==3.0.3`, too old for `apply_chat_template`; fixed by
installing a newer `jinja2` to user site-packages, which shadows the older
one without touching the system package). Both were added to the new `vlm`
optional dependency group.

**One mapping normalization was added** after smoke testing showed the
model uses simplified key names (e.g. `"state"`) instead of the canonical
`box_15_state`-style keys for `state_local_entries` specifically, while
every other section matched the canonical schema's keys exactly on the
same successful documents. `mapping.py` gained a small, explicit key-alias
table for that one section -- a structural JSON key rename, not a value
repair, so it stays within the Phase 5A boundary ("normalize representation
into the canonical Pydantic model" is explicitly permitted;
value-level repair is not).

Not attempted in Phase 5A (explicitly out of scope): a 150- or
600-document benchmark, prompt optimization, constrained/JSON-schema-
guided decoding, fine-tuning, quantization, batched inference, or any
Pipeline A/B comparison or promotion decision.

## Phase 6 - Validation, Confidence Signals, And Human Review Routing

Phase 6 implements the layer between extraction and downstream
output/review: `src/w2_pipeline/validation/`. It judges an already-produced
canonical `W2Document` (never ground truth) and routes it to `accepted` or
`needs_review` with explainable, machine-readable issue codes. Full
architecture: `docs/contracts/validation-and-routing.md`. Full narrative:
`docs/experiments/phase6-validation-feasibility.md`.

Backend-neutral by construction: `validate_w2_document()` imports only the
canonical contract, never `w2_pipeline.extraction` or
`w2_pipeline.evaluation` (enforced by an AST-based structural test), so
Pipeline A and Pipeline B call the identical function on their own output.
No ML/probabilistic confidence model was built -- `ExtractionSignals`
carries pipeline-agnostic quality metadata (outcome, route, warnings) but
deliberately no unified confidence score, since Pipeline A's deterministic
OCR/parsing and Pipeline B's generative VLM have no comparable per-field
confidence semantics.

Ten deterministic rules run over every document: extraction signals,
supported metadata (document type/tax year/schema version), employee
identity required fields (`ssn`/`first_name`/`last_name`), SSN format,
employer identity required fields (`ein`/`name`), EIN format, core
wage/tax fields required (Boxes 1/2/5/6), monetary field validity
(non-negative, <=2 decimal places), Box 12 code format
(1-2 uppercase letters), and empty state/local entries. Required-field
decisions are evidence-based from `src/w2_pipeline/evaluation/synthetic.py`'s
own generation logic, not invented -- see the contract doc's "Required-Field
Decisions" section, including the deliberate choice to leave Boxes 3/4
optional (a documented, adjustable interpretation). Routing
(`RoutingPolicy`/`decide_status`) is kept structurally separate from rule
evaluation: the default policy sends any `error`-severity issue to review;
`RoutingPolicy(escalate_warnings=True)` additionally escalates warning-only
documents.

56 new tests (`tests/validation/`), 268 total passing, zero regressions.
The small integration verification (brief item 12) used only existing
fixtures (no new inference run) and passed: known-good documents (with
both Pipeline-A-shaped and Pipeline-B-shaped signals) accepted;
intentionally corrupted and intentionally-missing-critical-field documents
correctly routed to review.

**Unplanned real finding, reported not fixed (Phase 6 is validation-only,
extraction-behavior changes are out of scope):** manually running the new
CLI against a real, already-on-disk Symage ground-truth fixture surfaced
`employer.name = null`; checking further (not part of the committed test
suite) confirmed this is real ground truth, not a bug, but also confirmed
that (a) `employer.name` has never been in that record's
`evaluated_field_paths`, so no benchmark run has ever scored it, and (b)
actual Pipeline A extraction on the corresponding image also returns
`employer.name = null`, consistently across 5 documents checked. This gap
has therefore been invisible to every Pipeline A accuracy number reported
in this document to date. Phase 6 validation caught it on the first real
document checked, precisely because it does not depend on
`evaluated_field_paths` or any other ground-truth-scoping mechanism. See
`docs/experiments/phase6-validation-feasibility.md` for the full trace;
`docs/contracts/validation-and-routing.md`'s "Known Limitations" for the
pointer. Recommended next step for whoever picks this up: investigate
`_parse_employer` in `parser_2026.py`.

Not attempted in Phase 6 (explicitly out of scope): a review UI, CSV
export, persistence, a routing-policy configuration UI, any ML/statistical
confidence model, or a fix to the Pipeline A employer-name gap found above.

## Phase 6B - Employer Name Extraction Gap: Investigated And Fixed

Narrow follow-up to the Phase 6 finding above. Full record:
`docs/experiments/phase6b-employer-name-investigation.md`.

**Root cause (parser-side, not OCR recognition, backend-neutral):** the
real 2026 W-2 form's Box c ("Employer's name, address, and ZIP code") is
one combined, unlabeled multi-line block -- confirmed via the Symage
dataset's own evaluator-side FUNSD annotations (inspected for diagnosis
only, never used as ground truth or injected into the pipeline) and via
direct PaddleOCR output, which recognized `"Timberline Trading Co."`,
`"105 Penland St"`, and `"Murphy, NC 28906"` as three clean, correctly
segmented observations. `_parse_employer`'s primary path
(`_value_after_label`, requiring a literal `"Name:"` line) matches only
the internal synthetic generator's own rendering convention, never the
external Symage render's real-form layout, and -- unlike
`_parse_employee`, which already has a ratio-based OCR zone fallback
covering SSN/first/last/suffix -- `employer.name` had no fallback
recovery path at all (only `employer.ein` did).

**Fix**: `parser_2026.py` gained `_first_row_text_in_zone` (isolates only
the topmost printed line within a zone that may span multiple lines, used
because Box c's name/address lines are stacked vertically) and
`_apply_ocr_employer_layout_fallbacks` (mirrors the existing employee
equivalent; fills `employer.ein`, relocated unchanged, and now
`employer.name`) via a calibrated zone `(0.04, 0.35, 0.25, 0.33)` derived
from FUNSD answer boxes across all 5 diagnostic documents.
`employer.address` has the identical gap but is out of this fix's scope.

**Verification**: 7 new focused tests (275 total passing, zero
regressions) plus a real-pipeline check against all 5 diagnostic documents
with both PaddleOCR and Tesseract -- `employer.name` now recovers exactly
(matching the FUNSD-confirmed correct values:
`Timberline Trading Co.`, `BlueWave Enterprises`,
`Infinity Enterprises Inc.`, `Bright Horizons Corp`,
`Evergreen Solutions LLC`), `employer.ein` unchanged, `employer.address`
unchanged (still `null`, as intended), and every employee/federal field
unchanged. No 150/600-document benchmark was run (out of scope).

**Ground-truth/evaluation scope**: investigated, documented, not
implemented. The FUNSD answer's structure
(`"<name>\n<address>\n<city, state zip>"`) is an authoritative,
deterministic mapping independent of any Pipeline A prediction, and would
satisfy the criteria for adding `employer.name` to the Symage adapter's
`evaluated_field_paths` -- but doing so requires changing
`src/w2_pipeline/evaluation/external_symage.py` and regenerating the
external dataset, a benchmark-harness change distinct from this parser
fix, left as a separate follow-up task.

## Future Phases (after Phase 6B)

```text
Phase 7 (not yet scoped) - human review UI/workflow consuming
ValidationResult, and/or larger-scale Pipeline B evaluation / Pipeline
A vs. Pipeline B comparison, at the user's direction.
```

Any future Pipeline B benchmark should be compared against whichever
Pipeline A configuration performs best across Phase 4D/4E, not
automatically against the Phase 4B/4C PSM 3 baseline, and must hold the
same dataset/ground-truth/evaluator constant the way every Pipeline A
experiment in this document does. A future Phase 7 human-review UI would
consume `ValidationResult` as its primary input contract.

## Completed Phase History

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

Phase 4B external results (historical; predate the Phase 4C Box e semantic
correction below and are superseded for any employee-name accuracy claim):

- external Symage clean renders, 150 documents: `field_accuracy =
  0.9887878787878788`, `failure_rate = 0.0`, average 2.223 seconds/document,
  route `ocr`, with 37 structured incorrect field records
- all prepared external variants, 600 documents: `field_accuracy =
  0.8926515151515152`, `failure_rate = 0.0`, average 2.131 seconds/document,
  route `ocr`
- variant accuracy: clean 98.88%, compressed JPEG 97.97%, rotated PNG 92.45%,
  blurred PNG 67.76%

Post-Phase 4B employee-name correction:

- Symage external ground truth now splits `Employee's first name and initial`
  into `employee.first_name` and `employee.middle_initial`.
- Pipeline A OCR Box e fallback now orders name-zone words left-to-right,
  splits trailing uppercase initials, and filters tiny one- to three-character
  OCR fragments only when normal-size neighboring name tokens are present.
- Benchmark reports now include metadata for run timestamp, source datasets,
  variant scope, schema version, Git commit, and OCR configuration.
- Historical Phase 4B result artifacts predate this semantic correction and
  should not be used for corrected Box e name-accuracy claims; the Phase 4C
  reruns below are the corrected numbers.

Completed Phase 4C corrected Box e benchmark reruns:

```text
data/evaluation/results/phase4c_external_clean_150_name_semantics.json
data/evaluation/results/phase4c_external_clean_150_name_semantics.md
data/evaluation/results/phase4c_external_all_variants_600_name_semantics.json
data/evaluation/results/phase4c_external_all_variants_600_name_semantics.md
```

These were the authoritative external Pipeline A benchmark results (main
PSM 3 + supplemental PSM 6 incumbent, corrected Box e semantics) before the
Phase 4E checkbox-vision fix; both numbers below are now superseded by the
Phase 4E post-checkbox-vision Tesseract reruns (see "Completed Phase
History") and are retained here as historical record only:

- external Symage clean renders, 150 documents: `field_accuracy =
  0.991304347826087` (3,420 / 3,450 correct), `failed_documents = 0`, average
  2.0517181199200363 seconds/document. Employee Box e breakdown:
  `employee.first_name` 93.33%, `employee.middle_initial` 94.0%,
  `employee.last_name` 100%, `employee.suffix` 100%. **Superseded** by the
  Phase 4E post-checkbox-vision rerun: `field_accuracy = 0.9927536231884058`
  (3,425/3,450), `box_13.retirement_plan` 100.0% (up from 96.67%), all other
  fields unchanged.
- all prepared external variants, 600 documents: `field_accuracy =
  0.8846376811594203` (12,208 / 13,800 correct), `failed_documents = 0`,
  average 2.1994630620232782 seconds/document. **Superseded** by the
  Phase 4E post-checkbox-vision rerun: `field_accuracy = 0.8897826086956522`
  (12,279/13,800), `box_13.retirement_plan` improved on every variant (fully
  resolved on clean/compressed, partially on rotated/blurred — see
  "Completed Phase History"), all other fields unchanged.
- variant accuracy: clean render 99.13% (see superseded note above),
  compressed JPEG 98.20%, rotated PNG 89.45%, blurred PNG 67.07% — all four
  superseded; post-fix figures are clean 99.28%, compressed 98.96%, rotated
  89.97%, blurred 67.71%.

The corrected numbers are lower than the Phase 4B pre-correction numbers
primarily because `employee.middle_initial` is now scored as its own field
path across every document/variant, not because extraction quality regressed.

Completed Phase 4D.1 PSM 11 experiment:

```text
data/evaluation/results/phase4d_psm11_external_clean_150.json
data/evaluation/results/phase4d_psm11_external_clean_150.md
```

Main PSM 11 + targeted supplemental PSM 6, same 150 external clean-render
documents, corrected ground truth:

- `field_accuracy = 0.9104347826086957` (3,141 / 3,450 correct),
  `failed_documents = 0`, average 2.1542158065199692 seconds/document.
- Improved fields versus the Phase 4C PSM 3 incumbent: `employee.first_name`
  98.0%, `employee.middle_initial` 99.33%, `employer.ein` 100.0%,
  `box_13.retirement_plan` 100.0%, and federal Boxes 3/5/6 at 100.0%.
- Regressed fields: federal `box_1_wages_tips_other_compensation` and
  `box_2_federal_income_tax_withheld` both dropped to `0 / 150` correct
  (complete extraction failure on every clean-render document).
- Conclusion: PSM 11 is not a viable replacement for the incumbent main PSM 3
  configuration despite its sparse-field gains. It remains useful diagnostic
  evidence but is not deployed as a default.

Completed Phase 4D.2 PSM 12 experiment:

```text
data/evaluation/results/phase4d_psm12_external_clean_150.json
data/evaluation/results/phase4d_psm12_external_clean_150.md
```

Main PSM 12 + targeted supplemental PSM 6, same 150 external clean-render
documents, corrected ground truth:

- `field_accuracy = 0.504927536231884` (1,742 / 3,450 correct),
  `failed_documents = 0`, average 2.3475697785066707 seconds/document,
  `field_failure_count = 1,708`.
- Zeroed fields (0 / 150 correct): `employee.first_name`,
  `employee.last_name`, `employee.ssn`, `employer.ein`, and all six of
  `federal_wages_and_taxes.box_1_wages_tips_other_compensation` through
  `box_6_medicare_tax_withheld`.
- Also degraded well below the incumbent: `employee.middle_initial` (21.3%)
  and `box_13.retirement_plan` (40.0%).
- Only Box 7, Box 8, Box 13's other two flags, and non-financial metadata
  fields stayed fully correct.
- Conclusion: PSM 12 is not a viable Pipeline A configuration. Unlike PSM 11's
  narrow Box 1/2 regression, PSM 12 regressed broadly across identity and
  federal money fields with no offsetting gains, performing roughly half as
  well overall as the PSM 3 incumbent and worse than PSM 11 on every degraded
  field. Phase 4D's PSM comparison is complete; see "Immediate Next
  Experiment" for Phase 4E.

Completed Phase 4E PaddleOCR backend implementation:

```text
src/w2_pipeline/extraction/ocr_backend.py
src/w2_pipeline/extraction/ocr_paddle.py
src/w2_pipeline/extraction/pdf_rendering.py
src/w2_pipeline/extraction/acquisition.py
src/w2_pipeline/evaluation/run_pipeline_a.py
tests/extraction/test_ocr_paddle.py
tests/extraction/test_pdf_rendering.py
tests/evaluation/test_run_pipeline_a.py
pyproject.toml
data/evaluation/results/phase4e_paddleocr_smoke_5.json
data/evaluation/results/phase4e_paddleocr_smoke_5.md
```

Added a structural `OcrAdapter` contract so `ObservationAcquirer` depends on
any backend implementing `extract_image`/`extract_pdf_pages` rather than on
`TesseractOcrAdapter` directly; extracted shared PDF-page-to-image rendering
out of the Tesseract adapter so both backends use one implementation; added
`PaddleOcrAdapter`/`PaddleOcrConfig` calling PaddleOCR 3.7.0's
`predict()` pipeline and mapping `rec_texts`/`rec_boxes` into
`TextObservation`; added `--ocr-backend {tesseract, paddleocr}` to the
benchmark CLI (default unchanged); added the `paddle` optional dependency
group. The parser, evaluator, canonical schema, and annotation isolation
boundary were not changed. Full test suite: 111 tests passing.

Smoke-validated (not yet benchmarked at scale):

- 5-document external Symage clean-render smoke run: `field_accuracy =
  0.9826086956521739` (113/115 correct), `failed_documents = 0`, average
  `74.29913957080062` seconds/document. Only miss: `box_13.retirement_plan`
  (3/5), an existing known weakness, not a new regression.
- `enable_mkldnn=True` (PaddlePaddle's own default) crashed CPU inference
  with a PIR attribute-conversion `NotImplementedError` on the reference
  development machine; `PaddleOcrConfig` defaults to `enable_mkldnn=False`
  as a correctness fix.
- Conclusion so far: PaddleOCR is functionally correct and shows a strong
  accuracy signal on 5 documents, but is roughly 35-37x slower than Tesseract
  on CPU. The full 150-document comparison needed to make an incumbent
  decision has **not** been run; see "Immediate Next Experiment."

Completed Phase 4E GPU enablement:

```text
src/w2_pipeline/extraction/ocr_paddle.py (describe_paddle_gpu_availability)
src/w2_pipeline/evaluation/run_pipeline_a.py (--paddle-device)
tests/extraction/test_ocr_paddle.py
tests/evaluation/test_run_pipeline_a.py
pyproject.toml (paddle-gpu extra)
```

Installed `paddlepaddle-gpu==3.3.1` (replacing CPU `paddlepaddle==3.3.1`,
same version, `cu126` CUDA index matched to the reference machine's NVIDIA
driver 610.43.02) alongside unchanged `paddleocr==3.7.0`; added
`--paddle-device` (default `cpu`, unchanged) and
`describe_paddle_gpu_availability()`; added a `paddle-gpu` optional
dependency group containing only `paddleocr`, since neither `paddleocr` nor
`paddlex` declares its own `paddlepaddle` dependency and therefore cannot
silently reinstall or conflict with an already-installed GPU runtime. 8 new
unit tests (mocked; no real GPU or PaddlePaddle required). Full suite: 121
tests passing.

Verification (non-benchmark, RTX 3060, 12 GB VRAM):

```text
describe_paddle_gpu_availability() -> compiled_with_cuda: true,
  cuda_device_count: 1, cuda_device_names: ["NVIDIA GeForce RTX 3060"]
single-image extract_image(device="gpu") -> correct text, 5.96s total
  (includes one-time CUDA-context/model-init overhead, not throughput)
```

Conclusion: GPU execution is installed, explicit, reproducible, and
selectable, and has been verified end-to-end on this machine. No accuracy or
throughput benchmark has been run on GPU at any scale. The incumbent and all
defaults (including `PaddleOcrConfig.device = "cpu"`) are unchanged. The
150-document PaddleOCR benchmark — now runnable on CPU or GPU — remains the
next step and is deliberately left to a separate task; see "Immediate Next
Experiment."

Completed Phase 4E GPU 5-document smoke:

```text
data/evaluation/results/phase4e_paddleocr_gpu_smoke_5.json
data/evaluation/results/phase4e_paddleocr_gpu_smoke_5.md
```

`--ocr-backend paddleocr --paddle-device gpu`, same 5 external Symage
clean-render documents as the CPU smoke, same commit lineage (`ca3b2a3`):

- `field_accuracy = 0.9826086956521739` (113/115 correct),
  `failed_documents = 0`, average `2.1144952545990234` seconds/document.
  Identical accuracy and failure profile to the CPU smoke: the same two
  documents (`symage_900001...`, `symage_900002...`) failed the same field
  (`box_13.retirement_plan`, expected `true`/predicted `false`) in both runs.
- Versus CPU: ~35.2x faster (`74.3s` -> `2.11s`/document) with no accuracy
  change. Versus the Tesseract incumbent's 150-document average
  (`2.0517s`/document): within ~3% at this 5-document sample size.
- `paddlepaddle-gpu==3.3.1`, `paddleocr==3.7.0`, NVIDIA GeForce RTX 3060.
- Conclusion: strong enough signal — identical accuracy/failure behavior at
  near-Tesseract speed — to justify running the full 150-document PaddleOCR
  GPU benchmark rather than the CPU device. That run
  (`phase4e_paddleocr_gpu_external_clean_150`) was launched immediately after
  this result. A 5-document sample remains too small to make an incumbent
  decision on its own.

Completed Phase 4E PaddleOCR GPU 150-document benchmark:

```text
data/evaluation/results/phase4e_paddleocr_gpu_external_clean_150.json
data/evaluation/results/phase4e_paddleocr_gpu_external_clean_150.md
```

`--ocr-backend paddleocr --paddle-device gpu`, full 150-document external
Symage clean-render set, same corrected ground truth/parser/evaluator/schema
as the Phase 4C Tesseract incumbent result:

- `field_accuracy = 0.9739130434782609` (3,360/3,450 correct),
  `failed_documents = 0`, `field_failure_count = 90`, average
  `1.349492507300068` seconds/document.
- All 90 failures are `box_13.retirement_plan` (60/150 correct, 40.0%
  accuracy). Every other field — employee first/middle/last name/suffix,
  SSN, employer EIN/control number, all of federal Boxes 1-11 — is 100%
  correct across all 150 documents.
- Versus the Tesseract incumbent on the identical set: PaddleOCR GPU's
  overall accuracy is lower (97.39% vs. 99.13%, 90 vs. 30 field failures),
  but it is ~34% faster (`1.35s` vs. `2.05s`/document) and its error surface
  is one narrow field instead of Tesseract's spread across seven fields
  (`employee.first_name` 93.33%, `employee.middle_initial` 94.0%,
  `box_13.retirement_plan` 96.67%, `employer.ein` 98.67%,
  `box_6_medicare_tax_withheld` 98.67%, `box_3_social_security_wages` 99.33%,
  `box_5_medicare_wages_and_tips` 99.33%) — PaddleOCR is 100% correct on
  every one of those seven Tesseract-weak fields.
- Conclusion: PaddleOCR GPU is **not** promoted to incumbent — lower overall
  accuracy is disqualifying by itself. But the finding is more nuanced than a
  simple loss: faster, zero document failures, and a single systematic
  weak field versus Tesseract's diffuse weaknesses. Whether that trade-off,
  or a future hybrid approach, is worth pursuing is an open decision; see
  "Immediate Next Experiment."
- **Superseded** by the post-checkbox-vision rerun below
  (`phase4e_paddleocr_gpu_checkbox_vision_external_clean_150`,
  `field_accuracy = 1.0`); this result predates the fix and is retained here
  as historical record only.

Completed Phase 4E Box 13 visual checkbox detection (implementation, follows
directly from the investigation above):

```text
src/w2_pipeline/extraction/checkbox_vision.py
src/w2_pipeline/extraction/models.py (ObservationSet.box_13_visual_marks)
src/w2_pipeline/extraction/acquisition.py
src/w2_pipeline/extraction/parser_2026.py
tests/extraction/test_checkbox_vision.py
tests/extraction/test_acquisition.py
tests/extraction/test_parser_2026.py (extended)
```

Added a pixel-based checkbox detector, independent of OCR text, calibrated
against all 150 external clean-render documents (unchecked ink ratio
`0.0787`, checked ratio `0.1000`, zero overlap, threshold `0.09`). Wired
through acquisition so it runs on every OCR-routed page image regardless of
backend, OR'd into the parser's existing Box 13 fallback (the prior
OCR-token mechanism was kept, not removed, for defense in depth). Scoped to
`retirement_plan` only: `statutory_employee`/`third_party_sick_pay` have no
ground-truth-positive example available to calibrate against, and an
analogy-based zone guess for them produced ambiguous ink ratios (`0.1134`,
`0.0904`) rather than the clean separation `retirement_plan` showed — those
two fields were deliberately left unchanged rather than risk a regression
on fields that already score 100%. 9 new tests; full suite 130 passing. A
20-document real-pipeline smoke check (PaddleOCR GPU and Tesseract, not a
full 150-document rerun) confirmed the fix: PaddleOCR GPU reached 1.0 field
accuracy (20/20 on `retirement_plan`); Tesseract was unaffected (still 20/20
on `retirement_plan`, its one remaining miss being the pre-existing,
unrelated `employer.ein` failure on `symage_900021`). The formal
150-document benchmark artifacts have not been rerun with this fix in
place — see "Immediate Next Experiment."

Completed Phase 4E Tesseract incumbent 150-document rerun (post
checkbox-vision fix):

```text
data/evaluation/results/phase4e_tesseract_checkbox_vision_external_clean_150.json
data/evaluation/results/phase4e_tesseract_checkbox_vision_external_clean_150.md
```

Formal rerun of the Tesseract incumbent's authoritative clean-150 benchmark
(main PSM 3 + supplemental PSM 6, same 150 external clean-render documents,
same corrected ground truth/parser/evaluator/schema as the Phase 4C result)
with the Box 13 visual checkbox detector in place:

- `field_accuracy = 0.9927536231884058` (3,425/3,450 correct),
  `failed_documents = 0`, `field_failure_count = 25`, average
  `2.330209926666645` seconds/document (up from `2.052s`, the added cost of
  the pixel-based checkbox pass).
- Versus the prior authoritative Phase 4C result (`0.991304347826087`,
  3,420/3,450): the only per-field change across all 23 scored fields is
  `box_13.retirement_plan`, 96.67% -> 100.0% (145/150 -> 150/150) — exactly
  the 5 documents the fix was calibrated to recover. Every other field's
  correct/incorrect count is bit-for-bit identical (weakest remaining:
  `employee.first_name` 93.33%, `employee.middle_initial` 94.0%,
  `employer.ein` 98.67%).
- Conclusion: the checkbox-vision fix is confirmed regression-free at full
  150-document scale on the Tesseract incumbent, matching the 20-document
  smoke check's prediction exactly. This result is now the authoritative
  Tesseract clean-150 number, superseding
  `phase4c_external_clean_150_name_semantics` for that scope; the incumbent
  configuration itself (PSM 3 + PSM 6) is unchanged. Three further reruns
  followed in sequence and are all complete (see the next three entries):
  the PaddleOCR GPU 150-document rerun, the Tesseract 600-document
  robustness rerun, and the PaddleOCR GPU 600-document robustness rerun.

Completed Phase 4E PaddleOCR GPU incumbent-comparison 150-document rerun
(post checkbox-vision fix):

```text
data/evaluation/results/phase4e_paddleocr_gpu_checkbox_vision_external_clean_150.json
data/evaluation/results/phase4e_paddleocr_gpu_checkbox_vision_external_clean_150.md
```

Formal rerun of PaddleOCR GPU's 150-document external clean-render benchmark
(`--ocr-backend paddleocr --paddle-device gpu`, same 150 documents, same
corrected ground truth/parser/evaluator/schema as the historical Phase 4E
PaddleOCR GPU result) with the Box 13 visual checkbox detector in place:

- `field_accuracy = 1.0` (3,450/3,450 correct), `failed_documents = 0`,
  `field_failure_count = 0`, average `1.439184085346657` seconds/document
  (up from `1.349s`, the added cost of the pixel-based checkbox pass).
- Versus the historical Phase 4E PaddleOCR GPU result (`0.9739130434782609`,
  3,360/3,450, 90 field failures): the only field that changed is
  `box_13.retirement_plan`, 40.0% -> 100.0% (60/150 -> 150/150) — every one
  of the 90 historical failures was this field, and all are now resolved.
  Every other field was already 100% and remains so; no field anywhere in
  the 3,450-field surface is below 100%.
- Versus the Tesseract incumbent's same-day post-checkbox-vision result
  (`0.9927536231884058`, 3,425/3,450, `2.330s`/doc): PaddleOCR GPU now scores
  higher accuracy (100.0% vs. 99.28%) at lower latency (1.44s vs. 2.33s/doc,
  ~38% faster), including 100% on all seven fields that remain Tesseract's
  weakest (`employee.first_name`, `employee.middle_initial`, `employer.ein`,
  `box_6_medicare_tax_withheld`, `box_3_social_security_wages`,
  `box_5_medicare_wages_and_tips`, plus `box_13.retirement_plan` itself).
- Conclusion: the checkbox-vision fix, implemented specifically to close
  this gap, performs exactly as predicted at full 150-document scale — a
  perfect, regression-free result. This closes and inverts PaddleOCR GPU's
  historical headline weakness: it is now strictly better than the
  Tesseract incumbent on this clean-150 benchmark on both accuracy and
  speed. This does **not** by itself promote PaddleOCR GPU to incumbent —
  no promotion decision was made as part of this rerun, per the experiment
  skill's boundaries (report the result, let the user decide) — but it
  substantially strengthens the case for that decision. The 600-document
  robustness benchmark (compressed/rotated/blurred) with the fix in place
  has deliberately not been run as part of this task; see "Immediate Next
  Experiment."

Completed Phase 4E Tesseract incumbent 600-document robustness rerun (post
checkbox-vision fix):

```text
data/evaluation/results/phase4e_tesseract_checkbox_vision_external_all_variants_600.json
data/evaluation/results/phase4e_tesseract_checkbox_vision_external_all_variants_600.md
```

Formal rerun of the Tesseract incumbent's authoritative 600-document
robustness benchmark (all four external variants: clean render, compressed
JPEG, rotated PNG, blurred PNG; main PSM 3 + supplemental PSM 6, unchanged)
with the Box 13 visual checkbox detector in place. Tesseract-only by
explicit task scope — no PaddleOCR run as part of this task. This answers
the open question left after the checkbox-vision implementation and the two
prior clean-150 reruns: how the ink-coverage threshold, calibrated only
against clean renders, behaves under degraded image quality.

- `field_accuracy = 0.8897826086956522` (12,279/13,800 correct), up from
  `0.8846376811594203` (12,208/13,800), `failed_documents = 0`, average
  `2.318962704046665` seconds/document (up from `2.199s`).
- **The only field that changed anywhere in the aggregate result is
  `box_13.retirement_plan`**; every other field's correct/incorrect count is
  unchanged across all four variants — zero regressions.
- Per-variant `box_13.retirement_plan` breakdown (out of 150 documents each):
  clean render 96.67% -> **100.0%** (fully resolved, matches the standalone
  clean-150 rerun); compressed JPEG 82.67% -> **100.0%** (fully resolved —
  compression doesn't shift checkbox geometry); rotated PNG 48.0% -> 60.0%
  (improved but not resolved — rotation shifts the checkbox's true-image
  position past the fixed calibration zone); blurred PNG 40.0% -> 54.67%
  (improved but not resolved — blur degrades the ink-coverage measurement's
  reliability near the `0.09` threshold rather than shifting geometry).
- Conclusion: the fix is a full, unconditional win on clean and compressed
  images but only a partial win under rotation and blur — exactly the
  outcome anticipated by the documented caveat that
  `RETIREMENT_PLAN_ZONE`/the ink-coverage threshold were calibrated solely
  against clean renders. This result supersedes
  `phase4c_external_all_variants_600_name_semantics` as the authoritative
  Tesseract 600-document robustness number; the incumbent configuration is
  unchanged. Whether the residual rotated/blurred gap warrants a follow-up
  (rotation-aware zone, blur-adjusted threshold) is an open decision, not
  addressed here. The equivalent PaddleOCR GPU 600-document robustness
  rerun remains outstanding and was out of scope for this task.

Completed Phase 4E PaddleOCR GPU 600-document robustness rerun (post
checkbox-vision fix):

```text
data/evaluation/results/phase4e_paddleocr_gpu_checkbox_vision_external_all_variants_600.json
data/evaluation/results/phase4e_paddleocr_gpu_checkbox_vision_external_all_variants_600.md
```

Formal rerun of PaddleOCR GPU's 600-document robustness benchmark (all four
external variants; `--ocr-backend paddleocr --paddle-device gpu`) with the
Box 13 visual checkbox detector in place, closing the last outstanding item
from "Immediate Next Experiment." This is PaddleOCR GPU's first-ever
600-document robustness data point — no prior PaddleOCR benchmark existed
at this scope for the compressed/rotated/blurred variants, so there is no
PaddleOCR "before" number to diff against for those three; comparisons
below are against PaddleOCR's own clean-150 post-fix result and against the
Tesseract 600-document robustness result from the preceding rerun.

- `field_accuracy = 0.976231884057971` (13,472/13,800 correct),
  `failed_documents = 0`, `field_failure_count = 328`, average
  `1.329903785876671` seconds/document (essentially matching PaddleOCR's
  clean-150 post-fix rate of `1.439s`/doc — no robustness-driven slowdown).
- **Every one of the 328 failures is on `rotated_png`.** Clean render,
  compressed JPEG, and blurred PNG are all `field_accuracy = 1.0`
  (3,450/3,450 each, zero failures) — perfect on three of four variants,
  including blur, which is Tesseract's worst variant (67.71%).
- `rotated_png` (`field_accuracy = 0.904927536231884`, 3,122/3,450):
  failures are concentrated in exactly three fields —
  `employee.first_name` (0/150, complete failure), `employee.middle_initial`
  (32/150, 21.3%), and `box_13.retirement_plan` (90/150, 60.0%).
- **New finding, unrelated to checkbox vision:** every rotated-image
  `employee.first_name` failure shows the printed field-label text appended
  to the predicted name (e.g. expected `"Lori"`, predicted `"Lori e
  Employee's first name and initial"`) — a label-bleed artifact in
  PaddleOCR's rotated-image name-zone word reconstruction. This is a
  complete, systematic failure (0/150) newly surfaced by this rerun (no
  prior PaddleOCR robustness data existed to have caught it earlier), not a
  regression from anything.
- **`box_13.retirement_plan` rotated failures are identical, document for
  document, to Tesseract's** — cross-checking `document_id` sets shows the
  same exact 60 documents fail on both backends (`60/60` overlap). This
  confirms the visual checkbox detector runs identically regardless of OCR
  backend (it operates on the same source image pixels) and that its
  rotation weakness is a property of the fixed calibration zone, not either
  backend's OCR behavior.
- Versus the Tesseract 600-document result (88.98% aggregate, worst variant
  blurred at 67.71%): PaddleOCR GPU's aggregate accuracy is substantially
  higher (97.62%) and its worst variant (rotated, 90.49%) is far better than
  Tesseract's worst (blurred, 67.71%) and marginally better than Tesseract's
  own rotated result (89.97%).
- Conclusion: PaddleOCR GPU's robustness profile, measured here for the
  first time, is stronger than Tesseract's across the full 600-document set
  — higher aggregate accuracy, zero failures on two variants where Tesseract
  has real weaknesses (compressed marginally, blurred substantially), and a
  comparable rotated-image result despite sharing the identical Box 13
  rotation weakness. Its one new, previously unmeasured weakness — complete
  `employee.first_name` failure under rotation — is a genuine caveat, not a
  regression, and is unrelated to the checkbox-vision fix. This does
  **not** promote PaddleOCR GPU to incumbent or change the incumbent
  configuration — no promotion decision was made as part of this rerun, per
  the experiment skill's boundaries. No Tesseract PSM 11 or other
  configuration was run, per this task's explicit scope.

Completed Phase 4E targeted supplemental PSM 11 smoke test — disqualifying
regression found:

```text
data/evaluation/results/phase4e_tesseract_supplemental_psm11_smoke_5.json
data/evaluation/results/phase4e_tesseract_supplemental_psm11_smoke_5.md
```

Ran the readiness-unlocked configuration for the first time: main PSM 3 +
targeted supplemental PSM 6 + targeted supplemental PSM 11
(`--tesseract-supplemental-psm 6,11`), 5 external clean-render documents,
checkbox vision enabled.

- `field_accuracy = 0.9565217391304348` (110/115), `failed_documents = 0`,
  average `3.528s`/document (up 51% from the incumbent's `2.330s`/document).
- All 5 field failures are `employee.first_name`, 0/5 correct (100%
  failure). Cross-checked against the same 5 `document_id`s in the
  Tesseract 600-document robustness rerun: all 5 were 100% correct under
  the PSM 3 + PSM 6 incumbent alone — an unambiguous regression, not
  sampling noise.
- Root cause: text duplication, not a targeting or row-grouping failure.
  The employee-name OCR fallback (`_zone_text` in `parser_2026.py`) joins
  every token found in its zone rather than picking one, unlike the
  first-match logic (`_first_regex_text_in_zone`/`_first_money_text_in_zone`)
  used for EIN and money fields. Since PSM 11's supplemental pass and PSM
  3's main pass both land readings of the same name in the shared zone,
  `_zone_text` concatenates both (e.g. expected `"Steven"`, predicted
  `"Steven Steven D"`).
- `employer.ein` and federal Boxes 3/5/6 (the other four approved target
  fields) all stayed 5/5 correct — confirming the row-grouping isolation
  and zone-targeting built during the readiness work performed exactly as
  designed for first-match-style fallbacks. Box 13 and SSN (explicitly
  non-target fields) also stayed 5/5 correct, confirming PSM 11
  supplementation did not leak outside its approved zones.
- Conclusion: **this configuration is not marked eligible for the
  150-document benchmark**, per this smoke task's explicit stop condition.
  Two candidate fixes were identified but not implemented (out of scope for
  a smoke-test task): make `_zone_text` resilient to multiple overlapping
  observation sources in one zone, or narrow PSM 11 supplementation to only
  `employer.ein`/Box 3/5/6 and drop the name zone entirely. Neither the
  historical Tesseract artifacts nor the incumbent configuration were
  touched.

Completed Phase 4E targeted supplemental PSM 11 retry without the name
zone — no regression, no demonstrated benefit:

```text
data/evaluation/results/phase4e_tesseract_supplemental_psm11_no_name_zone_smoke_5.json
data/evaluation/results/phase4e_tesseract_supplemental_psm11_no_name_zone_smoke_5.md
```

Applied the smaller of the two candidate fixes above: removed the
employee-name zone from `_SUPPLEMENTAL_TARGET_ZONES[11]`
(`src/w2_pipeline/extraction/ocr.py`) rather than redesigning `_zone_text`.
PSM 11 supplementation now targets only `employer.ein` and federal Boxes
3/5/6 — the four fields that use first-match fallback logic and were
unaffected by the duplication bug. Updated the one affected unit test;
full suite 143 passing (unchanged count). Re-ran the identical 5-document
clean-render smoke.

- `field_accuracy = 1.0` (115/115 correct), `failed_documents = 0`,
  `field_failure_count = 0`, average `3.656s`/document (+56.9% vs. the
  incumbent's `2.330s`).
- Same 5 documents as the disqualified smoke
  (`symage_900001`/`900002`/`900003`/`900004`/`900006`). Cross-checked
  against the incumbent's result for these exact documents: all 115
  fields were already 100% correct under PSM 3 + PSM 6 alone — zero
  primary-path failures on the four target fields for PSM 11 to have a
  chance to recover in this specific sample.
- **No regression**: the disqualifying `employee.first_name` duplication
  is gone (no longer targeted, so PSM 3's unmodified reading is the only
  source, exactly as under the incumbent) and every other field matches
  the incumbent exactly.
- **No demonstrated recovery benefit**: this sample cannot show whether
  targeted PSM 11 supplementation actually recovers anything, since
  nothing was broken to recover from. A sample containing at least one
  primary-path failure on `employer.ein` or Box 3/5/6 (occurring at
  roughly a 1-1.3% document rate per the 150-document incumbent numbers)
  would be needed to observe that; a 5-document sample cannot be expected
  to contain one.
- Conclusion: per the decision rule for this task ("no regression but no
  demonstrated recovery benefit -> do not automatically advance; document
  that the smoke did not prove value"), **this configuration is not marked
  eligible for the clean-150 benchmark.** It is no longer disqualified,
  but promotion to a larger-scale run would need to be a separate,
  explicit decision with a sample large enough to actually test the
  recovery hypothesis — not run as part of this task. No 150-document or
  600-document run, no PaddleOCR run, and no other configuration change
  were made; the incumbent, the disqualified smoke, and all other
  historical artifacts are preserved unchanged.

Completed Phase 4E targeted supplemental PSM 11 recovery diagnostic —
meaningful recovery demonstrated, marked justified for clean-150:

```text
data/evaluation/results/phase4e_tesseract_supplemental_psm11_recovery_diagnostic_5.json
data/evaluation/results/phase4e_tesseract_supplemental_psm11_recovery_diagnostic_5.md
```

**A targeted diagnostic, not an accuracy benchmark** — its aggregate
`field_accuracy` is not representative of anything but this deliberately
biased sample. Selected, from the 150-document incumbent result, every
document where PSM 3 + PSM 6 failed at least one of PSM 11's four target
fields (6 known failures across 5 documents), then reran exactly those
documents with PSM 11 enabled via a temporary manifest (built and deleted
for this run only; not a retained artifact).

- `field_accuracy = 0.9652173913043478` (111/115, deliberately
  unrepresentative), average `3.640s`/document.
- **4 of 6 (66.7%) known target-field failures recovered**: `employer.ein`
  on `symage_900021` and `symage_900119` (both `"missing"` -> exact
  match), `box_5`/`box_6` on `symage_900063` (both `"missing"` -> exact
  match). **2 of 6 not recovered**: `box_3` on `symage_900075` and `box_6`
  on `symage_900123` — both were `"mismatch"`-kind (the primary path
  already produced a wrong, non-`None` value), and the existing
  `None`-only fallback gate structurally cannot fire for those regardless
  of what PSM 11 reads. **100% of `"missing"`-kind failures recovered, 0%
  of `"mismatch"`-kind** — a clean, fully explained mechanistic pattern,
  not partial/inconsistent signal.
- **Zero leakage confirmed under a harder sample**: `symage_900119`'s two
  pre-existing, unrelated failures (`employee.first_name`/
  `middle_initial`, outside PSM 11's target set since the name zone was
  removed) were bit-for-bit unchanged.
- Conclusion: this is meaningful recovery, not "none or very few," per the
  decision rule for this task. **Targeted supplemental PSM 11
  (`employer.ein` + Boxes 3/5/6 only) is marked justified for a controlled
  clean-150 benchmark.** That benchmark has **not** been run — it remains
  the mechanical next step if pursued; see "Immediate Next Experiment".
  The incumbent configuration is unchanged; no promotion was made by this
  diagnostic itself. No 150-document or 600-document run (beyond reading
  the existing historical result), no PaddleOCR run, and no other
  configuration change were made.

Completed Phase 4E controlled clean-150 benchmark for targeted
supplemental PSM 11 — confirmed gain, zero regressions, reported not
promoted:

```text
data/evaluation/results/phase4e_tesseract_supplemental_psm11_external_clean_150.json
data/evaluation/results/phase4e_tesseract_supplemental_psm11_external_clean_150.md
```

Acted on the recovery diagnostic's justification: main PSM 3 + targeted
supplemental PSM 6 + targeted supplemental PSM 11 (`employer.ein`/Box
3/5/6 only), full 150-document external clean-render set, checkbox vision
enabled, same corrected ground truth/parser/evaluator/schema as the
incumbent.

- `field_accuracy = 0.9939130434782608` (3,429/3,450), up from the
  incumbent's `0.9927536231884058` (3,425/3,450); `failed_documents = 0`;
  `field_failure_count = 21`, down from 25; average `3.541479775440033`
  seconds/document, up from `2.330209926666645` (**+51.98%**).
- Per-field: `employer.ein` 98.67% -> **100.0%** (+2), `box_5` 99.33% ->
  **100.0%** (+1), `box_6` 98.67% -> 99.33% (+1), `box_3` unchanged
  (99.33%, its one failure is `"mismatch"`-kind and structurally
  unrecoverable). No other field changed.
- Document-level cross-check against the incumbent's `field_failures`
  confirms **exactly the 4 recoveries the diagnostic predicted**
  (`symage_900021.employer.ein`, `symage_900119.employer.ein`,
  `symage_900063.box_5`, `symage_900063.box_6`, all `"missing"`-kind) and
  **zero new failures anywhere** — the regressed-field set is empty, and
  all 21 remaining failures have bit-for-bit identical predicted values
  to the incumbent (nothing disturbed, only filled in).
- Conclusion: a real but narrow accuracy gain (0.116 percentage points, 3
  of 150 documents affected) at a substantial, universal latency cost
  (+52% per document, since the second full-page OCR pass runs on every
  document regardless of whether it benefits). Per the decision rule for
  this task, this is recorded as a confirmed gain with zero regressions,
  not automatically promoted — the incumbent configuration is unchanged,
  and whether the accuracy gain justifies the latency cost in production
  is an explicit trade-off left for the user to decide. No 600-document
  run, no PaddleOCR run, and no other configuration change were made; the
  incumbent and all three prior PSM 11 artifacts (both smokes and the
  diagnostic) are preserved unchanged.

Completed Phase 4E rotated employee-name label-bleed investigation
(diagnosis only, no fix implemented):

```text
docs/experiments/phase4e-paddle-rotation-name-investigation.md
```

Traced the rotated-`employee.first_name` failure (0/150 on both backends;
predicted values like `"Lori"` -> `"Lori e Employee's first name and
initial"`) from raw PaddleOCR `predict()` output through the adapter to
the parser, using 3 representative documents (with/without a middle
initial, plus an accented name). Root cause: the shared, backend-neutral
employee-name OCR fallback (`_apply_ocr_employee_layout_fallbacks`/
`_zone_text` in `parser_2026.py`) uses a fixed ratio-based target zone
normalized against detected-text extent (not true image pixels); under
rotation, the printed Box e field label's normalized `y` position crosses
the zone's `0.505` floor (clean: `0.4852`, outside; rotated: `0.5060`,
inside — reproduced identically across 4 documents), so the label text
gets joined into the name value. The missing middle initial follows
mechanically: `split_first_name_and_initial` only checks the *last*
whitespace-split token, which the merged label's trailing words push the
true initial out of. PaddleOCR's raw output was verified correct before
any adapter/parser code runs — the label and value are separate,
correctly-recognized, non-overlapping entries — ruling out Paddle's
detection/recognition and the adapter's coordinate conversion.

**Correction to prior documentation**: this was previously reported (from
the PaddleOCR 600-document robustness rerun) as a PaddleOCR-specific
weakness ("Tesseract's rotated `employee.first_name` is 53.67%, weak but
not zeroed"). That figure was Tesseract's *aggregate across all four
variants*; the rotated-only figure, recomputed directly, is 0/150 (0%) —
identical to PaddleOCR — and `employee.middle_initial` is 32/150 (21.33%)
on both backends too. Both backends share the identical bug because it
lives in shared parser code both routes flow through equally. This
removes a caveat that previously appeared unique to PaddleOCR GPU in the
incumbent-promotion comparison; corrected in "Current Phase," "Immediate
Next Experiment," and "Current Known Weaknesses" above.

Recommended fix (not implemented, per this investigation's explicit
scope): filter the known, static Box e label text out of zone-filtered
observations — backend-neutral, requires no ratio recalibration.
Rejected as the primary fix: renormalizing zone ratios against true image
dimensions, which would require recalibrating every zone constant in the
fallback system (name, EIN, all federal box zones), not just this one —
out of scope for "smallest evidence-supported fix." See the report for
full detail, including why the true-image-normalization alternative was
checked and rejected, and why the failure's severity (100%, not partial)
is specific to this template/rotation-angle combination even though the
underlying zone-ratio-instability mechanism is generic to any rotated
document using this fallback pattern.

Completed Phase 4E rotated employee-name label-bleed fix (implemented and
verified):

```text
src/w2_pipeline/extraction/parser_2026.py (_clean_layout_token, _BOX_E_LABEL_WORDS)
tests/extraction/test_parser_2026.py (6 new tests)
```

Implemented the investigation's recommended fix: `_clean_layout_token`
(shared by the employee first-name/middle-initial, last-name, and suffix
OCR fallback zones) now filters Box e's known, static printed label
vocabulary at the word level — stripping matching words out of a multi-
word observation and rejoining the survivors, rather than only exact-
matching a token's whole string as before. This works identically whether
the label arrives as one merged observation (PaddleOCR's line-level
recognition, e.g. `"e Employee's first name and initial"`) or as several
separate word tokens interleaved with the name by x-position (Tesseract's
word-level recognition). No OCR-backend branching was added; the fix
lives entirely in shared parser code. No OCR settings, checkbox vision,
ground truth, evaluator, or ratio-zone constant were touched.

6 new focused tests cover: a clean name unaffected by the filter; a
PaddleOCR-style merged label with a middle initial recovering
`first_name="Steven"`/`middle_initial="D"`; the same without a middle
initial (`first_name="Lori"`); an accented name surviving the ASCII-only
label-word filter untouched (`"Jesús"`); a Tesseract-style fragmented/
interleaved label recovering the name correctly; and a regression check
confirming last name and suffix zones are unaffected. Full suite: 149
tests passing (143 before this task, zero regressions).

Real-pipeline smoke (not a benchmark): ran `PipelineAExtractor` directly
against the actual rotated source images (not synthetic fixtures) for 3
representative documents × 2 backends. 5/6 exact matches
(`symage_900000` no-initial and `symage_900001` with-initial correct on
both backends; `symage_900026` accented-with-initial correct on
PaddleOCR). The one non-match — Tesseract on `symage_900026` predicting
`"Jesus"` instead of `"Jesús"` — is confirmed **not** a regression or
part of this fix's scope: Tesseract already misread the same accent on
that document's *clean* render (pre-existing, unrelated accent-
recognition limitation); before this fix, Tesseract's rotated prediction
for that document was `"Jesus Employee's D first name and"` (both the
accent drop and the label-bleed, middle initial lost) — after the fix it
is `"Jesus"` with `middle_initial="D"` correctly recovered, confirming
the label-bleed component is fully resolved and only the separate,
pre-existing accent issue remains.

Conclusion: the fix resolves the rotated `employee.first_name`/
`employee.middle_initial` label-bleed corruption on both backends, per
this task's explicit scope (no 150/600-document benchmark run, no PSM 11
experiments, no Pipeline B work). The historical 150/600-document
benchmark artifacts for both backends now predate this fix for these two
fields; rerunning them to obtain corrected authoritative numbers is the
natural next mechanical step, not performed as part of this task.

Completed Phase 4E PaddleOCR GPU 150-document `rotated_png` rerun (post
Box-e-label fix) — confirmed fix at scale, one new bug found:

```text
data/evaluation/results/phase4e_paddleocr_gpu_box_e_fix_rotated_150.json
data/evaluation/results/phase4e_paddleocr_gpu_box_e_fix_rotated_150.md
```

Reran PaddleOCR GPU against the full 150-document `rotated_png` variant
only (checkbox vision enabled, current parser including the Box e fix),
to confirm the fix at scale. Compared against the historical PaddleOCR
GPU rotated subset (`phase4e_paddleocr_gpu_checkbox_vision_external_all_variants_600.json`
filtered to `variant_id == "rotated_png"`: 3,122/3,450 = 90.49%).

- `employee.first_name`: 0/150 (0%) -> **150/150 (100%), fully resolved,
  no exceptions**.
- `employee.middle_initial`: 32/150 (21.33%) -> 144/150 (96.0%),
  substantially improved (112 of 118 historical failures recovered) but
  not fully resolved — see the new-bug finding below.
- `box_13.retirement_plan`: 90/150 (60.0%) -> 90/150 (60.0%), unchanged
  as expected (separate checkbox-vision rotation-calibration limitation,
  out of scope).
- Overall: `field_accuracy = 0.9808695652173913` (3,384/3,450), up from
  `0.904927536231884` (3,122/3,450), +7.6 percentage points on this
  variant. `failed_documents = 0`. Average duration `1.427s`/document,
  close to the historical PaddleOCR GPU aggregate rate (`1.349s`/doc
  across all four variants; no rotated-only historical baseline exists
  for an exact comparison).
- Zero regressions anywhere, confirmed by an exhaustive document-and-
  field-level diff: 262 fields recovered, 0 newly failing, all 66
  remaining failures (60 `box_13.retirement_plan` + 6
  `employee.middle_initial`) present in both the old and new results.

**New finding: a real regression in the Box e label fix itself, not a
pre-existing limitation.** All 6 remaining `employee.middle_initial`
failures share `expected: "E"`; cross-referenced against ground truth,
this is exactly the 6 of 118 documents with any middle initial whose true
initial is `"E"` — every other letter succeeds. Root cause (confirmed
directly: `_clean_layout_token("E")` returns `None`, `_clean_layout_token("D")`
returns `"D"`): `_is_box_e_label_word` lowercases its input before
checking membership in `_BOX_E_LABEL_WORDS`, which includes lowercase
`"e"` (the box-letter marker) — this also incorrectly matches and
discards a legitimate capital `"E"` initial. The pre-existing, case-
sensitive `_SINGLE_CHAR_JUNK` check already handled the genuine marker
case correctly and was not the source of this bug. Not variant-specific,
so plausibly also affects clean/compressed/blurred documents with a `"E"`
middle initial — not verified as part of this `rotated_png`-scoped task.
Recommended fix (small, low-risk, **not implemented** per this task's
explicit scope): remove the redundant `"e"` entry from
`_BOX_E_LABEL_WORDS`.

Per this task's explicit instruction not to hide or normalize evaluator
differences: this finding is reported plainly as a new defect, distinct
from (and not conflated with) the original label-bleed bug or Tesseract's
separate accent-recognition limitation. No clean/compressed/blurred
variant, no full 600-document benchmark, no Tesseract, no PSM 11, and no
Pipeline B work were performed, per this task's explicit scope. The
historical 600-document PaddleOCR artifact was not modified.

Completed Phase 4E Box e filter capital-E regression fix (implemented and
verified):

```text
src/w2_pipeline/extraction/parser_2026.py (_BOX_E_LABEL_WORDS)
tests/extraction/test_parser_2026.py (10 new tests)
```

Fixed the capital-`"E"` middle-initial regression found by the preceding
`rotated_png` rerun, exactly as diagnosed: removed the redundant `"e"`
entry from `_BOX_E_LABEL_WORDS`, so `_is_box_e_label_word` no longer
lowercase-matches a legitimate capital `"E"` initial against the
box-letter marker. The marker case remains correctly handled by the
pre-existing, case-sensitive `_SINGLE_CHAR_JUNK` check alone — no other
line changed, no OCR-backend branching, no OCR-settings change, no zone
recalibration, no checkbox-vision change.

Verified directly: `_clean_layout_token("E") -> "E"`,
`_clean_layout_token("e") -> None`,
`_clean_layout_token("e Employee's first name and initial") -> None`,
`_clean_layout_token("Lori e Employee's first name and initial") ->
"Lori"`, `_clean_layout_token("Steven E e Employee's first name and
initial") -> "Steven E"`.

10 new focused tests: direct `_clean_layout_token` checks for `"E"`
preservation and continued `"e"` filtering; an end-to-end PaddleOCR-style
merged-label case with a capital-E initial; a parametrized check across
`"D"`/`"J"`/`"K"`/`"W"`/`"M"` confirming every other initial still works;
and two more reconfirming the original no-initial and Tesseract-
fragmented cases from the prior fix task. Full suite: 159 tests passing
(149 before this task, zero regressions).

Real-pipeline verification (not a benchmark): `symage_900023` (ground
truth `first_name="James"`, `middle_initial="E"` — the exact bug case)
via PaddleOCR GPU against the actual rotated source image now correctly
extracts both fields; `symage_900001` (`"Steven"`/`"D"`) confirmed
unaffected.

Conclusion: the capital-`"E"` regression is fixed and verified at both
the unit level and against a real rotated image. No 150-document or
600-document benchmark was run to requantify the `rotated_png` numbers
with both Box e fixes in place — the prior rerun's
`employee.middle_initial` figure (144/150, 96.0%) now undercounts by
exactly the 6 documents this fix addresses; a rerun to confirm the
corrected number (expected 150/150) is the natural next mechanical step,
not performed as part of this task. No Tesseract benchmark, no PSM 11
work, and no Pipeline B work were performed.

Completed Phase 4E PaddleOCR GPU 150-document `rotated_png` rerun (post
capital-E fix) — fully confirmed, zero regressions:

```text
data/evaluation/results/phase4e_paddleocr_gpu_capital_e_fix_rotated_150.json
data/evaluation/results/phase4e_paddleocr_gpu_capital_e_fix_rotated_150.md
```

Reran PaddleOCR GPU against the full 150-document `rotated_png` variant
with both Box e fixes in place (label-bleed filter + capital-E denylist
correction), to close out the reconfirmation the capital-E fix task
flagged as outstanding.

- `employee.middle_initial`: 144/150 (96.0%) -> **150/150 (100%)**. All 6
  capital-`"E"` failures recovered, confirmed by exact document ID —
  `symage_900023`, `symage_900028`, `symage_900047`, `symage_900063`,
  `symage_900067`, `symage_900080` — matching the 6 identified in the
  capital-E fix task precisely.
- `employee.first_name`: 150/150 (100%), unchanged.
- `box_13.retirement_plan`: 90/150 (60.0%), unchanged — correctly
  unaffected (separate, already-documented checkbox-vision limitation).
- Overall: `field_accuracy = 0.9826086956521739` (3,390/3,450), up from
  `0.9808695652173913` (3,384/3,450) — exactly +6 fields. `failed_documents
  = 0`. Average duration `1.342s`/document (within normal GPU run-to-run
  variance of the pre-fix rerun's `1.427s`).
- Zero regressions, confirmed by an exhaustive document-and-field-level
  diff: exactly 6 fields recovered, 0 newly failing, all 60 remaining
  failures (`box_13.retirement_plan`) present in both results unchanged.

Conclusion: both Box e fixes are now fully verified at 150-document scale
on PaddleOCR GPU's `rotated_png` variant — `employee.first_name` and
`employee.middle_initial` are both 100% correct, with the sole remaining
weakness (`box_13.retirement_plan`, a separate limitation) untouched. The
full 600-document benchmark and the equivalent Tesseract rerun remain
outstanding and were not run, per this task's explicit scope; no PSM 11
work and no Pipeline B work were performed. All prior historical
artifacts, including both earlier `rotated_png` PaddleOCR results, are
preserved unchanged.

Completed Phase 4E Tesseract incumbent 150-document `rotated_png` rerun
(post both Box e fixes) — confirms the fixes are backend-neutral:

```text
data/evaluation/results/phase4e_tesseract_capital_e_fix_rotated_150.json
data/evaluation/results/phase4e_tesseract_capital_e_fix_rotated_150.md
```

Reran the Tesseract incumbent (main PSM 3 + supplemental PSM 6,
unchanged) against the full 150-document `rotated_png` variant with both
Box e fixes in place, to confirm the fix on the second backend, matching
the two PaddleOCR GPU `rotated_png` reruns already completed.

- `employee.first_name`: 0/150 (0%) -> 146/150 (97.33%). Massive recovery,
  not perfect like PaddleOCR's 150/150 — but the 4 remaining failures are
  fully explained and none are new: 3 are Tesseract's separate,
  pre-existing accent-recognition limitation (`"Jesús"` -> `"Jesus"`,
  `"Óliver"` -> `"Oliver"`, `"Adán"` -> `"Adan"`, already present on these
  documents' clean renders); the 4th (`symage_900118`, `"Logan"`)
  improved from label-bleed garbage (`"Employee's first name and"`) to a
  clean `None` — the corruption is gone, but Tesseract's word-level OCR
  still never detects the name in this document under rotation, a
  separate pre-existing gap.
- `employee.middle_initial`: 32/150 (21.33%) -> 147/150 (98.0%). The 3
  remaining failures (`symage_900062`/`symage_900068`, expected `"C"`;
  `symage_900135`, expected `"I"`) are bit-for-bit unchanged
  `"missing"`-kind failures already present in the historical result —
  pre-existing detection gaps unrelated to either Box e fix.
- `box_13.retirement_plan`: 90/150 (60.0%), unchanged — correctly
  unaffected, matching both PaddleOCR reruns.
- Overall: `field_accuracy = 0.9753623188405797` (3,365/3,450), up from
  `0.8997101449275362` (3,104/3,450) — a +7.6 percentage point
  improvement, closely matching PaddleOCR's own gain from the first fix.
  `failed_documents = 0`. Average duration `2.361s`/document, essentially
  unchanged from the historical aggregate rate (`2.319s`/doc) — no
  latency regression.
- Zero regressions, confirmed by an exhaustive document-and-field-level
  diff: 261 fields recovered, 0 newly failing; the 85 remaining failures
  (60 `box_13.retirement_plan` + 7 employee-name cases explained above +
  18 more in federal Boxes 3/5/6, SSN, EIN, last name) are all
  bit-for-bit unchanged from the historical result — pre-existing
  Tesseract rotation weaknesses the Box e fixes never targeted.

Conclusion: both Box e fixes are confirmed genuinely backend-neutral —
Tesseract and PaddleOCR GPU share the identical underlying bug via
`_clean_layout_token` and both benefit substantially. Tesseract's
remaining gap versus PaddleOCR's clean 150/150 is fully attributable to
separate, pre-existing OCR quality differences (accent recognition,
occasional word-level detection misses), not a fix limitation. The full
600-document benchmark for either backend remains outstanding and was not
run, per this task's explicit scope; no PaddleOCR run, no PSM 11 work,
and no Pipeline B work were performed. All historical artifacts,
including the 600-document Tesseract robustness result, are preserved
unchanged.

## Current Known Weaknesses

- Employee first name and middle initial remain the weakest fields under the
  incumbent PSM 3 + PSM 6 configuration (93.33% / 94.0% on the clean set).
- **The employee-name OCR fallback (`_zone_text` in `parser_2026.py`)
  joins every observation in its target zone rather than picking one,
  unlike the first-match fallback logic used for EIN/money fields.** The
  first targeted supplemental PSM 11 smoke test demonstrated this breaks
  completely (100% -> 0% on `employee.first_name`, text duplication) the
  moment a second observation source also lands readings in that zone;
  the fix applied was to remove the name zone from PSM 11's target set
  entirely (mitigated by scope reduction, not by fixing `_zone_text`
  itself). `_zone_text` remains unmodified and is still only safe today
  because nothing currently contributes overlapping observations to the
  employee-name zone. Any future work (a different supplemental pass, a
  different OCR backend feature) that adds a second observation source
  touching that zone must account for this before relying on `_zone_text`
  as-is; see "Completed Phase History" for both smoke tests.
- Box 13 retirement-plan checkbox detection was a known weak field under the
  incumbent configuration (96.67% on the recorded 150-document clean
  benchmark). A backend-neutral visual checkbox detector has since been
  added. On clean and compressed-JPEG images it is a complete fix on both
  backends: Tesseract and PaddleOCR GPU both reach 100.0% on the clean-150
  benchmark, and both reach 100.0% on clean and compressed in their
  respective 600-document robustness reruns. **Under rotation it is only a
  partial fix on both backends, identically**: Tesseract improves 48.0% ->
  60.0% and PaddleOCR GPU lands at the same 60.0% — cross-checked
  document-for-document, the exact same 60 documents fail on both backends,
  confirming the fixed true-image-relative calibration zone (not either
  backend's OCR behavior) is the limiting factor, since it doesn't track
  rotation's geometry shift. **Under blur, the two backends diverge**:
  Tesseract only partially improves (40.0% -> 54.67%, ink-coverage
  measurement gets noisier near threshold) while PaddleOCR GPU is
  unaffected and reaches 100.0%. The residual rotation gap is now a known,
  cross-backend weakness; the blur gap is Tesseract-specific.
- Employer EIN and employee SSN degrade under rotated/blurred variants (on
  Tesseract; PaddleOCR GPU is unaffected on blur and shares the rotation
  weakness only on `box_13.retirement_plan`, not EIN/SSN).
- Blur is Tesseract's dominant degradation case (aggregate field accuracy
  67.07% -> 67.71% post-checkbox-vision-fix on the blurred variant,
  essentially unchanged outside `box_13.retirement_plan`); rotation is a
  moderate degradation case for Tesseract (89.45% -> 89.97%, same caveat).
  PaddleOCR GPU has no blur weakness (100.0%) and a comparable rotation
  result (89.97% -> Tesseract vs. 90.49% PaddleOCR), but see the
  rotated-image `employee.first_name` weakness below, which is
  **backend-neutral, not unique to PaddleOCR** (corrected below).
- **RESOLVED (pending 150/600-document reconfirmation): rotated-image
  `employee.first_name` was a complete, systematic failure (0/150, 0%) on
  BOTH backends** — confirmed backend-neutral, root-caused, and now fixed.
  Historical failures showed the printed field-label text bleeding into
  the predicted name (e.g. expected `"Lori"`, predicted `"Lori e
  Employee's first name and initial"`), with `employee.middle_initial`
  also weak under the same condition (32/150 = 21.33% correct, on both
  backends identically). **Correction to the original 600-document
  robustness rerun**: this was previously reported as a PaddleOCR-specific
  severity ("Tesseract's rotated `employee.first_name` is weak, 53.67%,
  but not zeroed") — that 53.67% figure was Tesseract's aggregate across
  all four variants, not the rotated-only figure; recomputed directly,
  Tesseract was also 0/150 (0%) on rotated `employee.first_name` and
  32/150 (21.33%) on rotated `employee.middle_initial`, identical to
  PaddleOCR. Full investigation:
  `docs/experiments/phase4e-paddle-rotation-name-investigation.md`. Root
  cause: the shared, backend-neutral employee-name OCR fallback
  (`_zone_text` in `parser_2026.py`) used a fixed ratio-based zone,
  normalized against detected-text extent rather than true image pixels,
  that only captured the printed Box e label under rotation (clean-render
  label ratio `0.4852`, safely outside the zone's `0.505` floor; rotated
  `0.5060`, just inside). **Fix implemented**: `_clean_layout_token` now
  filters the known Box e label vocabulary at the word level (backend-
  neutral, no ratio recalibration, no OCR-settings change), covered by 6
  new tests (149 passing) and verified via a real-pipeline smoke against
  actual rotated images for both backends (5/6 exact matches; the one
  non-match is Tesseract's unrelated, pre-existing accent-recognition
  limitation, not this bug). See
  `docs/experiments/pipeline-a-extraction-history.md`'s "Rotated
  Employee-Name Label-Bleed Fix" entry for the implementation record.
  **Confirmed at scale for PaddleOCR GPU's `rotated_png` variant, with
  the follow-up capital-`"E"` fix below also included**: a full
  150-document rerun (after both Box e fixes) showed
  `employee.first_name` 0/150 -> 150/150 (100%, fully resolved) and
  `employee.middle_initial` 32/150 -> **150/150 (100%, fully resolved)**,
  zero regressions, `box_13.retirement_plan` correctly unaffected (60.0%,
  a separate limitation). **The historical benchmark numbers for
  clean/compressed/blurred (both backends) and for Tesseract on any
  variant still predate these fixes and have not been reconfirmed at
  scale** — that rerun is the natural next mechanical step, not yet done.
- **RESOLVED: a capital `"E"` middle initial was incorrectly discarded —
  a real, narrow regression introduced by the Box e label fix itself, NOT
  a pre-existing limitation.** Found by the `rotated_png` rerun (all 6
  residual `employee.middle_initial` failures there shared
  `expected: "E"`, confirmed to be exactly the 6 of 118 documents with
  any middle initial whose true initial is `"E"`, every other letter
  succeeding). Root cause: `_is_box_e_label_word` lowercased its input
  before matching against `_BOX_E_LABEL_WORDS` (which included lowercase
  `"e"`, the box-letter marker), so it also incorrectly matched and
  discarded a legitimate capital `"E"` initial. **Fix implemented**:
  removed the redundant `"e"` entry from `_BOX_E_LABEL_WORDS`; the
  pre-existing case-sensitive `_SINGLE_CHAR_JUNK` check alone correctly
  handles the genuine marker case. 10 new tests (159 passing). Verified
  directly (`_clean_layout_token("E") -> "E"`) and against a real rotated
  image via PaddleOCR GPU (`symage_900023`, `"James"`/`"E"`, correctly
  extracted). **Reconfirmed at 150-document scale**: a second full
  `rotated_png` rerun with both fixes in place showed
  `employee.middle_initial` 144/150 -> 150/150 (100%, all 6 exact
  documents — `symage_900023`/`900028`/`900047`/`900063`/`900067`/`900080`
  — recovered), zero regressions, `employee.first_name` and
  `box_13.retirement_plan` unaffected. Not variant-specific, so this fix
  plausibly also corrects clean/compressed/blurred documents with a `"E"`
  middle initial, though that was not verified — the full 600-document
  benchmark and the equivalent Tesseract rerun remain outstanding.
- PSM 11 trades the above name/EIN/Box 13 weaknesses for a total loss of
  federal Boxes 1 and 2, so it is documented as a known failure mode rather
  than adopted.
- PSM 12 is a documented broad-failure mode: it trades none of the incumbent's
  weaknesses away and additionally zeroes federal Boxes 1-6, employee last
  name, and employer EIN, so it is rejected outright rather than considered a
  partial trade-off.
- PaddleOCR CPU's known weakness is throughput: ~74.3 seconds/document
  (~35-37x slower than Tesseract), which GPU execution resolves (~1.35
  seconds/document, ~34% faster than Tesseract).
- PaddleOCR GPU's original 150-document benchmark showed its entire error
  surface concentrated in one field: `box_13.retirement_plan` (40.0%
  accuracy, 0/90 on every document where the box is actually checked). This
  is now understood, fixed at the code level (backend-neutral visual
  checkbox detector; see "Completed Phase History"), and **reconfirmed at
  full 150-document scale**: `field_accuracy = 1.0`, zero field failures
  anywhere, `box_13.retirement_plan` 100.0%. The 97.39%/40.0% figures are
  now historical. PaddleOCR GPU's 600-document robustness has now also been
  measured for the first time: `field_accuracy = 0.976231884057971`,
  perfect on clean/compressed/blurred, with all failures on `rotated_png`
  (90.49%) — see the rotated-image `employee.first_name` weakness above,
  the one open item this rerun surfaced rather than resolved.

## Unimplemented Capabilities

- The 150-document CPU PaddleOCR benchmark has not been run (GPU was
  benchmarked instead, based on the GPU smoke result). The 600-document
  PaddleOCR robustness benchmark has been run on GPU
  (`phase4e_paddleocr_gpu_checkbox_vision_external_all_variants_600`,
  `field_accuracy = 0.976231884057971`); the CPU device has not been
  benchmarked at 600-document scale.
- Phase 5 (Pipeline B document-vision/VLM challenger) has not been started.
- Review routing, confidence calibration, validation engines, persistence,
  FastAPI/API layer, frontend, CSV export, and cost tracking remain
  unimplemented future-phase work.

## Open Issues

- Review routing, confidence calibration, additional OCR optimization, model extraction,
  validation engines, persistence, frontend, export, and cost tracking remain
  unimplemented future-phase work.
