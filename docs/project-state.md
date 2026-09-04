# Project State

Last updated: 2026-09-04

## Current Phase

Phase 4E's PaddleOCR GPU evaluation is complete through the 150-document
benchmark stage. PaddleOCR GPU does **not** exceed the Tesseract incumbent's
overall field accuracy (97.39% vs. 99.13% on the identical 150-document clean
set) and has therefore **not** been promoted to incumbent. The result is more
nuanced than a simple loss, though: PaddleOCR GPU is ~34% faster than
Tesseract (`1.35s` vs. `2.05s`/document) with zero document failures, and its
entire 90-field error surface is one single systematic field
(`box_13.retirement_plan`, 40.0% accuracy) rather than Tesseract's more
diffuse spread across seven fields (including employee name fields where
PaddleOCR is 100% correct). See "Immediate Next Experiment" for what remains
open. Phase 4D (Tesseract main-PSM experiments) is complete.

Most recently completed:

- Phase 4E PaddleOCR GPU **150-document** benchmark: `field_accuracy =
  0.9739130434782609` (3,360/3,450 correct), `failed_documents = 0`,
  `field_failure_count = 90`, average `1.349492507300068`
  seconds/document. Every failure is `box_13.retirement_plan` (60/150
  correct); every other field, including employee first/last/middle name,
  SSN, employer EIN, and all of federal Boxes 1-11, is 100% correct across
  all 150 documents. Not promoted to incumbent from this result — see
  "Immediate Next Experiment."
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
SSN-recovery pass, running on CPU. The Phase 4E PaddleOCR GPU 150-document
benchmark is now complete and was evaluated against it on equal footing (same
150 documents, same variant), but PaddleOCR GPU's lower overall field
accuracy (97.39% vs. 99.13%) means it was not promoted to incumbent. Whether
PaddleOCR GPU's speed advantage and narrower failure profile make it worth
adopting despite the lower headline accuracy is an open product/architecture
decision, not one this experiment made; see "Immediate Next Experiment."

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

Experiment narrative (what was tested and learned, as opposed to current
state):

```text
docs/experiments/pipeline-a-extraction-history.md
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
- Both Phase 4D main-PSM experiments are complete; no further PSM values are
  currently planned for evaluation.
- PaddleOCR is available as an alternate OCR backend via `--ocr-backend
  paddleocr` (`src/w2_pipeline/extraction/ocr_paddle.py`), selectable behind
  the same `OcrAdapter` contract Tesseract implements. It is **not** the
  incumbent. Evaluated at full 150-document scale on GPU: `field_accuracy =
  0.9739130434782609` vs. Tesseract's `0.991304347826087` on the identical
  set, so it was not promoted. It is ~34% faster than Tesseract
  (`1.35s` vs. `2.05s`/document) and its entire error surface is one field
  (`box_13.retirement_plan`, 40.0% accuracy) rather than Tesseract's spread
  across seven fields.
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
- Confidence scores remain exploratory.
- Real taxpayer data must not be committed.

## Immediate Next Experiment

The Phase 4E PaddleOCR GPU evaluation sequence (unit tests -> 5-doc CPU smoke
-> GPU enablement -> 5-doc GPU smoke -> 150-doc GPU benchmark) is complete.
PaddleOCR GPU was not promoted to incumbent: `field_accuracy = 0.9739130434782609`
vs. Tesseract's `0.991304347826087` on the identical 150-document clean set.

What is genuinely open, and requires a decision rather than another
mechanical rerun, is what to do with the finding that PaddleOCR GPU's entire
90-field error surface is one systematic field (`box_13.retirement_plan`,
40.0% accuracy) while it is 100% correct everywhere Tesseract is weakest
(employee name fields, EIN, some money boxes) and ~34% faster overall. This
document does not resolve that decision. Plausible next steps, none started:

- Run the 600-document robustness set (compressed/rotated/blurred variants)
  with PaddleOCR GPU to see whether its narrow clean-render failure mode
  holds up under degradation the way the Tesseract incumbent's does, before
  any incumbent conversation happens on more than the clean variant alone.
  Given the now-understood root cause (below), PaddleOCR's
  `box_13.retirement_plan` recall is likely to remain near zero regardless of
  variant, since the checkbox mark is never detected as text at all; the
  open question for a 600-document run is how the other fields degrade, not
  this one.
- **Done, diagnostic only** (see `docs/experiments/pipeline-a-extraction-history.md`,
  "Phase 4E PaddleOCR `box_13.retirement_plan` Failure Investigation"):
  PaddleOCR's PP-OCRv6 text detector never emits any observation for the
  rendered checkbox glyph — 0% recall across every one of the 90
  `true`-labeled documents, confirmed via raw-observation inspection, not
  merely inferred from the aggregate. Tesseract only "detects" it because its
  classical segmentation garbles the same glyph into stray text (`"[V"`,
  `"4"`) that happens to land in the parser's `mark_tokens` allow-list — a
  fallback that is implicitly Tesseract-shaped, not backend-neutral. No
  parser or Paddle configuration change was made; this is a finding, not a
  fix.
- Given that finding, a possible future hybrid strategy is more concrete now
  than a generic idea: PaddleOCR is 100% correct on every field besides
  `box_13.retirement_plan` (including the fields Tesseract itself struggles
  with), so a hybrid could in principle use Paddle for identity/money fields
  and a different, detection-agnostic signal (e.g. pixel-density analysis of
  the checkbox zone, not dependent on any backend's text detection) for that
  one field — analogous to Tesseract's own supplemental PSM 6 pass. Not
  implemented or decided here.
- Decide PaddleOCR GPU is not worth further investment given the lower
  headline accuracy, and proceed to Phase 5 without further Paddle work.

## Future Phases (after Phase 4E)

```text
Phase 5 - Pipeline B: Document Vision / Schema-Constrained Extraction
```

Phase 5 is a genuinely different document-vision/VLM architecture and should
implement a model-based challenger that produces the same canonical
`W2Document` and runs against the existing evaluator without changing ground
truth or exposing annotations. Phase 5 is compared against whichever Pipeline
A configuration performs best across Phase 4D/4E, not automatically against
the Phase 4B/4C PSM 3 baseline.

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

These are the current authoritative external Pipeline A benchmark results
(main PSM 3 + supplemental PSM 6 incumbent, corrected Box e semantics):

- external Symage clean renders, 150 documents: `field_accuracy =
  0.991304347826087` (3,420 / 3,450 correct), `failed_documents = 0`, average
  2.0517181199200363 seconds/document. Employee Box e breakdown:
  `employee.first_name` 93.33%, `employee.middle_initial` 94.0%,
  `employee.last_name` 100%, `employee.suffix` 100%.
- all prepared external variants, 600 documents: `field_accuracy =
  0.8846376811594203` (12,208 / 13,800 correct), `failed_documents = 0`,
  average 2.1994630620232782 seconds/document.
- variant accuracy: clean render 99.13%, compressed JPEG 98.20%, rotated PNG
  89.45%, blurred PNG 67.07%.

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

## Current Known Weaknesses

- Employee first name and middle initial remain the weakest fields under the
  incumbent PSM 3 + PSM 6 configuration (93.33% / 94.0% on the clean set).
- Box 13 retirement-plan checkbox detection remains a known weak field under
  the incumbent configuration.
- Employer EIN and employee SSN degrade under rotated/blurred variants.
- Blur is the dominant degradation case (67.07% aggregate field accuracy on
  the blurred variant); rotation is a moderate degradation case (89.45%).
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
- PaddleOCR GPU's known weakness, at 150-document clean-render scale, is
  entirely concentrated in one field: `box_13.retirement_plan` (40.0%
  accuracy, vs. Tesseract's 96.67% on the same field; PaddleOCR is 0/90 on
  every document where the box is actually checked). Every other scored
  field is 100% correct across all 150 documents, including the fields
  Tesseract is weakest on (employee first/middle name, employer EIN). Root
  cause is understood (see the experiment history's failure-investigation
  entry): PaddleOCR's text detector never perceives the rendered checkbox
  mark as a text region at all, so it is not a recognition-quality issue and
  not fixable by tuning Paddle's recognition settings; Tesseract only
  "catches" it because its noisier segmentation garbles the same glyph into
  stray text that happens to satisfy the parser's (implicitly
  Tesseract-shaped) mark-token allow-list. PaddleOCR GPU's behavior under
  the 600-document robustness variants (compressed/rotated/blurred) is
  unknown; only the clean-render variant has been benchmarked at scale.

## Unimplemented Capabilities

- The 150-document CPU PaddleOCR benchmark has not been run (GPU was
  benchmarked instead, based on the GPU smoke result). The 600-document
  PaddleOCR robustness benchmark (any device) has not been run.
- Phase 5 (Pipeline B document-vision/VLM challenger) has not been started.
- Review routing, confidence calibration, validation engines, persistence,
  FastAPI/API layer, frontend, CSV export, and cost tracking remain
  unimplemented future-phase work.

## Open Issues

- Review routing, confidence calibration, additional OCR optimization, model extraction,
  validation engines, persistence, frontend, export, and cost tracking remain
  unimplemented future-phase work.
