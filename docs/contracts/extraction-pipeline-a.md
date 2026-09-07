# Pipeline A Extraction Contract

Phase 4 implements Pipeline A, the deterministic native-text/OCR baseline.

**Note (Phase 8D.3)**: this document is preserved as written from Phase
4, when Tesseract PSM 3 was the incumbent OCR configuration and
PaddleOCR was a newly-added, not-yet-selected alternative backend. As
of Phase 8B/8C, **PaddleOCR (GPU) is the selected production OCR
backend**; Tesseract remains a supported, documented CPU-only
cost-optimized alternative. See `docs/final-architecture.md` and
`docs/final-decisions.md` for the current selection and evidence. The
observation model, routing, and parser architecture described below are
unchanged.

## Scope

Pipeline A starts after Phase 2 ingestion:

```text
IngestedDocument / ExtractionInput
-> route document
-> acquire text + layout
-> parse deterministic W-2 fields
-> canonical W2Document
```

It does not implement Pipeline B, model inference, confidence thresholds,
validation, review routing, persistence, export, frontend work, or RAG.

## Observation Model

Native PDF extraction and OCR converge on:

```text
TextObservation
```

Each observation records:

- text
- 1-indexed page number
- top-left-origin bounding box using `x0`, `y0`, `x1`, `y1`
- source: `native_pdf` or `ocr`
- `is_supplemental`: `True` when the observation came from a targeted
  supplemental OCR pass (see "Targeted Supplemental OCR Passes" below)
  rather than the main pass; `False` for every native-PDF and main-pass OCR
  observation.

The deterministic parser consumes this common representation rather than
PyMuPDF or Tesseract-specific objects.

`ObservationSet` also carries `box_13_visual_marks: dict[str, bool]`, a
non-OCR, pixel-derived signal populated independent of `TextObservation`
content; see "Box 13 Visual Checkbox Detection" below.

## Routing

PDFs with usable embedded text use PyMuPDF native line extraction. Image files
and image-only PDFs use OCR. Mixed PDFs are processed page by page, combining
native observations for text pages and OCR observations for image-only pages.

## OCR Engine

Phase 4 selects Tesseract as the initial OCR baseline. The Python package
calls the local `tesseract` system binary and parses TSV output into
observations. Phase 4B sets full-page segmentation mode `--psm 3` as the
default and uses a supplemental `--psm 6` pass only to retain recognized
SSN-like text in the top identifier region. Phase 4D keeps PSM 3 as the
incumbent default while allowing controlled full-page PSM 11 and PSM 12
experiments through configuration.

If Tesseract is unavailable, Pipeline A raises `MissingOcrDependencyError` with
an actionable installation message. Unit tests do not require the system OCR
binary.

### Targeted Supplemental OCR Passes

Beyond the configurable *main* page segmentation mode, `TesseractOcrConfig`
also accepts `supplemental_page_segmentation_modes: tuple[int, ...]`
(default `(6,)`), each run in addition to the main pass and geo-fenced to a
small set of approved target zones defined in
`src/w2_pipeline/extraction/ocr.py`'s `_SUPPLEMENTAL_TARGET_ZONES` table.
Supported supplemental modes:
`SUPPORTED_SUPPLEMENTAL_PAGE_SEGMENTATION_MODES = (6, 11)`.

- **PSM 6** (the original, single-purpose mechanism): the top identifier
  region only, further filtered to text matching an SSN shape. Always on by
  default; the incumbent configuration.
- **PSM 11** (Phase 4E, opt-in): four zones —
  `employer.ein` (filtered to an EIN shape),
  `federal_wages_and_taxes.box_3_social_security_wages`,
  `box_5_medicare_wages_and_tips`, and `box_6_medicare_tax_withheld`. Each
  zone tuple is identical to its corresponding OCR fallback zone in
  `parser_2026.py`, so a recovered observation lands exactly where the
  parser will later look for it. PSM 11 supplementation deliberately
  excludes Box 13 (owned by `checkbox_vision.py`) and SSN (owned by PSM 6).
  It originally also targeted the employee-name zone
  (`employee.first_name`/`employee.middle_initial`, matching the full set
  of fields the Phase 4D.1 PSM 11 experiment showed improve over PSM 3),
  but a 5-document smoke test found this caused a disqualifying regression
  — see the caveat below — so the name zone was removed.

A supplemental pass can never corrupt an already-correct primary-path
*line-based* value: `TextObservation.is_supplemental` observations are
excluded from the parser's primary row/line reconstruction
(`_group_observation_rows`) and from its page-extent computation
(`_layout_extent`), so a supplemental pass can never duplicate or corrupt
a Box 1-11/12/14/state-local line the way an unfiltered second full-page
pass would. **This protection does not extend to every zone-based OCR
fallback, however** — `_apply_ocr_employee_layout_fallbacks`'s
employee-name recovery (`_zone_text`) joins every observation found in its
zone rather than picking the first/best match, unlike the first-match
logic (`_first_regex_text_in_zone`/`_first_money_text_in_zone`) used for
SSN/EIN/money fields. A 5-document smoke test
(`phase4e_tesseract_supplemental_psm11_smoke_5`; see
`docs/experiments/pipeline-a-extraction-history.md`) demonstrated this
concretely: enabling PSM 11 with the name zone still targeted regressed
`employee.first_name` from 100% to 0% via text duplication (e.g.
`"Steven"` -> `"Steven Steven D"`), because both PSM 3's main pass and PSM
11's supplemental pass land readings of the same name in that zone and
`_zone_text` concatenates both. This is why the name zone is no longer in
PSM 11's target set — any future supplemental pass (or other new
observation source) that would touch the employee-name zone must account
for `_zone_text`'s join-all behavior first. `employer.ein` and Box 3/5/6
are unaffected by this failure mode since their fallbacks are first-match.

Enable it via the CLI:

```bash
--tesseract-supplemental-psm 6,11
```

(default `"6"`, matching the incumbent unchanged; comma-separated, parsed
and validated by `TesseractOcrConfig`). A random 5-document smoke with
this narrowed target set showed zero regressions but no demonstrated
recovery benefit (the sample had no primary-path failures on `employer.ein`
or Box 3/5/6 to recover from). A follow-up diagnostic that deliberately
sampled documents where the incumbent *does* fail one of these fields
found 4/6 (66.7%) of those known failures recovered, with zero leakage
outside scope — a targeted diagnostic, not a representative benchmark, but
meaningful recovery, so this configuration was marked justified for a
controlled clean-150 benchmark, which has since confirmed the gain at full
scale: `field_accuracy = 0.9939130434782608` (3,429/3,450, up from the
incumbent's 3,425/3,450) with **zero regressions**, at **+51.98%** average
latency (`2.330s` -> `3.541s`/document). This is a real but narrow gain (3
of 150 documents affected) against a substantial universal latency cost —
**not promoted**; the accuracy/latency trade-off is reported for an
explicit user decision, not resolved automatically. See
`docs/project-state.md`'s "Immediate Next Experiment".

### OCR Backend Boundary

Pipeline A's observation acquisition layer (`ObservationAcquirer`) depends on
a structural `OcrAdapter` contract (`src/w2_pipeline/extraction/ocr_backend.py`)
rather than on Tesseract directly:

```python
class OcrAdapter(Protocol):
    def extract_image(self, image_path, *, page_number: int = 1) -> list[TextObservation]: ...
    def extract_pdf_pages(self, pdf_path, *, page_numbers=None) -> list[TextObservation]: ...
```

Any backend implementing this contract is interchangeable behind
`ObservationAcquirer` without the deterministic parser knowing which engine
produced an observation. Both OCR backends share PDF-page-to-image rendering
through `src/w2_pipeline/extraction/pdf_rendering.py` rather than duplicating
PyMuPDF rendering logic.

Phase 4 through Phase 4D used Tesseract exclusively. Phase 4E adds PaddleOCR
as a second backend behind the same contract, selectable with
`--ocr-backend {tesseract, paddleocr}` on the benchmark CLI. Tesseract remains
the default; adding PaddleOCR support does not change the incumbent.

### PaddleOCR Backend (Phase 4E)

`PaddleOcrAdapter` (`src/w2_pipeline/extraction/ocr_paddle.py`) calls the
`paddleocr` Python package's `PaddleOCR(...).predict(image_path)` pipeline and
converts each result's `res.json["res"]` payload into `TextObservation`
values: `rec_texts` becomes observation text, `rec_boxes` (already
`[x_min, y_min, x_max, y_max]` per detection) becomes the bounding box
directly, and `rec_scores` is not currently used for filtering. Unlike
Tesseract's word-level TSV output, PaddleOCR returns already-reconstructed
text lines, so the parser receives line-level observations similar in shape
to native PDF text extraction rather than requiring OCR word-row
reconstruction.

`PaddleOcrConfig` defaults:

```text
lang: "en"
device: "cpu"
use_doc_orientation_classify: False
use_doc_unwarping: False
use_textline_orientation: False
enable_mkldnn: False
```

`enable_mkldnn` defaults to `False` because PaddlePaddle's oneDNN CPU
execution path raised a PIR attribute-conversion error
(`ConvertPirAttribute2RuntimeAttribute not support
[pir::ArrayAttribute<pir::DoubleAttribute>]`) for the default PP-OCRv6 models
on the reference development machine; plain CPU inference without MKL-DNN is
stable. This is an environment-specific correctness fix, not a tuning choice.

If the `paddleocr` package is not installed, Pipeline A raises the same
`MissingOcrDependencyError` used by the Tesseract backend, pointing at the
`paddle` optional dependency group. Install it with:

```bash
pip install '.[paddle]'
```

Unit tests do not require PaddleOCR or its models installed; they override
the adapter's raw-prediction seam with canned payloads, mirroring the
existing Tesseract test pattern.

### GPU Execution (Phase 4E GPU Enablement)

`PaddleOcrConfig.device` is a free-form string passed straight through to
`PaddleOCR(device=...)`; no code change was needed to make GPU execution
selectable, since the field already accepted any device string the PaddleOCR
constructor understands (`"cpu"`, `"gpu"`, `"gpu:0"`, and so on). What GPU
enablement added was the GPU-capable runtime, an explicit CLI switch, and a
non-benchmark verification step.

**Hardware inspected on the reference development machine:** WSL2 on
Windows, NVIDIA GeForce RTX 3060 (12 GB VRAM), driver 610.43.02 with WSL CUDA
passthrough libraries present under `/usr/lib/wsl/lib/` (`libcuda.so`, etc.).
No system CUDA toolkit (`nvcc`) is installed or required; PaddlePaddle's GPU
wheel bundles its own CUDA/cuDNN runtime and talks to the GPU through
`libcuda.so` provided by the WSL driver passthrough.

**Runtime package.** PaddlePaddle distributes GPU builds as a separate
package, `paddlepaddle-gpu`, from its own CUDA-version-specific package
index rather than standard PyPI — `paddlepaddle` (CPU) and `paddlepaddle-gpu`
cannot both be installed usefully at once (both provide the same importable
`paddle` module), so only one may be installed at a time. Neither `paddleocr`
nor `paddlex` declares a `paddlepaddle` dependency in their own package
metadata (verified via `importlib.metadata`), so installing/reinstalling
`paddleocr` does not silently pull in or clobber whichever `paddle` package
is already present.

Install the GPU runtime, matching the exact `paddlepaddle` version already
used for CPU (avoid unrelated version churn), choosing the CUDA index by
driver version per Paddle's official guidance ("you only need to care about
the GPU driver version," not the toolkit version) — `cu126` requires driver
>= 550.54.14, comfortably below this machine's 610.43.02:

```bash
pip uninstall -y paddlepaddle
pip install "paddlepaddle-gpu==3.3.1" -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
```

To restore CPU-only execution later:

```bash
pip uninstall -y paddlepaddle-gpu
pip install "paddlepaddle>=3,<4"
```

**Selecting the device.** The benchmark CLI exposes `--paddle-device`
(default `cpu`, unchanged), used only with `--ocr-backend paddleocr`:

```bash
python -m w2_pipeline.evaluation.run_pipeline_a <manifest> --ocr-backend paddleocr --paddle-device gpu --limit 5
```

`enable_mkldnn` is a CPU-only oneDNN acceleration flag and has no effect when
`device` selects a GPU; its `False` default remains a CPU-specific
correctness fix and does not need to change for GPU execution.

**Non-benchmark GPU sanity check.** `describe_paddle_gpu_availability()`
(`src/w2_pipeline/extraction/ocr_paddle.py`) queries PaddlePaddle's own
device APIs (`paddle.device.is_compiled_with_cuda()`,
`paddle.device.cuda.device_count()`, `paddle.device.cuda.get_device_name()`)
without loading any OCR model or running inference — a fast, reproducible way
to confirm the GPU runtime is correctly installed before attempting a real
OCR run:

```bash
python -c "from w2_pipeline.extraction.ocr_paddle import describe_paddle_gpu_availability; print(describe_paddle_gpu_availability())"
```

On the reference development machine this reported `compiled_with_cuda:
True`, `cuda_device_count: 1`, and `cuda_device_names: ['NVIDIA GeForce RTX
3060']`, confirming the GPU runtime is correctly installed and the driver is
visible to PaddlePaddle. A minimal one-image PaddleOCR `extract_image()` call
with `device="gpu"` was also run manually against a tiny synthetic test image
(not committed as a benchmark artifact, and not the Phase 4E 5- or
150-document benchmark): it correctly recognized the sample text in `5.96`
seconds total, confirming end-to-end GPU inference works, not just device
visibility. That figure includes one-time GPU/CUDA context and model
initialization overhead and is not a representative per-document throughput
number — only a full benchmark run can establish that.

**Scope boundary.** GPU enablement makes GPU execution available and
selectable; it does not change the incumbent, does not run the Phase 4E
5-document or 150-document PaddleOCR benchmarks on GPU, and does not change
`PaddleOcrConfig`'s default `device` away from `"cpu"`. The full 150-document
PaddleOCR benchmark (on CPU or GPU) remains a separate, not-yet-run task; see
`docs/project-state.md`.

## Parser Strategy

The initial 2026 W-2 parser uses explicit deterministic rules:

- layout-aware employee and employer identity regions
- label/value parsing for federal Boxes 1-8, 10, and 11
- exact `Decimal` money parsing without float conversion
- OCR word-row reconstruction for Tesseract word observations
- OCR full-page geometry/zone fallbacks for employee name/SSN, employer
  EIN/name, federal money boxes, and Box 13 checkbox markers
- Box e employee-name parsing that reads the first-name-and-initial region
  left-to-right, splits a trailing uppercase single-letter token into
  `employee.middle_initial`, and keeps `employee.last_name` and
  `employee.suffix` as independent visual subfields
- conservative tiny OCR artifact filtering in the Box e name zones when a
  much smaller one- to three-character fragment appears alongside normal-size
  name text
- repeated Box 12 code/value rows
- Box 13 checkbox text markers
- Box 14a amount or text values
- Box 14b tipped occupation codes
- repeated state/local rows for Boxes 15-20

Box 9 is not populated by the internal 2026 fixture generator. The canonical
schema still contains the Phase 1 field, but the Phase 4 fixture correction
prevents the renderer from inventing unsupported Box 9 content.

Pipeline A does not transliterate or normalize employee-name accents. Strings
are preserved as recognized and compared exactly by the evaluator; for
example, `Jesús` and `Jesus` remain different semantic values.

### Employer Name OCR Fallback (Phase 6B)

`_apply_ocr_employer_layout_fallbacks` (`parser_2026.py`) fills
`employer.ein` (relocated, unchanged logic) and `employer.name` whenever
the primary label-based path (`_value_after_label`, which requires a
literal `"Name:"` line) leaves them `None`. This exists because the real
2026 W-2 form's Box c presents employer name/address/ZIP as one combined,
unlabeled multi-line block -- the internal synthetic generator's own
rendering convention (explicit `"Name:"`/`"Address 1:"` lines) does not
match the external Symage renders' real-form layout, and `employer.name`
had no OCR recovery path at all before this fix (unlike employee fields,
which already had `_apply_ocr_employee_layout_fallbacks`). `employer.name`
uses a new helper, `_first_row_text_in_zone`, which isolates only the
topmost printed line within a zone -- required because the calibrated
zone `(0.04, 0.35, 0.25, 0.33)` necessarily spans the employer's address
lines too (Box c's three lines are stacked vertically, not laid out
side-by-side the way Box e's name/last-name/suffix sub-fields are).
`employer.address` is not populated by this fallback -- it has the
identical architectural gap but is out of this fix's scope. See
`docs/experiments/phase6b-employer-name-investigation.md` for the full
root-cause investigation and verification.

## Box 13 Visual Checkbox Detection

Box 13 checkbox state (`statutory_employee`, `retirement_plan`,
`third_party_sick_pay`) has two possible signals: the text-prefix mechanism
(`"13 Retirement plan: X"` reconstructed from embedded/OCR text) and an OCR
layout fallback (`_apply_ocr_box_13_layout_fallbacks` in `parser_2026.py`).

The layout fallback historically depended entirely on OCR text output: it
scanned a page zone for observations whose text matched a small allow-list
of mark tokens (`{"x", "v", "✓", "✔", "[v", "v]", "[x", "x]", "4"}`). The
Phase 4E PaddleOCR investigation
(`docs/experiments/pipeline-a-extraction-history.md`) found this allow-list
was implicitly Tesseract-shaped: PaddleOCR's text detector never emits any
observation for the checkbox glyph at all (it is not linguistically
plausible text), while Tesseract's noisier segmentation happens to garble it
into stray text that the allow-list was built to catch. No OCR-token
adjustment can fix a backend that places zero observations in the zone.

`src/w2_pipeline/extraction/checkbox_vision.py` adds a backend-neutral
alternative: it detects the mark directly from page pixels (dark-pixel ink
coverage within a page-relative zone), independent of any OCR engine's text
output. `ObservationAcquirer` (`acquisition.py`) runs this detector on the
same source image used for OCR, for every OCR-routed acquisition (plain
image input, or rendered pages for image-only/mixed PDF routes), and
attaches the result to `ObservationSet.box_13_visual_marks` — a
`dict[str, bool]` keyed by flag name, populated independent of which
`OcrAdapter` produced the surrounding text observations. `parser_2026.py`'s
`_apply_ocr_box_13_layout_fallbacks` ORs this signal in alongside the
existing text-prefix and OCR-token mechanisms (defense in depth; the visual
signal can only add true positives, never override a correct decision from
another path). A visual-detection failure (e.g. an unreadable image)
degrades to "no mark detected" and records a warning rather than failing
extraction, since this is always an additive signal.

**Scope**: only `retirement_plan` has a validated zone. The Symage external
benchmark's 150 clean-render documents have no ground-truth-positive example
for `statutory_employee` or `third_party_sick_pay`, so no zone could be
empirically calibrated for them without risking an unvalidated guess on two
fields that already score 100% under the existing mechanisms. They remain on
the OCR-token fallback only, unchanged.

**Calibration.** `RETIREMENT_PLAN_ZONE = (0.615, 0.655, 0.250, 0.280)` is
expressed as fractions of the true page image dimensions (from
`PIL.Image.size`), not of any OCR-detected text extent — this is a
deliberate correction from the older zones (e.g.
`(0.655, 0.705, 0.535, 0.585)` used by the OCR-token fallback), which are
ratios of `_layout_extent(observations)`, an OCR-detected-text bounding
box that can differ substantially from the true image size (on the external
Symage clean renders, detected text spans roughly the top half of a full
2550x3300 page, so text-extent-relative and true-image-relative ratios are
not interchangeable). Measured across all 150 external Symage clean-render
documents, dark-pixel ink coverage in this zone separates cleanly into an
unchecked cluster (ratio `0.0787`, checkbox border only) and a checked
cluster (ratio `0.1000`, border plus mark) with **zero overlap** across every
document — a wide, safe margin for the `0.09` threshold
(`_INK_COVERAGE_THRESHOLD` in `checkbox_vision.py`).

**Verification.** A 20-document PaddleOCR GPU smoke run against the
external clean-render manifest after this change reached `1.0` field
accuracy (460/460 fields, including 20/20 on `box_13.retirement_plan`,
versus systematic failure before the fix). The same 20 documents under
Tesseract remained unaffected (still 20/20 on `retirement_plan`; its one
remaining failure in that sample is the pre-existing, unrelated
`employer.ein` miss on `symage_900021`). This was a 20-document smoke check,
not a full 150-document benchmark; re-running the full Phase 4C/4E
150-document (and, if warranted, 600-document) benchmarks to update the
authoritative numbers is a natural follow-up, not performed as part of this
implementation task.

**Superseded for the plain-image acquisition path (Phase 8C.11).** The
fixed-zone `RETIREMENT_PLAN_ZONE` detector described above is no longer the
first mechanism `ObservationAcquirer` runs for `box_13.retirement_plan` on
plain-image documents. Phase 8C.10 (`docs/experiments/phase8c10-anchor-relative-checkbox-detector.md`)
introduced an OCR-anchor-relative detector (`extraction/checkbox_anchor.py`)
that locates the printed "Retirement plan" label in the OCR observations
already produced and derives the checkbox's position relative to that
label, rather than a fixed page-coordinate ratio; Phase 8C.11
(`docs/experiments/phase8c11-anchor-checkbox-promotion.md`) promoted it to
`ObservationAcquirer`'s default (`enable_anchor_relative_checkbox=True`).
The fixed-zone detector documented in this section remains in the code and
now serves two narrower roles: an explicit, measurable fallback when the
anchor-relative detector cannot localize the label/checkbox on a
plain-image document (recorded as `checkbox_detection_method =
"fixed_zone_fallback"` in `ObservationSet.box_13_checkbox_evidence`, never
silent), and the unchanged primary mechanism for image-only/mixed PDF
routes, which Phase 8C.10/8C.11 did not touch. Passing
`enable_anchor_relative_checkbox=False` reproduces the pre-8C.11 fixed-zone-only
behavior for diagnostic/backward comparison; production callers no longer
need to (and should not) pass it.

## Benchmark Isolation

Pipeline A integrates with the Phase 3/3B evaluator through `ExtractionInput`.
For external Symage records, the extractor receives only document path, document
ID, source metadata, and optional tax-year hint. It never receives tokens,
bounding boxes, NER tags, FUNSD, COCO, YOLO, or canonical ground truth.

## Benchmark Commands

Internal clean PDF smoke benchmark:

```bash
python -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/generated/manifest.jsonl --variant-id clean_pdf --limit 5
```

External Symage clean-render smoke benchmark:

```bash
python -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl --variant-id external_clean_render --limit 5
```

External Symage clean-render PSM experiment smoke benchmark:

```bash
python -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl --variant-id external_clean_render --tesseract-psm 11 --limit 5
```

External Symage clean-render targeted PSM 11 supplemental smoke benchmark
(main PSM 3 incumbent + PSM 6 SSN recovery + PSM 11 restricted to
`employer.ein` and federal Boxes 3/5/6 only — see "Targeted Supplemental
OCR Passes" above; already run twice at 5-document scale with zero
regressions but no demonstrated recovery benefit yet, not yet eligible for
a larger run):

```bash
python -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl --variant-id external_clean_render --tesseract-psm 3 --tesseract-supplemental-psm 6,11 --limit 5
```

Full external prepared benchmark:

```bash
python -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl
```

External Symage clean-render PaddleOCR smoke benchmark:

```bash
python -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl --variant-id external_clean_render --ocr-backend paddleocr --limit 5
```

The `--tesseract-psm` option selects only the main full-page Tesseract page
segmentation mode for Pipeline A. Supported experiment values are `3`, `11`,
and `12`. The targeted supplemental PSM 6 SSN recovery pass remains enabled so
PSM 11 and PSM 12 experiments isolate the main segmentation mode.
`--tesseract-psm` is ignored when `--ocr-backend paddleocr` is selected.
`--tesseract-supplemental-psm` (default `6`) separately controls the
targeted supplemental pass(es); see "Targeted Supplemental OCR Passes"
above.

## Baseline Results

The initial Phase 4 native-PDF smoke check used internal generated clean PDFs:

```text
documents: 5
field_accuracy: 1.0
failure_rate: 0.0
route: native_pdf
```

Phase 4B installed and exercised Tesseract end to end for external Symage image
benchmarks. The external clean-render benchmark result is:

```text
documents: 150
field_accuracy: 0.9887878787878788
failure_rate: 0.0
average_duration_seconds: 2.2230018675666874
route: ocr
```

The full prepared external-variant benchmark result is:

```text
documents: 600
field_accuracy: 0.8926515151515152
failure_rate: 0.0
average_duration_seconds: 2.1310415448267
route: ocr
```

Variant accuracy:

```text
external_clean_render: 0.9887878787878788
compressed_jpeg: 0.9796969696969697
rotated_png: 0.9245454545454546
blurred_png: 0.6775757575757576
```

Pipeline A performs strongly on clean and compressed external W-2 images,
degrades moderately under rotation, and degrades substantially under blur.
Known weaknesses include employee first-name extraction, Box 13 retirement-plan
checkbox detection, employee SSN/employer EIN under degraded variants, and
blurred federal Boxes 1-6. These results establish a deterministic measured
baseline, not a final production extraction architecture.

After Phase 4B, Box e employee-name semantics were corrected so
`employee.first_name` no longer absorbs the middle initial. Historical Phase
4B results remain useful as OCR baselines, but any benchmark intended to
evaluate employee-name field accuracy must be rerun against regenerated
external ground truth with `employee.middle_initial` included in
`evaluated_field_paths`.

## Phase 4E PaddleOCR Backend Smoke Result

Phase 4E's implementation was validated with a 5-document PaddleOCR smoke
benchmark against the same external Symage clean-render set used by the
Tesseract baselines, before any full-scale PaddleOCR benchmark was run:

```text
documents: 5
field_accuracy: 0.9826086956521739
failed_documents: 0
correct_fields: 113
total_fields: 115
average_duration_seconds: 74.29913957080062
artifact: data/evaluation/results/phase4e_paddleocr_smoke_5.json
```

The only incorrect field across the 5 documents was `box_13.retirement_plan`
(3/5 correct), already a known weak field under the Tesseract incumbent.
Employee identity fields (first/last name, SSN), employer EIN, and all
federal money boxes were exact on this small sample.

This smoke result is directional evidence that the implementation is
functionally correct, not a statistically meaningful comparison against the
150-document Tesseract baseline. The dominant finding from the smoke run is
throughput, not accuracy: PaddleOCR averaged approximately 74.3
seconds/document versus Tesseract's approximately 2.05-2.22
seconds/document, roughly a 35-37x slowdown, driven by deep-learning model
inference versus Tesseract's classical OCR pipeline. A full 150-document
PaddleOCR benchmark would take on the order of 3 hours of wall-clock time at
this rate (longer for the 600-document robustness set), versus roughly 5
minutes for the equivalent Tesseract run. The full 150-document PaddleOCR
comparison has not been run as part of Phase 4E's implementation task and
remains the next step before PaddleOCR could be considered as an incumbent
replacement.
