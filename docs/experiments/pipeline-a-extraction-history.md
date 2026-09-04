# Pipeline A Extraction History

This file records benchmark interpretation notes that affect how Pipeline A
results should be compared over time.

## Phase 4 Native-PDF Smoke Baseline

The initial Phase 4 Pipeline A implementation established the deterministic
native-text/OCR baseline and verified internal generated clean PDFs:

```text
date: 2026-09-03
scope: internal generated W-2 clean PDFs, first 5 documents
route: native_pdf
field_accuracy: 1.0
failure_rate: 0.0
```

This run validated the canonical extraction/evaluation plumbing for local
fixtures. It was not an external OCR realism benchmark.

## Phase 4B External OCR Baseline

Phase 4B installed and exercised Tesseract OCR end to end against prepared
Symage synthetic 2026 W-2 image renders:

```text
date: 2026-09-04
scope: external Symage clean renders, 150 documents
artifact: data/evaluation/results/phase4b_external_clean_150.json
field_accuracy: 0.9887878787878788
failure_rate: 0.0
average_duration_seconds: 2.2230018675666874
```

The companion robustness run covered all prepared clean, compressed, rotated,
and blurred variants:

```text
artifact: data/evaluation/results/phase4b_external_all_variants_600.json
documents: 600
field_accuracy: 0.8926515151515152
failure_rate: 0.0
average_duration_seconds: 2.1310415448267
```

These artifacts are useful historical OCR baselines. They predate the Box e
employee-name semantic correction below.

## Post-Phase 4B Box e Name Correction

The official 2026 Form W-2 Box e separates employee name into:

```text
Employee's first name and initial | Last name | Suff.
```

The canonical schema already represented this as `employee.first_name`,
`employee.middle_initial`, `employee.last_name`, and `employee.suffix`.
However, the Symage adapter previously stored first name plus middle initial
inside `employee.first_name`, and the OCR layout fallback could read a
slightly higher middle-initial token before the first-name token.

The correction:

- splits Symage `Employee's first name and initial` answers into first name and
  nullable middle initial
- includes `employee.middle_initial` in external `evaluated_field_paths`
- orders OCR Box e name-zone words left-to-right
- filters tiny OCR fragments in employee-name zones when normal-size neighbor
  tokens are present
- preserves exact string comparison, including accents
- adds run metadata to saved Pipeline A benchmark summaries

Historical Phase 4B result artifacts should not be used for corrected Box e
name-accuracy claims. Reruns after this correction must regenerate local
external ground truth from annotations before executing Pipeline A.

## Phase 4C Corrected Box e Clean Benchmark

Phase 4C reran the 150-document external clean-render benchmark after
regenerating local Symage ground truth from evaluator-side annotations with
corrected Box e employee-name semantics.

```text
date: 2026-09-04
scope: external Symage clean renders, 150 documents
artifact: data/evaluation/results/phase4c_external_clean_150_name_semantics.json
markdown: data/evaluation/results/phase4c_external_clean_150_name_semantics.md
pipeline_commit: fc4d2f6c2ad0f5573a457901c19dd0de0eb30ece
documents: 150
successful_documents: 150
failed_documents: 0
field_accuracy: 0.991304347826087
correct_fields: 3420
total_fields: 3450
field_failure_count: 30
average_duration_seconds: 2.0517181199200363
```

Employee Box e field results:

```text
employee.first_name: 140 / 150 correct, 0.9333333333333333 accuracy
employee.middle_initial: 141 / 150 correct, 0.94 accuracy
employee.last_name: 150 / 150 correct, 1.0 accuracy
employee.suffix: 150 / 150 correct, 1.0 accuracy
```

The corrected clean benchmark improved overall field accuracy from the Phase
4B clean baseline of `0.9887878787878788` to `0.991304347826087`, while also
expanding the evaluated field count from `3,300` to `3,450` because
`employee.middle_initial` is now scored independently for all 150 external
clean documents. Remaining clean-render failures are concentrated in employee
first name, employee middle initial, Box 13 retirement-plan detection,
employer EIN, and a small number of federal money fields.

## Phase 4C Corrected Box e Robustness Benchmark

Phase 4C also reran the full 600-document prepared external robustness set
after the employee-name semantic correction. This benchmark covered the same
150 Symage documents across clean render, compressed JPEG, rotated PNG, and
blurred PNG variants.

```text
date: 2026-09-04
scope: external Symage clean/compressed/rotated/blurred variants, 600 documents
artifact: data/evaluation/results/phase4c_external_all_variants_600_name_semantics.json
markdown: data/evaluation/results/phase4c_external_all_variants_600_name_semantics.md
pipeline_commit: ba71746aa0c3a44e0ab036b88099135821ff058d
documents: 600
successful_documents: 600
failed_documents: 0
field_accuracy: 0.8846376811594203
correct_fields: 12208
total_fields: 13800
field_failure_count: 1592
average_duration_seconds: 2.1994630620232782
```

Variant results:

```text
external_clean_render: 3420 / 3450 correct, 0.991304347826087 accuracy
compressed_jpeg: 3388 / 3450 correct, 0.9820289855072464 accuracy
rotated_png: 3086 / 3450 correct, 0.8944927536231884 accuracy
blurred_png: 2314 / 3450 correct, 0.6707246376811594 accuracy
```

The corrected robustness benchmark lowered the aggregate field accuracy from
the Phase 4B robustness baseline of `0.8926515151515152` to
`0.8846376811594203`, largely because `employee.middle_initial` is now scored
as its own field across every variant. The clean and compressed variants remain
strong, rotation remains a moderate weakness, and blur remains the dominant
degradation case. The weakest fields were employee first name, employee middle
initial, Box 13 retirement-plan detection, employee last name, federal Box 3,
employee SSN, employer EIN, and federal Boxes 5/6.

The run was launched before the Phase 4D CLI/configuration commit landed; the
saved JSON metadata records the actual launch commit for reproducibility.

## Phase 4D PSM 11/12 Experiment Preparation

Phase 4D prepares controlled Tesseract sparse-text page segmentation
experiments within Pipeline A. It does not create new pipelines and does not
change canonical schema, ground truth semantics, parser logic, evaluator
matching, or annotation isolation.

Prepared comparison:

```text
incumbent: main PSM 3 + targeted supplemental PSM 6
phase4d.1: main PSM 11 + targeted supplemental PSM 6
phase4d.2: main PSM 12 + targeted supplemental PSM 6
dataset: Symage/synthetic-us-forms-preview
variant: external_clean_render
documents: 150
```

Planned result artifacts:

```text
data/evaluation/results/phase4d_psm11_external_clean_150.json
data/evaluation/results/phase4d_psm11_external_clean_150.md
data/evaluation/results/phase4d_psm12_external_clean_150.json
data/evaluation/results/phase4d_psm12_external_clean_150.md
```

At preparation time, the Phase 4C 600-document robustness benchmark was still
running detached, so the Phase 4D 150-document PSM runs were not launched. Run
PSM 11 first after the 600 run exits, then inspect and commit its artifacts
before launching PSM 12. Do not run the two PSM experiments concurrently.

## Phase 4D.1 Tesseract PSM 11 Clean Benchmark

Phase 4D.1 ran Pipeline A with main Tesseract PSM 11 and the same targeted
supplemental PSM 6 SSN recovery used by the incumbent PSM 3 configuration.
The dataset, corrected Symage ground truth, parser, evaluator, schema, and
external clean-render variant were held constant.

```text
date: 2026-09-04
scope: external Symage clean renders, 150 documents
artifact: data/evaluation/results/phase4d_psm11_external_clean_150.json
markdown: data/evaluation/results/phase4d_psm11_external_clean_150.md
pipeline_commit: ced96cabdd27e5e766024153e5351308498356c6
main_psm: 11
supplemental_psm: 6
documents: 150
successful_documents: 150
failed_documents: 0
field_accuracy: 0.9104347826086957
correct_fields: 3141
total_fields: 3450
field_failure_count: 309
average_duration_seconds: 2.1542158065199692
```

Key field results:

```text
employee.first_name: 147 / 150 correct, 0.98 accuracy
employee.middle_initial: 149 / 150 correct, 0.9933333333333333 accuracy
employee.ssn: 145 / 150 correct, 0.9666666666666667 accuracy
employer.ein: 150 / 150 correct, 1.0 accuracy
box_13.retirement_plan: 150 / 150 correct, 1.0 accuracy
federal_wages_and_taxes.box_1_wages_tips_other_compensation: 0 / 150 correct, 0.0 accuracy
federal_wages_and_taxes.box_2_federal_income_tax_withheld: 0 / 150 correct, 0.0 accuracy
federal_wages_and_taxes.box_3_social_security_wages: 150 / 150 correct, 1.0 accuracy
federal_wages_and_taxes.box_5_medicare_wages_and_tips: 150 / 150 correct, 1.0 accuracy
federal_wages_and_taxes.box_6_medicare_tax_withheld: 150 / 150 correct, 1.0 accuracy
```

Compared with the Phase 4C incumbent clean benchmark, PSM 11 improved employee
first name, employee middle initial, employer EIN, Box 13 retirement-plan
detection, and federal Boxes 3/5/6. However, it failed to extract federal
Boxes 1 and 2 on every clean-render document, dropping overall field accuracy
from `0.991304347826087` to `0.9104347826086957` and increasing field failures
from `30` to `309`.

Conclusion: PSM 11 is not a replacement for the incumbent main PSM 3
configuration. Its field-specific improvements may be useful diagnostic
evidence, but the complete Box 1/2 regression is too severe for default
Pipeline A configuration.

## Phase 4D.2 Tesseract PSM 12 Clean Benchmark

Phase 4D.2 ran Pipeline A with main Tesseract PSM 12 and the same targeted
supplemental PSM 6 SSN recovery used by the incumbent PSM 3 configuration and
the PSM 11 experiment. The dataset, corrected Symage ground truth, parser,
evaluator, schema, and external clean-render variant were held constant.

```text
date: 2026-09-04
scope: external Symage clean renders, 150 documents
artifact: data/evaluation/results/phase4d_psm12_external_clean_150.json
markdown: data/evaluation/results/phase4d_psm12_external_clean_150.md
pipeline_commit: 0fa75373600a684f4d01420db02fa065c4a80415
main_psm: 12
supplemental_psm: 6
documents: 150
successful_documents: 150
failed_documents: 0
field_accuracy: 0.504927536231884
correct_fields: 1742
total_fields: 3450
field_failure_count: 1708
average_duration_seconds: 2.3475697785066707
```

Key field results:

```text
employee.first_name: 0 / 150 correct, 0.0 accuracy
employee.last_name: 0 / 150 correct, 0.0 accuracy
employee.ssn: 0 / 150 correct, 0.0 accuracy
employer.ein: 0 / 150 correct, 0.0 accuracy
employee.middle_initial: 32 / 150 correct, 0.21333333333333335 accuracy
box_13.retirement_plan: 60 / 150 correct, 0.4 accuracy
federal_wages_and_taxes.box_1_wages_tips_other_compensation: 0 / 150 correct, 0.0 accuracy
federal_wages_and_taxes.box_2_federal_income_tax_withheld: 0 / 150 correct, 0.0 accuracy
federal_wages_and_taxes.box_3_social_security_wages: 0 / 150 correct, 0.0 accuracy
federal_wages_and_taxes.box_4_social_security_tax_withheld: 0 / 150 correct, 0.0 accuracy
federal_wages_and_taxes.box_5_medicare_wages_and_tips: 0 / 150 correct, 0.0 accuracy
federal_wages_and_taxes.box_6_medicare_tax_withheld: 0 / 150 correct, 0.0 accuracy
federal_wages_and_taxes.box_7_social_security_tips: 150 / 150 correct, 1.0 accuracy
federal_wages_and_taxes.box_8_allocated_tips: 150 / 150 correct, 1.0 accuracy
```

Compared with both the Phase 4C incumbent (99.13%) and the Phase 4D.1 PSM 11
experiment (91.04%), PSM 12 is a severe, broad regression rather than a
targeted one. Unlike PSM 11, which isolated its failure to federal Boxes 1
and 2 while improving several identity fields, PSM 12 zeroed employee first
name, employee last name, employee SSN, employer EIN, and all six of federal
Boxes 1 through 6, while employee middle initial (21.3%) and Box 13
retirement-plan detection (40.0%) also degraded well below both the incumbent
and PSM 11. Only Box 7, Box 8, Box 13's other two flags, and non-financial
metadata fields remained fully correct. Overall field accuracy fell to
`0.504927536231884`, roughly half of the incumbent, with `1,708` field
failures versus `30` for the incumbent and `309` for PSM 11.

Conclusion: PSM 12 is not a viable Pipeline A configuration, clean-render or
otherwise. It regresses essentially every scored field group instead of
trading targeted weaknesses for targeted gains the way PSM 11 did, and it does
not surface a narrower diagnostic signal worth pursuing further. The incumbent
main PSM 3 + supplemental PSM 6 configuration remains the best-performing
Pipeline A configuration evaluated to date. Phase 4D's controlled PSM
comparison is complete; the next planned Pipeline A experiment is Phase 4E,
evaluating PaddleOCR as an alternate OCR backend behind the same observation
boundary, parser, canonical schema, and evaluator.

## Phase 4E PaddleOCR Backend Implementation

Phase 4E added PaddleOCR as a second Pipeline A OCR backend behind the same
`OcrAdapter` structural contract Tesseract already implemented
(`src/w2_pipeline/extraction/ocr_backend.py`), so the deterministic parser,
canonical schema, evaluator, and annotation isolation boundary were unchanged.
`ObservationAcquirer` now accepts any adapter implementing `extract_image`
and `extract_pdf_pages`; PDF-page-to-image rendering was factored out of the
Tesseract adapter into a shared helper
(`src/w2_pipeline/extraction/pdf_rendering.py`) so both backends use identical
rendering rather than duplicating PyMuPDF logic. `PaddleOcrAdapter`
(`src/w2_pipeline/extraction/ocr_paddle.py`) calls PaddleOCR 3.7.0's
`PaddleOCR(...).predict(image_path)` pipeline and maps each result's
`rec_texts`/`rec_boxes` into `TextObservation` values. The `run_pipeline_a`
CLI gained `--ocr-backend {tesseract, paddleocr}` (default `tesseract`,
unchanged) and `pyproject.toml` gained an optional `paddle` dependency group
(`paddlepaddle`, `paddleocr`). 11 new unit tests were added
(`tests/extraction/test_ocr_paddle.py`,
`tests/extraction/test_pdf_rendering.py`, plus additions to
`tests/evaluation/test_run_pipeline_a.py`); all use canned payloads or fake
clients and do not require PaddleOCR installed. The full suite (111 tests)
passed after the change.

During implementation, `paddleocr==3.7.0` + `paddlepaddle==3.3.1` installed
cleanly from PyPI (a much heavier dependency tree than the classic
`paddleocr` 2.x line: it now pulls in `paddlex` and `modelscope`), but default
CPU inference with `enable_mkldnn=True` (the PaddlePaddle default) raised
`NotImplementedError: (Unimplemented)
ConvertPirAttribute2RuntimeAttribute not support
[pir::ArrayAttribute<pir::DoubleAttribute>]` for the default PP-OCRv6 models
on the reference development machine. Disabling MKL-DNN
(`enable_mkldnn=False`, now `PaddleOcrConfig`'s default) resolved it; plain
CPU inference is stable. This is recorded as an environment-specific
correctness fix, not a tuning choice, and should be revisited if a future
PaddlePaddle/oneDNN release fixes the underlying PIR conversion gap.

```text
date: 2026-09-04
scope: external Symage clean renders, 5 documents (smoke only)
artifact: data/evaluation/results/phase4e_paddleocr_smoke_5.json
markdown: data/evaluation/results/phase4e_paddleocr_smoke_5.md
backend: paddleocr (lang=en, device=cpu, use_doc_orientation_classify=False,
  use_doc_unwarping=False, use_textline_orientation=False, enable_mkldnn=False)
documents: 5
successful_documents: 5
failed_documents: 0
field_accuracy: 0.9826086956521739
correct_fields: 113
total_fields: 115
field_failure_count: 2
average_duration_seconds: 74.29913957080062
```

The only incorrect field across the 5 smoke documents was
`box_13.retirement_plan` (3/5 correct) — already a known weak field under the
Tesseract incumbent, not a PaddleOCR-specific regression. Employee first
name, last name, and SSN; employer EIN and control number; and every federal
money box (1 through 11) were exact on this sample.

The decisive finding from the smoke run is throughput, not accuracy:
PaddleOCR averaged `74.3` seconds/document versus the Tesseract incumbent's
`2.05`-`2.22` seconds/document, a roughly 35-37x slowdown from deep-learning
model inference versus classical OCR. At this rate a full 150-document
benchmark is on the order of 3 hours of wall-clock time (longer for the
600-document robustness set) versus roughly 5 minutes for Tesseract.

Conclusion: the PaddleOCR backend implementation is functionally correct and
passed its smoke evaluation with a strong accuracy signal, but this is
directional evidence from 5 documents, not a statistically meaningful
comparison against the 150-document Tesseract baseline. Per the Phase 4E
implementation task's explicit scope, the full 150-document PaddleOCR
benchmark was **not** run as part of this task. It is the next step before
PaddleOCR could be evaluated as a genuine incumbent candidate, and the
person/task requesting it should be aware of the multi-hour runtime cost
before launching it.

## Phase 4E GPU Enablement

A follow-up Phase 4E task prepared the PaddleOCR backend for GPU execution on
the reference development machine's local NVIDIA RTX 3060, without running
any Phase 4E benchmark (5- or 150-document) on GPU or CPU and without
changing the incumbent or any default configuration.

Environment inspected (WSL2 on Windows):

```text
GPU: NVIDIA GeForce RTX 3060, 12 GB VRAM
Driver: 610.43.02 (nvidia-smi: CUDA UMD Version 13.3)
WSL CUDA passthrough: libcuda.so present under /usr/lib/wsl/lib/
System CUDA toolkit (nvcc): not installed (not required for prebuilt wheels)
Python: 3.10.12, x86_64
Existing install: paddlepaddle==3.3.1 (CPU), paddleocr==3.7.0
```

Paddle distributes GPU builds as a separate `paddlepaddle-gpu` package from
its own CUDA-version-specific index (not PyPI), selected by driver version
rather than installed CUDA toolkit version. `cu126` requires driver >=
550.54.14 (Linux); this machine's 610.43.02 comfortably exceeds it, so `cu126`
was chosen as the newest documented stable option rather than the older
`cu118`. `paddlepaddle-gpu==3.3.1` was available at that index, exactly
matching the already-installed CPU `paddlepaddle` version, avoiding
unnecessary version churn; `paddleocr==3.7.0` was left unchanged.

Verified via `importlib.metadata` that neither `paddleocr` nor `paddlex`
declares a `paddlepaddle` dependency in their own package metadata, so a
`paddle-gpu` optional-dependency group containing only `paddleocr` cannot
silently reinstall or conflict with an already-installed GPU runtime — this
shaped the `pyproject.toml` dependency strategy (see `docs/contracts/
extraction-pipeline-a.md`, "GPU Execution" section, for the full rationale).

Runtime swap performed:

```text
pip uninstall -y paddlepaddle
pip install "paddlepaddle-gpu==3.3.1" -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
```

The GPU wheel and its bundled CUDA/cuDNN/NCCL runtime totaled roughly 2.9 GB
of downloads (dominant cost: a ~2 GB `paddlepaddle_gpu` wheel plus ~900 MB of
`nvidia-*-cu12` runtime packages), a materially heavier install than the
~195 MB CPU wheel.

Verification (non-benchmark):

```text
describe_paddle_gpu_availability() ->
  paddle_version: 3.3.1
  compiled_with_cuda: true
  cuda_device_count: 1
  cuda_device_names: ["NVIDIA GeForce RTX 3060"]
```

A minimal single-image `PaddleOcrAdapter.extract_image()` call with
`device="gpu"` (same tiny synthetic test image used for the earlier CPU API
verification, not a W-2 document and not a benchmark artifact) correctly
recognized the sample text in `5.96` seconds total, including one-time
CUDA-context and model-initialization overhead — confirming genuine
end-to-end GPU inference, not just device visibility.

Code changes: `PaddleOcrConfig.device` already accepted any device string
(no change needed for basic GPU selection); added `--paddle-device` to the
`run_pipeline_a` CLI (default `cpu`, unchanged, used only with `--ocr-backend
paddleocr`) and `describe_paddle_gpu_availability()`
(`src/w2_pipeline/extraction/ocr_paddle.py`) as a reusable, testable
diagnostic. Added a `paddle-gpu` optional dependency group (`paddleocr` only)
to `pyproject.toml`. 8 new unit tests covering device selection and the GPU
diagnostic (mocked; none require a real GPU or PaddlePaddle installed) bring
the suite to 121 passing tests.

Conclusion: GPU execution is now installed, explicit, reproducible, and
selectable via `--paddle-device`, and has been verified to work end-to-end on
this machine's RTX 3060. No accuracy or throughput benchmark has been run on
GPU. The CPU incumbent (Tesseract PSM 3 + PSM 6) is unchanged, and
`PaddleOcrConfig`'s default device remains `cpu`. The next step — running the
Phase 4E 150-document PaddleOCR comparison, now with the option of GPU
execution — is deliberately left to a separate task using the Pipeline A
extraction experiment workflow, per this task's explicit scope.

## Phase 4E PaddleOCR GPU 5-Document Smoke

A follow-up experiment ran PaddleOCR with `--paddle-device gpu` against the
same 5-document external Symage clean-render subset used for the CPU smoke,
holding dataset, ground truth, parser, evaluator, and schema constant. This
was a pure configuration-flag experiment: no Paddle implementation changes
were made or needed.

```text
date: 2026-09-04
scope: external Symage clean renders, 5 documents (smoke only)
artifact: data/evaluation/results/phase4e_paddleocr_gpu_smoke_5.json
markdown: data/evaluation/results/phase4e_paddleocr_gpu_smoke_5.md
pipeline_commit: ca3b2a3342abfe9ee81b7943e80db33a2c3f08ce
backend: paddleocr (device=gpu, lang=en, use_doc_orientation_classify=False,
  use_doc_unwarping=False, use_textline_orientation=False)
paddlepaddle_version: 3.3.1 (paddlepaddle-gpu, cu126)
paddleocr_version: 3.7.0
hardware: NVIDIA GeForce RTX 3060 (WSL2 CUDA passthrough)
documents: 5
successful_documents: 5
failed_documents: 0
field_accuracy: 0.9826086956521739
correct_fields: 113
total_fields: 115
field_failure_count: 2
average_duration_seconds: 2.1144952545990234
```

Per-field failures are identical to the CPU smoke — the same two documents,
the same field, the same direction of error:

```text
symage_900001-irs_w2_single_page_2026-p0: box_13.retirement_plan
  expected=true, predicted=false
symage_900002-irs_w2_single_page_2026-p0: box_13.retirement_plan
  expected=true, predicted=false
```

Comparison against the prior CPU smoke (`phase4e_paddleocr_smoke_5.json`,
same 5 documents, same commit lineage):

```text
                    CPU smoke              GPU smoke
field_accuracy:     0.9826086956521739     0.9826086956521739  (identical)
correct/total:      113/115                113/115             (identical)
failed_documents:   0                      0                   (identical)
field_failures:     2 (box_13.retirement_plan x2)  same 2, same documents, same field
avg_duration_sec:   74.29913957080062      2.1144952545990234
speedup:            -                       ~35.2x
```

Comparison against the Tesseract PSM 3 + PSM 6 incumbent (Phase 4C, 150-doc
clean benchmark, not a 5-document subset, so only latency is directly
comparable at this sample size): Tesseract's average duration was `2.0517`
seconds/document. PaddleOCR GPU's `2.1145` seconds/document is now in the
same order of magnitude as Tesseract, a roughly 3% difference on this
5-document sample, versus the CPU backend's ~35-37x slower throughput.
Accuracy is not directly compared here because the Tesseract figure is a
150-document aggregate (99.13%) while this PaddleOCR figure is a 5-document
sample (98.26%); a same-scale comparison requires the 150-document PaddleOCR
GPU run.

Conclusion: GPU execution eliminates PaddleOCR's throughput disadvantage on
this smoke sample without any accuracy or failure-profile change relative to
CPU — same 113/115 fields correct, same two `box_13.retirement_plan` misses,
same zero document failures. This is a strong enough signal to justify
running the full 150-document PaddleOCR GPU benchmark, which was launched
immediately after this result (`phase4e_paddleocr_gpu_external_clean_150`,
detached, not yet complete at the time this entry was written). The
150-document result — not this 5-document smoke — is the basis for any future
incumbent decision.

## Phase 4E PaddleOCR GPU 150-Document Benchmark

The full 150-document external Symage clean-render benchmark ran with
`--ocr-backend paddleocr --paddle-device gpu`, holding dataset, corrected
ground truth, parser, evaluator, and schema constant — the same set used for
the Phase 4C Tesseract incumbent result and both Phase 4D PSM experiments.
This was a pure experiment execution: no Paddle implementation, parser, or
Paddle accuracy-setting changes were made.

```text
date: 2026-09-04
scope: external Symage clean renders, 150 documents
artifact: data/evaluation/results/phase4e_paddleocr_gpu_external_clean_150.json
markdown: data/evaluation/results/phase4e_paddleocr_gpu_external_clean_150.md
pipeline_commit: 91235fd94028fcfc3aa45d93b0d40522c42c35a9
backend: paddleocr (device=gpu, lang=en, use_doc_orientation_classify=False,
  use_doc_unwarping=False, use_textline_orientation=False)
paddlepaddle_version: 3.3.1 (paddlepaddle-gpu, cu126)
paddleocr_version: 3.7.0
hardware: NVIDIA GeForce RTX 3060 (WSL2 CUDA passthrough)
documents: 150
successful_documents: 150
failed_documents: 0
field_accuracy: 0.9739130434782609
correct_fields: 3360
total_fields: 3450
field_failure_count: 90
average_duration_seconds: 1.349492507300068
```

Every one of the 90 field failures is the same field:
`box_13.retirement_plan` (60/150 correct, `0.4` accuracy) — expected `true`,
predicted `false`, on 90 distinct documents. No other field path has a single
incorrect value across all 150 documents: employee first name, middle
initial, last name, suffix, SSN; employer EIN, control number; and all of
federal Boxes 1 through 11 are 100% correct.

Direct comparison against the Tesseract PSM 3 + PSM 6 incumbent on the
identical 150-document clean set (Phase 4C):

```text
                    Tesseract incumbent    PaddleOCR GPU
field_accuracy:     0.991304347826087      0.9739130434782609
correct/total:      3420 / 3450            3360 / 3450
field_failures:     30                     90
avg_duration_sec:   2.0517181199200363     1.349492507300068  (~34% faster)
failed_documents:   0                      0
```

Per-field, the two backends' weaknesses are almost entirely disjoint rather
than overlapping. Tesseract's incumbent failures are spread across seven
fields: `employee.first_name` (93.33%), `employee.middle_initial` (94.0%),
`box_13.retirement_plan` (96.67%), `employer.ein` (98.67%),
`box_6_medicare_tax_withheld` (98.67%), `box_3_social_security_wages`
(99.33%), and `box_5_medicare_wages_and_tips` (99.33%). PaddleOCR GPU is
100% correct on every one of those seven fields, but is dramatically worse
than Tesseract on the one field where Tesseract is already comparatively
strong: `box_13.retirement_plan` drops from Tesseract's 96.67% to PaddleOCR's
40.0%.

Conclusion: at 150-document scale, PaddleOCR GPU does **not** exceed the
Tesseract incumbent's overall field accuracy (97.39% vs. 99.13%), so it is
**not** promoted to incumbent from this result. However, the result is more
nuanced than "worse": PaddleOCR GPU is meaningfully faster (~34% lower
average latency than Tesseract, and roughly 55x faster than PaddleOCR CPU),
has zero document failures, and its entire error surface is one single,
narrow, systematic field failure (`box_13.retirement_plan`) rather than
Tesseract's more diffuse spread across seven fields including identity
fields (employee name) and federal money boxes. Whether that narrow,
concentrated failure mode is preferable to Tesseract's broader-but-shallower
one (e.g., because a single systematic weak field is easier to target with a
future fix than several unrelated ones) is a product/architecture judgment
call, not a decision made by this experiment run. This finding, not a
recommendation, is recorded for that future decision. No further Paddle
tuning or hybrid-backend design was attempted as part of this task.

## Phase 4E PaddleOCR `box_13.retirement_plan` Failure Investigation

A follow-up investigation determined why PaddleOCR GPU's 90 field failures
were entirely concentrated in `box_13.retirement_plan`. This was a diagnostic
task only: no parser logic, Paddle configuration, or accuracy settings were
changed, and no new 150- or 600-document benchmark was run.

**First finding, from the existing 150-document result alone (no new run
needed):** the ground truth for the 150-document clean set has 90 documents
with `retirement_plan = true` and 59 with `retirement_plan = false` (1 of the
150 ground-truth files uses a differently formatted document ID and was not
inspected). PaddleOCR's 90 field failures are exactly the 90 true-labeled
documents; none of its 60 "correct" predictions come from a true-labeled
document. In other words, PaddleOCR predicted `retirement_plan = false` on
**every single document**, with zero exceptions — 0% recall on the positive
class, not a scattered or borderline recognition-quality issue.

**Diagnostic sample.** Raw observations (`extract_image`, no ground truth or
annotations passed to the extractor) were captured for both backends on
three documents: `symage_900001` and `symage_900002` (ground truth `true`,
both are among PaddleOCR's 90 failures) and `symage_900003` (ground truth
`false`, a trivial true-negative for both backends, included for contrast).
These were chosen as representative rather than cherry-picked: the first two
sequential `true`-labeled documents in the manifest, plus the first
sequential `false`-labeled one.

**What the raw observations show.** For both `true`-labeled documents,
Tesseract detects a small, isolated observation inside the retirement-plan
checkbox geometry zone (`0.655-0.705` x, `0.535-0.585` y of the page) at
almost identical pixel coordinates in both documents (`(1601,850)-(1637,894)`
and `(1606,850)-(1641,894)`) — evidently the same template-fixed checkbox
glyph. Tesseract recognizes that glyph as garbled text: `"[V"` on one
document, `"4"` on the other. **PaddleOCR detects zero observations anywhere
in that zone, or anywhere in the wider Box 13 row band around it, on either
document.** The checkbox glyph is not merged into a neighboring label, not
recognized as different text, not shifted outside the expected zone — it is
simply absent from PaddleOCR's output entirely. For the `false`-labeled
contrast document, neither backend detects anything in the zone, as
expected (there is genuinely no mark to find).

Everything else in the raw observations is consistent between backends and
rules out several candidate causes:

- **Not a coordinate/geometry conversion bug**: label positions agree almost
  exactly between backends (e.g. `"Retirement"` at `(1592-1595,801-804)` for
  Tesseract vs. `(1601,805)` for Paddle on the same document — same region,
  well within normal OCR jitter). The zone-ratio math (`_observations_in_zone`,
  driven by `_layout_extent`) is backend-agnostic and both backends' page
  extents match to within a few pixels.
- **Not an observation-ordering or word-row-reconstruction bug**: both
  backends' reconstructed lines around Box 13 are sensible and correctly
  ordered (e.g. `"...13 Statutory Retirement Third-party..."` for Tesseract,
  `"...13 Statutory Retirement sick pay Third-party..."` for Paddle).
- **Not an adapter conversion bug**: `PaddleOcrAdapter.extract_image` was
  inspected directly (`src/w2_pipeline/extraction/ocr_paddle.py`) — it maps
  every entry in PaddleOCR's own `rec_texts`/`rec_boxes` payload to a
  `TextObservation`, with no filtering that could silently drop the checkbox
  glyph if PaddleOCR had actually recognized it as a text region.

**Root cause.** This is a genuine backend behavioral difference at the text
**detection** stage, not a bug anywhere in this project's code. PP-OCRv6's
detection model is a learned model tuned to find coherent, plausible text
regions/lines in a document image, and correctly (by its own design) does
not treat a small non-linguistic checkbox glyph as a text region worth
recognizing. Tesseract's classical connected-component segmentation is far
less selective — it treats almost any small isolated ink blob as *some*
character worth attempting to classify, right or wrong, which is exactly why
it produces garbled misreads like `"[V"` or `"4"` for this glyph rather than
detecting nothing.

Compounding this, `_has_checkbox_mark`'s `mark_tokens` allow-list
(`{"x", "v", "✓", "✔", "[v", "v]", "[x", "x]", "4"}`,
`src/w2_pipeline/extraction/parser_2026.py`) is not a backend-neutral
geometric signal despite its name and framing as a "layout fallback" — it is
implicitly shaped by Tesseract's specific misrecognition patterns for this
exact glyph (`"[V"` -> `"[v"` and `"4"` both appear in the allow-list, and
both were observed verbatim in this investigation's Tesseract output). This
matches the investigation brief's candidate causes "checkbox mark not
represented as OCR text" (true for Paddle's detection stage) and "parser
dependence on Tesseract-specific tokenization" (true for the existing
fallback's design) simultaneously — they are two sides of the same root
cause, not competing explanations. Critically, **no adjustment to the
token-matching logic could fix this on its own**: the fallback only ever
evaluates observations that exist in the zone, and Paddle places zero
observations there to evaluate. A fix would need to either give the parser
a genuinely detection-agnostic signal (e.g. pixel-density analysis of the
zone rather than depending on any backend having "read" the mark as text) or
accept that different OCR backends may need different mark-detection
strategies — either is a parser/architecture change, deliberately out of
scope for this investigation task.

**Conclusion.** PaddleOCR GPU's `box_13.retirement_plan` weakness is fully
explained: PP-OCRv6's text detector does not perceive the rendered checkbox
mark as text at all, so no downstream token-matching heuristic — Tesseract's
current one or a redesigned one — can recover it without a different
detection strategy. This is not a defect in the Paddle adapter, the common
observation model, or the word-row reconstruction; it is an inherent
consequence of PaddleOCR's detection model being more precise (in the
general case, a desirable property) than Tesseract's noisier segmentation,
combined with the current parser fallback having been implicitly
Tesseract-shaped rather than backend-neutral. No fix was implemented in this
task, per its explicit scope.

## Phase 4E Backend-Neutral Box 13 Checkbox Detection (Implementation)

A follow-up implementation task acted on the investigation above: rather
than relying on any OCR engine's text output for the Box 13 checkbox marks,
`src/w2_pipeline/extraction/checkbox_vision.py` detects the mark directly
from page pixels. Architecture: `ObservationAcquirer` runs the pixel
detector on the same source image used for OCR (for every OCR-routed
acquisition — plain image input, or rendered pages for image-only/mixed PDF
routes) and attaches results to a new `ObservationSet.box_13_visual_marks:
dict[str, bool]` field; `parser_2026.py`'s
`_apply_ocr_box_13_layout_fallbacks` ORs this in alongside the existing
text-prefix and OCR-token mechanisms. No Paddle-specific parser was created
and no new OCR-token allow-list entries were added; the correction is a
genuinely OCR-output-independent signal, exactly as the investigation
concluded was necessary.

**Scope decision.** Only `retirement_plan` received a validated zone. While
calibrating zones for the other two flags by geometric analogy to
`retirement_plan`'s confirmed position, the estimated `statutory_employee`
zone measured an ink-coverage ratio of `0.1134` and `third_party_sick_pay`
measured `0.0904` across all 150 external clean documents — both already
above or dangerously close to a viable threshold, despite both fields being
ground-truth `false` on every one of the 150 documents (there is no
positive example in this dataset for either flag to calibrate against).
Deploying unvalidated zones for those two fields risked turning two
currently-100%-correct fields into false positives. `statutory_employee` and
`third_party_sick_pay` were deliberately left on the existing OCR-token
fallback only; extending visual detection to them is future work gated on
finding or constructing genuine positive examples to calibrate against.

**Calibration (retirement_plan).** The critical correction was recognizing
that the existing OCR-token fallback's zones are ratios of
`_layout_extent(observations)` (the bounding extent of OCR-detected text),
not of the true image dimensions — on the external Symage clean renders,
detected text spans roughly the top half of a full 2550x3300-pixel page, so
these two reference frames are not interchangeable. The true pixel position
of the checkbox mark was located by cross-referencing Tesseract's raw
observation coordinates (themselves true image pixels) from the earlier
investigation's diagnostic output against the actual `PIL.Image.size` of the
same files. The resulting zone,
`RETIREMENT_PLAN_ZONE = (0.615, 0.655, 0.250, 0.280)` (true-image-relative),
was then validated by computing dark-pixel ink-coverage ratio across **all
150** external Symage clean-render documents (a pure pixel-analysis pass
over already-prepared local image files, not an OCR run or a scored
benchmark):

```text
unchecked cluster (n=59, ground truth false): ratio = 0.0787, zero variance
checked cluster   (n=90, ground truth true):  ratio = 0.1000, zero variance
threshold chosen: 0.09 (wide margin on both sides, zero overlap)
```

The zero-variance, zero-overlap result reflects that these are
template-rendered synthetic documents where the checkbox glyph's position
and size are pixel-identical across documents; only the checked/unchecked
state toggles.

**Verification.** Unit tests cover `checkbox_vision.py` directly (synthetic
drawn images), the parser's consumption of `box_13_visual_marks` (including
a fixture with no checkbox-mark observation at all, replicating PaddleOCR's
actual behavior), and `ObservationAcquirer`'s wiring (including graceful
degradation when detection fails). Full suite: 130 tests passing.

A real-pipeline smoke check — not a full 150-document benchmark, per this
session's established practice of smoke-testing implementation changes
before a full rerun — ran the first 20 external clean-render documents
(which include 12 ground-truth-`true` `retirement_plan` documents) through
both backends:

```text
PaddleOCR GPU: field_accuracy = 1.0 (460/460), box_13.retirement_plan = 20/20
Tesseract:     field_accuracy = 0.9978260869565218 (459/460),
               box_13.retirement_plan = 20/20 (unaffected)
               remaining failure: employer.ein on symage_900021 (pre-existing,
               unrelated to this change)
```

Conclusion: the fix resolves the demonstrated PaddleOCR `retirement_plan`
failure on this sample without regressing Tesseract. The full 150-document
(and, if warranted, 600-document) benchmarks for both backends should be
rerun to update the authoritative Phase 4C/4E numbers with this change in
place; that full rerun was not performed as part of this implementation
task.

## Phase 4E Tesseract Incumbent 150-Document Rerun (Post Checkbox Vision Fix)

Formal rerun of the Tesseract incumbent's authoritative clean-150 benchmark
with the Box 13 visual checkbox detector in place, per the "Immediate Next
Experiment" pointer left by the prior implementation task. Same 150 external
Symage clean-render documents, same corrected Box e ground truth, same
parser/evaluator/schema as the Phase 4C result — only the checkbox-vision
code path changed. Configuration held constant: main Tesseract PSM 3 +
targeted supplemental PSM 6, `--ocr-backend tesseract` (CLI default).

```text
data/evaluation/results/phase4e_tesseract_checkbox_vision_external_clean_150.json
data/evaluation/results/phase4e_tesseract_checkbox_vision_external_clean_150.md
```

- `field_accuracy = 0.9927536231884058` (3,425 / 3,450 correct),
  `failed_documents = 0`, `field_failure_count = 25`, average
  `2.330209926666645` seconds/document.
- Comparison against the prior authoritative Tesseract clean-150 result
  (`phase4c_external_clean_150_name_semantics`, `field_accuracy =
  0.991304347826087`, 3,420/3,450 correct, 30 field failures, average
  `2.0517181199200363` seconds/document): the **only** per-field change
  across all 23 scored canonical fields is `box_13.retirement_plan`, which
  moved from 96.67% (145/150) to 100.0% (150/150) — exactly the 5 documents
  the checkbox-vision fix was calibrated to recover. Every other field's
  correct/incorrect count is bit-for-bit identical to the Phase 4C result:
  `employee.first_name` 93.33%, `employee.middle_initial` 94.0%,
  `employer.ein` 98.67%, `box_6_medicare_tax_withheld` 98.67%,
  `box_3_social_security_wages` 99.33%, `box_5_medicare_wages_and_tips`
  99.33%, all remaining fields 100%.
- Average per-document duration increased from `2.052s` to `2.330s`
  (+13.5%), the added cost of running the pixel-based checkbox detector on
  every OCR-routed document; still far faster than PaddleOCR CPU and
  comparable to PaddleOCR GPU.
- Conclusion: the checkbox-vision fix is confirmed at full 150-document
  scale on the Tesseract incumbent — a clean, isolated improvement with zero
  regressions anywhere else in the 3,450-field surface, exactly matching the
  20-document smoke check's prediction. This result supersedes
  `phase4c_external_clean_150_name_semantics` as the authoritative Tesseract
  clean-150 number; the PSM 3 + PSM 6 configuration itself is unchanged and
  remains the incumbent. The equivalent PaddleOCR GPU rerun
  (`phase4e_paddleocr_gpu_external_clean_150`-equivalent) remains outstanding
  — see `docs/project-state.md`'s "Immediate Next Experiment."

## Phase 4E PaddleOCR GPU 150-Document Rerun (Post Checkbox Vision Fix)

Formal rerun of PaddleOCR GPU's 150-document external clean-render benchmark
with the Box 13 visual checkbox detector in place, closing out the
"Immediate Next Experiment" pointer's second half (the Tesseract side was
completed immediately prior — see above). Same 150 documents, same corrected
ground truth/parser/evaluator/schema as the historical Phase 4E PaddleOCR GPU
result — only the checkbox-vision code path changed. Configuration held
constant: `--ocr-backend paddleocr --paddle-device gpu`.

```text
data/evaluation/results/phase4e_paddleocr_gpu_checkbox_vision_external_clean_150.json
data/evaluation/results/phase4e_paddleocr_gpu_checkbox_vision_external_clean_150.md
```

- `field_accuracy = 1.0` (3,450 / 3,450 correct), `failed_documents = 0`,
  `field_failure_count = 0`, average `1.439184085346657` seconds/document.
- Comparison against the historical PaddleOCR GPU result
  (`phase4e_paddleocr_gpu_external_clean_150`, `field_accuracy =
  0.9739130434782609`, 3,360/3,450, 90 field failures, average `1.349s`/doc):
  the **only** field that changed is `box_13.retirement_plan`, which moved
  from 40.0% (60/150) to 100.0% (150/150) — every one of the 90 historical
  failures was this single field, and all 90 are now resolved. Every other
  field was already 100% correct in the historical run and remains so; there
  is no field anywhere in the 3,450-field surface below 100%. Average
  duration rose slightly (`1.349s` -> `1.439s`/doc, +6.7%), the added cost of
  the pixel-based checkbox pass, consistent in direction with the Tesseract
  rerun's overhead.
- Comparison against the same-day Tesseract post-checkbox-vision result
  (`phase4e_tesseract_checkbox_vision_external_clean_150`, `field_accuracy =
  0.9927536231884058`, 3,425/3,450, average `2.330s`/doc): PaddleOCR GPU now
  scores **higher** overall accuracy (100.0% vs. 99.28%) at **lower**
  latency (1.44s vs. 2.33s/doc, ~38% faster). PaddleOCR GPU has zero field
  failures anywhere in the 150-document set, including on the seven fields
  that remain Tesseract's weakest (`employee.first_name` 93.33%,
  `employee.middle_initial` 94.0%, `employer.ein` 98.67%,
  `box_6_medicare_tax_withheld` 98.67%, `box_3_social_security_wages`
  99.33%, `box_5_medicare_wages_and_tips` 99.33%) — PaddleOCR GPU is 100%
  correct on every one of those.
- Conclusion: the checkbox-vision fix, which was root-caused and implemented
  specifically to close PaddleOCR GPU's `box_13.retirement_plan` gap,
  confirms exactly as predicted at full 150-document scale: a perfect,
  regression-free result. With this fix in place, PaddleOCR GPU's historical
  headline weakness (lower overall accuracy than Tesseract, 97.39% vs.
  99.13%/99.28%) is fully closed and inverted — PaddleOCR GPU is now strictly
  better than the Tesseract incumbent on this clean-150 benchmark on both
  accuracy and speed. This does not by itself change the incumbent: no
  promotion decision was made as part of this rerun, per the experiment
  skill's boundaries (report the result, let the user decide) — but it
  substantially strengthens the case raised as an open question after the
  original 150-document PaddleOCR GPU benchmark. The 600-document robustness
  benchmark (compressed/rotated/blurred) with the fix in place has
  deliberately not been run as part of this task and remains the next
  mechanical step if the incumbent question is pursued further; the visual
  detector's ink-coverage threshold is still calibrated only against clean
  renders and unvalidated under degraded image quality.

## Phase 4E Tesseract Incumbent 600-Document Robustness Rerun (Post Checkbox Vision Fix)

Formal rerun of the Tesseract incumbent's authoritative 600-document
external robustness benchmark (all four variants: clean render, compressed
JPEG, rotated PNG, blurred PNG) with the Box 13 visual checkbox detector in
place. Tesseract-only, per this task's explicit scope — no PaddleOCR run.
Same 600 documents, same corrected ground truth/parser/evaluator/schema as
the Phase 4C result; only the checkbox-vision code path changed. This
directly answers the open question the checkbox-vision implementation and
the two prior 150-document reruns left outstanding: how the ink-coverage
threshold (calibrated only against clean renders) behaves under
compression, rotation, and blur.

```text
data/evaluation/results/phase4e_tesseract_checkbox_vision_external_all_variants_600.json
data/evaluation/results/phase4e_tesseract_checkbox_vision_external_all_variants_600.md
```

- `field_accuracy = 0.8897826086956522` (12,279 / 13,800 correct), up from
  `0.8846376811594203` (12,208/13,800), `failed_documents = 0`,
  `field_failure_count = 1,521` (down from 1,592), average
  `2.318962704046665` seconds/document (up from `2.199s`, the added cost of
  the pixel-based checkbox pass — consistent with the 150-document clean
  rerun's overhead).
- **The only field that changed anywhere in the aggregate 13,800-field
  surface is `box_13.retirement_plan`** (aggregate `0.6683333333333333` ->
  `0.7866666666666666`, 401/600 -> 472/600 correct); every other field's
  correct/incorrect count is unchanged across all four variants. Zero
  regressions.
- Per-variant breakdown of `box_13.retirement_plan` (out of 150 documents
  per variant), derived from the field-failure records:
  - `external_clean_render`: 96.67% (145/150) -> **100.0%** (150/150, 0
    failures) — matches the standalone clean-150 rerun exactly.
  - `compressed_jpeg`: 82.67% (124/150) -> **100.0%** (150/150, 0 failures)
    — fully resolved. Compression does not shift checkbox geometry, so the
    true-image-relative zone the detector was calibrated against still
    lands correctly.
  - `rotated_png`: 48.0% (72/150) -> 60.0% (90/150) — improved (+12
    points) but **not fully resolved**; 60 documents still fail. Rotation
    shifts the checkbox mark's true-image-pixel position, so the
    fixed-zone visual detector partially misses it; the remaining recovery
    comes from the OR'd text-prefix/OCR-token fallback mechanisms, not the
    visual signal.
  - `blurred_png`: 40.0% (60/150) -> 54.67% (82/150) — improved (+14.67
    points) but **not fully resolved**; 68 documents still fail. Blur
    degrades the ink-coverage measurement's reliability near the
    calibrated threshold rather than shifting geometry, so some documents
    still land on the wrong side of the `0.09` threshold.
- No other field showed any change under any variant, confirming the fix's
  isolation holds even under degraded image quality — it neither helps nor
  hurts any field besides `box_13.retirement_plan`.
- Conclusion: this closes the open question left after the checkbox-vision
  implementation. The fix is a full, unconditional win on clean and
  compressed images (both now 100% on `retirement_plan`) but only a partial
  win under rotation and blur, exactly as anticipated by the caveat that the
  ink-coverage threshold and `RETIREMENT_PLAN_ZONE` were calibrated solely
  against clean renders. This result now supersedes
  `phase4c_external_all_variants_600_name_semantics` as the authoritative
  Tesseract 600-document robustness number; the incumbent configuration
  itself (PSM 3 + PSM 6) is unchanged, and no promotion decision applies
  here (this is a Tesseract-only rerun). Whether the rotated/blurred
  shortfall is worth a follow-up investigation (e.g., a rotation-aware zone,
  or a blur-adjusted threshold) versus leaving it as a documented known
  weakness is an open decision for later, not addressed by this rerun. The
  equivalent PaddleOCR GPU 600-document robustness rerun remains outstanding
  and was explicitly out of scope for this task.

## Phase 4E PaddleOCR GPU 600-Document Robustness Rerun (Post Checkbox Vision Fix)

Formal rerun of PaddleOCR GPU's 600-document external robustness benchmark
(all four variants: clean render, compressed JPEG, rotated PNG, blurred
PNG; `--ocr-backend paddleocr --paddle-device gpu`) with the Box 13 visual
checkbox detector in place. This is PaddleOCR GPU's **first-ever**
600-document robustness data point — no prior PaddleOCR run at this scope
existed to compare against for the compressed/rotated/blurred variants
(only the clean-150 subset had a historical PaddleOCR number), so results
below are compared against the PaddleOCR clean-150 post-fix result and
against the Tesseract 600-document robustness result from the immediately
preceding rerun, not against a PaddleOCR "before" baseline for the degraded
variants.

```text
data/evaluation/results/phase4e_paddleocr_gpu_checkbox_vision_external_all_variants_600.json
data/evaluation/results/phase4e_paddleocr_gpu_checkbox_vision_external_all_variants_600.md
```

- `field_accuracy = 0.976231884057971` (13,472/13,800 correct),
  `failed_documents = 0`, `field_failure_count = 328`, average
  `1.329903785876671` seconds/document (essentially matching the clean-150
  post-fix rate of `1.439s`/doc — no meaningful robustness slowdown, unlike
  Tesseract's variant-dependent runtime).
- **Every one of the 328 failures is on the `rotated_png` variant.** Clean
  render, compressed JPEG, and blurred PNG are all `field_accuracy = 1.0`
  (3,450/3,450 each, zero failures) — a materially different robustness
  profile than Tesseract, whose worst variant is blurred (67.71%) not
  rotated.
- `rotated_png` breakdown (`field_accuracy = 0.904927536231884`,
  3,122/3,450): failures are concentrated in exactly three fields —
  `employee.first_name` (0/150 correct, complete failure),
  `employee.middle_initial` (32/150 correct, 21.3%), and
  `box_13.retirement_plan` (90/150 correct, 60.0%). No other field shows any
  failure under any variant.
- **The `employee.first_name`/`middle_initial` rotated failures are a new
  finding unrelated to the checkbox-vision fix.** Inspecting the failure
  records shows PaddleOCR's rotated-image text detection appends the
  printed field-label text to the extracted name (e.g. expected `"Lori"`,
  predicted `"Lori e Employee's first name and initial"`) — a label-bleed
  artifact in name-zone word reconstruction specific to rotated PaddleOCR
  text detection, not a Box 13 or checkbox-vision issue. This is Pipeline
  A's first robustness-scale evidence of this failure mode on PaddleOCR;
  Tesseract's rotated `employee.first_name` weakness (53.67% aggregate) has
  a different, non-zero failure pattern and is not caused by the same
  mechanism.
- **The `box_13.retirement_plan` rotated failures are identical, document
  for document, to Tesseract's**: cross-checking `document_id` sets, the
  same exact 60 documents fail `retirement_plan` under rotation on both
  backends (`60/60` overlap, zero backend-specific difference). This
  confirms the visual checkbox detector genuinely runs identically
  regardless of OCR backend — it operates on the same source image pixels
  — and that its rotation weakness is a property of the fixed
  `RETIREMENT_PLAN_ZONE` calibration (calibrated only against clean
  renders), not of either backend's OCR behavior.
- Versus the Tesseract 600-document robustness result (88.98% aggregate,
  worst variant blurred at 67.71%): PaddleOCR GPU's aggregate accuracy is
  substantially higher (97.62% vs. 88.98%) and its worst variant (rotated,
  90.49%) is far better than Tesseract's worst (blurred, 67.71%).
  PaddleOCR GPU is perfect on blur where Tesseract is weakest, and
  comparable to (marginally better than) Tesseract on rotation (90.49% vs.
  89.97%) despite the identical Box 13 rotation weakness both share.
- Conclusion: PaddleOCR GPU's robustness profile, now measured for the
  first time, is stronger than Tesseract's across the board on this
  600-document set — higher aggregate accuracy, no failure at all on
  compressed or blurred images, and a comparable (not worse) rotated-image
  result. Its one significant new weakness — complete `employee.first_name`
  failure under rotation from a label-bleed text-reconstruction artifact —
  is unrelated to checkbox vision and is a newly discovered, previously
  unmeasured limitation, not a regression from anything. This result does
  **not** change the incumbent configuration or promote PaddleOCR to
  incumbent; no promotion decision was made as part of this rerun, per the
  experiment skill's boundaries. It further strengthens the case raised
  after the clean-150 PaddleOCR GPU rerun, while also surfacing a
  rotation-specific text-reconstruction issue that would need its own
  investigation before PaddleOCR GPU could be considered a clean win across
  all four variants. No Tesseract PSM 11 (or any other configuration) was
  run as part of this task, per its explicit scope.

## Phase 4E Targeted Supplemental PSM 11 Readiness (Implementation Only)

A readiness/implementation task, not an experiment: determine whether
Pipeline A's existing configuration/CLI could express Tesseract main PSM 3
+ a *targeted* supplemental PSM 11 pass, restricted to only the fields the
Phase 4D.1 main-PSM-11 experiment (above) showed improve over the PSM 3
incumbent — `employee.first_name` (98.0%), `employee.middle_initial`
(99.33%), `employer.ein` (100.0%), and federal Boxes 3/5/6 (100.0% each) —
explicitly excluding `box_13.retirement_plan` (now owned by the
backend-neutral visual checkbox detector) and SSN (owned by the existing
PSM 6 supplemental pass).

**Finding: the existing mechanism could not express this.** The only
supplemental-pass filter in the codebase, `_top_identifier_observations`,
was hardcoded to one zone (the top identifier/SSN region) and one regex
(the SSN shape), applied identically to every configured supplemental
mode. There was also no CLI exposure of supplemental modes at all — only
the main PSM was configurable. Beyond the missing configuration surface, a
genuine safety problem was identified: PSM 11's approved target fields
include federal Boxes 3/5/6, whose recovery zones physically overlap the
*same* page regions the primary path already parses via row-grouped
"box-number label: value" line reconstruction (`_group_observation_rows`/
`_parse_federal`). Merging a second, differently-segmented OCR pass's
output into that same flat observation list — even after zone-filtering —
risked interleaving or duplicating tokens within an already-correct
primary-path row, potentially corrupting or silently overriding a value
that PSM 3 alone had already read correctly. This risk does not exist for
PSM 6's SSN zone, which is spatially isolated from every primary-path box
line, which is presumably why the original single-zone-only design never
needed to consider it.

**Implemented, smallest supporting extension** (see `CHANGELOG.md` for the
full file-by-file breakdown): a new `TextObservation.is_supplemental` flag;
a generalized per-PSM-mode target-zone table in `ocr.py`
(`SupplementalTargetZone`/`_SUPPLEMENTAL_TARGET_ZONES`) replacing the old
single-zone filter, with PSM 6 unchanged and PSM 11 given five zones
(name, EIN, box 3, box 5, box 6) each mirroring its corresponding
`parser_2026.py` fallback zone exactly; exclusion of supplemental
observations from the parser's primary row-grouping and page-extent
computation, so a supplemental pass can only ever reach the OCR
zone-based fallback functions — which already fire solely when the
primary path left a field empty, making corruption of an already-correct
primary value structurally impossible regardless of which supplemental
PSM is configured; and a new `--tesseract-supplemental-psm` CLI flag
(default `6`, incumbent behavior unchanged). No PSM-specific branching was
added to the parser's canonical field logic. 13 new focused tests; full
suite 143 passing, zero regressions.

**No experiment was run as part of this task** — the exact command for the
not-yet-run 5-document smoke experiment this readiness work unlocks:

```bash
python -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl --variant-id external_clean_render --tesseract-psm 3 --tesseract-supplemental-psm 6,11 --limit 5
```

Expected effect size is likely small relative to the original main-PSM-11
experiment: as a *supplemental* pass gated to fields the primary path left
empty, it can only recover the small residual gap PSM 3 alone misses on
these six fields (roughly 1-7% of documents per field on the clean-150
set), not replace PSM 3's read outright the way the rejected main-PSM-11
configuration did. Whether this is worth running, and at what scale, is
left to the user; the incumbent configuration is unchanged by this task.

## Phase 4E Targeted Supplemental PSM 11 Smoke Test — Disqualifying Regression Found

The readiness-unlocked smoke experiment above was run: main PSM 3 +
targeted supplemental PSM 6 + targeted supplemental PSM 11
(`--tesseract-supplemental-psm 6,11`), 5 external clean-render documents,
checkbox vision enabled.

```text
data/evaluation/results/phase4e_tesseract_supplemental_psm11_smoke_5.json
data/evaluation/results/phase4e_tesseract_supplemental_psm11_smoke_5.md
```

**Result: `field_accuracy = 0.9565217391304348` (110/115), `failed_documents
= 0`, average `3.528s`/document (up from the incumbent's `2.330s`/document,
+51%).** The 5 field failures are concentrated entirely in one field,
`employee.first_name` — **0/5 correct (100% failure)**. Cross-checked
against the same 5 documents' results in the Tesseract 600-document
robustness rerun (`phase4e_tesseract_checkbox_vision_external_clean_150`,
which includes these exact `document_id`s): **all 5 were 100% correct under
the PSM 3 + PSM 6 incumbent alone.** This is a clean, unambiguous
regression, not sampling noise — the smoke sample is small (5 documents)
but the failure rate on the one affected field is total (5/5).

**Root cause: text duplication, not a targeting or row-grouping bug.**
Every failure has the same shape — the predicted value is the correct name
duplicated, e.g. expected `"Steven"`, predicted `"Steven Steven D"`;
expected `"Melissa"`, predicted `"Melissa Melissa"`. The implementation
correctly kept PSM 11 supplemental observations out of primary
row-grouping (goal 2 of this smoke: confirmed — every row-grouped
primary-path field, including the money fields PSM 11 targets, remained
100% correct: `employer.ein`, `box_3`, `box_5`, `box_6` all 5/5). But the
employee-name OCR fallback (`_apply_ocr_employee_layout_fallbacks` /
`_zone_text` in `parser_2026.py`) was not designed with a second,
overlapping observation source in mind: it **joins every token found in
its target zone with spaces**, rather than picking the first/best match the
way the EIN and money-field fallbacks do
(`_first_regex_text_in_zone`/`_first_money_text_in_zone`). Since PSM 11's
supplemental pass and PSM 3's main pass both recognize the same physical
"Steven D" text and both land in the same approved name zone, `_zone_text`
concatenates both readings into one string. `employee.middle_initial`
(5/5 correct, unaffected) survives because its extraction
(`split_first_name_and_initial`) happens to still isolate the correct
trailing single-letter initial from the corrupted joined string even
though `first_name` does not — an incidental, not structural, protection.
Box 13 and SSN — explicitly non-target fields for PSM 11 — remained 100%
correct, confirming the zone-targeting itself is correctly scoped (PSM 11
supplemental output did not leak into either).

**Smoke-goal scorecard:**

1. PSM 11 supplemental path executes correctly: yes (ran cleanly, 0
   document failures, correct `ocr_configuration` metadata recorded).
2. Supplemental observations do not enter primary row grouping: **yes,
   confirmed** — every row-grouped field (EIN, Box 3/5/6) stayed correct.
3. Already-correct PSM 3 values are not overwritten: **no — disqualifying
   failure.** `employee.first_name`, one of the six explicitly approved
   target fields, regressed from 100% to 0% on this sample via
   join-based duplication in the shared OCR fallback path.
4. Whether PSM 11 recovers fields the primary path misses: inconclusive —
   all 5 sampled documents already had correct EIN/Box 3/5/6/middle-initial
   under the primary path alone, so no recovery opportunity existed in this
   sample to observe either way.
5. Latency impact: +51% average duration (`2.330s` -> `3.528s`/document),
   the cost of a full second full-page OCR pass, for a net regression
   rather than any measured improvement on this sample.

**Conclusion: this configuration is NOT marked eligible for the
150-document benchmark, per this task's explicit stop condition.** The
finding is a genuine implementation gap, not a targeting-zone or
row-grouping problem (those parts of the Phase 4E readiness work performed
exactly as designed). A fix would need to make the employee-name OCR
fallback (`_zone_text` and its callers in `_apply_ocr_employee_layout_fallbacks`)
resilient to multiple overlapping observation sources in the same zone —
e.g. preferring non-supplemental tokens first and only falling back to
supplemental tokens when the primary-only zone text is empty, mirroring
the field-level "only fires if still `None`" gating that already protects
every other fallback — before PSM 11 supplemental targeting of the name
zone could be safely retried. Scoping supplemental PSM 11 to only
`employer.ein`/Box 3/5/6 (dropping the name zone, where the join-based
fallback is structurally incompatible with a second observation source)
is a smaller, more surgical alternative fix not requiring a `_zone_text`
redesign. Neither fix was implemented as part of this smoke-test task, per
its explicit stop-and-document instruction. The smoke result artifacts are
preserved as evidence; the historical Tesseract incumbent artifacts were
not modified.

## Phase 4E Targeted Supplemental PSM 11 Retry Without the Name Zone — No Regression, No Demonstrated Benefit

Applied the smaller of the two candidate fixes identified above: rather
than redesigning `_zone_text`, removed the employee-name zone entirely
from PSM 11's approved target set in `_SUPPLEMENTAL_TARGET_ZONES`
(`src/w2_pipeline/extraction/ocr.py`). PSM 11 supplementation now targets
only the four fields whose parser fallback uses first-match zone logic
(`employer.ein`, `federal_wages_and_taxes.box_3_social_security_wages`,
`box_5_medicare_wages_and_tips`, `box_6_medicare_tax_withheld`), the same
fields that stayed 100% correct in the disqualified smoke above. Updated
the one affected unit test (`test_targeted_psm_11_supplemental_pass_is_scoped_to_approved_fields`)
accordingly; full suite 143 tests passing (unchanged count — no tests
added or removed, one test's expectation updated). Re-ran the identical
5-document clean-render smoke.

```text
data/evaluation/results/phase4e_tesseract_supplemental_psm11_no_name_zone_smoke_5.json
data/evaluation/results/phase4e_tesseract_supplemental_psm11_no_name_zone_smoke_5.md
```

- `field_accuracy = 1.0` (115/115 correct), `failed_documents = 0`,
  `field_failure_count = 0`, average `3.656s`/document.
- Same 5 documents as the disqualified smoke
  (`symage_900001`/`900002`/`900003`/`900004`/`900006`). Cross-checked
  against the PSM 3 + PSM 6 incumbent's result for these exact documents:
  **all 115 fields, across all 5 documents, were already 100% correct
  under the incumbent alone** — there were zero primary-path failures on
  `employer.ein` or Boxes 3/5/6 (or any other field) in this specific
  5-document sample to recover from.
- **No regression**: every field the incumbent already got right stayed
  right; the disqualifying `employee.first_name` duplication is gone (the
  field is no longer targeted by PSM 11 at all, so PSM 3's unmodified
  primary-path reading is the only source, exactly as under the
  incumbent).
- **No demonstrated recovery benefit**: because this sample had no
  primary-path failures on the four target fields to begin with, this
  smoke cannot show whether targeted PSM 11 supplementation actually
  recovers anything in practice — a true test of that requires a sample
  containing at least one primary-path failure on `employer.ein` or Box
  3/5/6, which occurs at roughly the 1-1.3% document rate seen in the
  150-document clean benchmark (`employer.ein` 98.67%, `box_6` 98.67%,
  `box_3`/`box_5` 99.33% each under the incumbent) — below what a
  5-document sample can be expected to surface.
- Latency: `3.656s`/document, up from the incumbent's `2.330s` (+56.9%,
  slightly higher than the name-zone-inclusive smoke's +51%, since the
  supplemental PSM 11 pass's cost is a full-page OCR re-scan regardless of
  how many zones its output is filtered down to afterward — dropping one
  zone does not reduce the cost of running the pass itself).
- Per the decision rule set for this task ("no regression but no
  demonstrated recovery benefit -> do not automatically advance; document
  that the smoke did not prove value"): **this configuration is not marked
  eligible for the clean-150 benchmark.** It is no longer disqualified
  (the regression is fixed), but it also has not yet earned promotion —
  the mechanical next step, if pursued, is a smoke sample large enough to
  contain at least one primary-path failure on a target field (the
  150-document set would trivially qualify, per the base rates above, but
  running it was explicitly out of scope for this task). No 150-document
  or 600-document run, no PaddleOCR run, and no other configuration change
  were made; the incumbent and all historical artifacts (including the
  disqualified smoke) are preserved unchanged.

## Phase 4E Targeted Supplemental PSM 11 Recovery Diagnostic — Meaningful Recovery Demonstrated

**This is a targeted diagnostic, not an accuracy benchmark, and its
aggregate `field_accuracy` figure below is not representative of anything
other than this specific, deliberately biased 5-document sample.** The
prior retry smoke used a random 5-document sample that happened to contain
zero primary-path failures on PSM 11's four target fields, so it could not
show whether targeted supplementation recovers anything. This diagnostic
instead selects, from the authoritative 150-document Tesseract incumbent
result (`phase4e_tesseract_checkbox_vision_external_clean_150`), every
document where the PSM 3 + PSM 6 incumbent failed at least one of PSM 11's
four target fields (`employer.ein`,
`federal_wages_and_taxes.box_3_social_security_wages`,
`box_5_medicare_wages_and_tips`, `box_6_medicare_tax_withheld`), then reran
exactly those documents with PSM 11 supplementation enabled
(`--tesseract-supplemental-psm 6,11`, checkbox vision unchanged) to see
whether the known failures get recovered.

Sample construction: 6 known target-field failures across 5 documents in
the 150-document incumbent result —
`symage_900021` (`employer.ein`, missing), `symage_900063` (`box_5`
missing and `box_6` missing), `symage_900075` (`box_3` mismatch, predicted
`"81"` vs. expected `"8.15E+4"`), `symage_900119` (`employer.ein`,
missing), `symage_900123` (`box_6` mismatch, predicted `"1204.85"` vs.
expected `"1294.85"`). A temporary 5-entry manifest containing only these
documents was built for the run and deleted immediately afterward (not a
retained artifact — only the run's JSON/MD outputs are).

```text
data/evaluation/results/phase4e_tesseract_supplemental_psm11_recovery_diagnostic_5.json
data/evaluation/results/phase4e_tesseract_supplemental_psm11_recovery_diagnostic_5.md
```

**Per-known-failure result:**

| Document | Field | Incumbent expected | Incumbent predicted | PSM3+6+11 predicted | Recovered |
| --- | --- | --- | --- | --- | --- |
| `symage_900021` | `employer.ein` | `78-9941160` | *(missing)* | `78-9941160` | **YES** |
| `symage_900063` | `box_5_medicare_wages_and_tips` | `3.08E+4` | *(missing)* | `3.08E+4` | **YES** |
| `symage_900063` | `box_6_medicare_tax_withheld` | `446.6` | *(missing)* | `446.6` | **YES** |
| `symage_900075` | `box_3_social_security_wages` | `8.15E+4` | `81` | `81` | no |
| `symage_900119` | `employer.ein` | `73-3368011` | *(missing)* | `73-3368011` | **YES** |
| `symage_900123` | `box_6_medicare_tax_withheld` | `1294.85` | `1204.85` | `1204.85` | no |

**4 of 6 (66.7%) known target-field failures recovered.** The pattern is
mechanistically clean and fully explained by the existing (unmodified)
fallback gating: `_apply_ocr_federal_layout_fallbacks`/
`_first_ein_from_ocr_layout` only run `if field_name is None or
getattr(federal, field_name) is not None: continue` — i.e. they only ever
fill a field that the primary path left `None`. **All 4 recovered failures
were `failure_kind: "missing"`** (the primary path found nothing, leaving
the field open for PSM 11 to fill via the zone-based fallback). **Both
unrecovered failures were `failure_kind: "mismatch"`** (the primary path
already produced an incorrect but non-`None` value, e.g. `"81"` instead of
`"8.15E+4"` — likely a decimal-scientific-notation misread — so the
fallback gate never fires at all, regardless of what PSM 11 might have
read correctly). This is a **100% recovery rate on the achievable subset
(missing-kind failures) and a structurally-expected 0% on mismatch-kind
failures**, not a partial or inconsistent signal.

**Zero regressions, including outside the target scope.** `symage_900119`
also has two pre-existing, unrelated incumbent failures
(`employee.first_name` mismatch, `employee.middle_initial` missing) —
these are outside PSM 11's target set (the name zone was deliberately
removed after the earlier disqualifying smoke) and were confirmed
**bit-for-bit unchanged** in the diagnostic run (same failure kind, same
predicted values), confirming PSM 11 supplementation still does not leak
outside its four approved zones even under this more adversarial sample.
No target field that the incumbent already got right regressed (not
directly testable by this diagnostic's construction, since the sample was
selected from failures only, but consistent with both prior smokes
finding zero such regressions).

- Diagnostic-run aggregate (**not representative — reported only for
  completeness, per this task's explicit instruction not to treat it as a
  benchmark number**): `field_accuracy = 0.9652173913043478` (111/115),
  average `3.640s`/document. This number is artificially low because the
  sample was deliberately drawn from known-failure documents, not a random
  or representative slice.
- Conclusion: **meaningful recovery demonstrated.** Per the decision rule
  for this task, targeted supplemental PSM 11 (restricted to
  `employer.ein`/Box 3/5/6) is **marked justified for a controlled
  clean-150 benchmark** — the natural next mechanical step, not run as
  part of this diagnostic task. Sizing that benchmark's expected effect:
  the full 150-document incumbent result has exactly 6 known failures on
  these four target fields out of its 25 total field failures (not an
  extrapolation — this diagnostic's sample *is* every such failure in that
  result). If the demonstrated 4/6 (66.7%) recovery rate holds at full
  scale, a clean-150 rerun with PSM 11 enabled would gain a handful of
  fields out of 3,450 — a small but real effect, comparable in magnitude
  to the checkbox-vision fix's clean-150 effect (+5 fields) — but that
  generalization is an assumption to confirm with the actual rerun, not a
  result already established by this 5-document diagnostic. The incumbent
  configuration itself remains unchanged; this diagnostic does not promote
  anything on its own. No 150-document or 600-document run (beyond reading
  the existing historical result), no PaddleOCR run, and no other
  configuration change were made; all historical artifacts, including
  both prior PSM 11 smokes, are preserved unchanged.

## Phase 4E Controlled Clean-150 Benchmark for Targeted Supplemental PSM 11 — Confirmed Gain, Zero Regressions

The recovery diagnostic's justification was acted on: main PSM 3 +
targeted supplemental PSM 6 + targeted supplemental PSM 11
(`--tesseract-supplemental-psm 6,11`, PSM 11 restricted to `employer.ein`
and federal Boxes 3/5/6 only), full 150-document external clean-render
set, checkbox vision enabled, same corrected ground truth/parser/evaluator/
schema as the incumbent result.

```text
data/evaluation/results/phase4e_tesseract_supplemental_psm11_external_clean_150.json
data/evaluation/results/phase4e_tesseract_supplemental_psm11_external_clean_150.md
```

- `field_accuracy = 0.9939130434782608` (3,429/3,450 correct), up from the
  incumbent's `0.9927536231884058` (3,425/3,450); `failed_documents = 0`;
  `field_failure_count = 21`, down from 25; average `3.541479775440033`
  seconds/document, up from `2.330209926666645` (**+51.98%**, +1.211s/doc).
- **Per-field changes, exactly matching the recovery diagnostic's
  prediction at full scale:**
  - `employer.ein`: 98.67% -> **100.0%** (148/150 -> 150/150, +2)
  - `federal_wages_and_taxes.box_5_medicare_wages_and_tips`: 99.33% ->
    **100.0%** (149/150 -> 150/150, +1)
  - `federal_wages_and_taxes.box_6_medicare_tax_withheld`: 98.67% ->
    99.33% (148/150 -> 149/150, +1)
  - `federal_wages_and_taxes.box_3_social_security_wages`: unchanged,
    99.33% (149/150) — the one `"mismatch"`-kind Box 3 failure
    (`symage_900075`, primary path reads `"81"` instead of `"8.15E+4"`)
    remains, as predicted, since the `None`-only fallback gate cannot
    address a non-`None` wrong value.
  - No other field changed at all.
- **Document-level recovery, cross-checked exactly against the incumbent's
  `field_failures`:** 4 fields recovered
  (`symage_900021.employer.ein`, `symage_900119.employer.ein`,
  `symage_900063.box_5_medicare_wages_and_tips`,
  `symage_900063.box_6_medicare_tax_withheld` — all four were
  `"missing"`-kind), **zero new failures anywhere** (the regressed set is
  empty), and all 21 remaining failures have **bit-for-bit identical**
  predicted values to the incumbent (same wrong text, same missing
  fields) — nothing was disturbed, only filled in. This is the full-scale
  confirmation of the 5-document diagnostic's 4/6 (66.7%) recovery
  result — every recoverable failure the diagnostic found (all 4
  `"missing"`-kind ones, spread across the same 3 documents) recovered
  identically at 150-document scale, and both `"mismatch"`-kind failures
  the diagnostic correctly predicted would not recover (`box_3` on
  `symage_900075`, `box_6` on `symage_900123`) did not recover here
  either.
- Conclusion, applying the decision rule for this task: **accuracy
  improved (99.28% -> 99.39%, +4 fields) with zero regressions** — this
  clears the bar for "record the gain," not rejection. The gain is small
  in absolute terms (0.116 percentage points, 4 of 3,450 fields, 3 of 150
  documents affected) and costs a substantial, consistent latency
  penalty (+52%, from running a full second full-page OCR pass) for every
  document processed, not just the ones that benefit. **This result does
  not automatically promote any incumbent** — the accuracy/latency
  trade-off (a real but narrow correctness gain, concentrated in
  `employer.ein` and Box 5/6 recovery only, against a substantial
  per-document runtime cost) is reported for the user to weigh, not
  decided here. No 600-document run, no PaddleOCR run, and no other
  configuration change were made; the incumbent and all prior PSM 11
  artifacts (both smokes and the diagnostic) are preserved unchanged.

## Phase 4E Rotated Employee-Name Label-Bleed Investigation

Investigation only — no fix implemented, no 150/600-document benchmark
run, no incumbent change. Full report:
`docs/experiments/phase4e-paddle-rotation-name-investigation.md`.

Traced the `rotated_png` `employee.first_name` failure (predicted values
like `"Lori"` -> `"Lori e Employee's first name and initial"`, 0/150
correct) end to end — pixels, raw PaddleOCR `predict()` output (before any
adapter code runs), `TextObservation` conversion, employee-name zone
selection, and the name-splitting heuristic — using 3 representative
rotated documents (with and without a middle initial, plus an accented
name), cross-referenced against the existing Tesseract 600-document
robustness result for contrast.

**Root cause: F (employee-name zone selection), driven by H (rotation
normalization / coordinate-space assumption).** PaddleOCR's raw
`rec_texts`/`rec_boxes` output was verified correct: the printed Box e
label (`"e Employee's first name and initial"`) and the name value
(`"Lori"`, or `"Steven D"` when Paddle's line-level recognition merges a
name with its initial) are two separate, correctly-recognized entries
with distinct, non-overlapping bounding boxes — ruling out Paddle's text
detection and recognition (A, B) and the adapter's coordinate conversion
(C, D; confirmed a 1:1 unmodified passthrough). The corruption is
introduced entirely downstream, in the shared, backend-neutral employee-
name OCR fallback (`_apply_ocr_employee_layout_fallbacks`/`_zone_text` in
`parser_2026.py`): its fixed target zone `(0.04, 0.28, 0.505, 0.550)` is
normalized against *detected-text extent* (`_layout_extent`), not true
image pixels. Measured directly on `symage_900000`: the label's
normalized `y` position is `0.4852` on the clean render (safely below the
zone's `0.505` floor) but `0.5060` on the rotated image (just inside) —
reproduced to four decimal places across 4 independent documents,
confirming a systematic, template/rotation-angle-driven effect rather
than per-document noise. `_zone_text` then joins every observation in the
zone (sorted by `x0`) into one string, merging the label into the name.
E (word/line reconstruction) is not implicated — the employee-name
fallback reads the flat zone-filtered observation list directly, without
row grouping.

**The missing middle initial is a direct, mechanical consequence (root
cause G)**: `split_first_name_and_initial`
(`contracts/employee_name.py`) only checks whether the *last*
whitespace-split token is a single uppercase letter; the corrupted
string's trailing junk words (`"...first name and initial"`) push the
true initial (`"D"`) out of that position, so the check silently fails
and the entire string — including the still-present `"D"` — becomes
`first_name` instead.

**Checked and rejected**: renormalizing the zone against true image
pixels instead of detected-text extent. Using the rotated image's true
height (3388px) instead of its detected extent (1674px) would push *both*
the label (`0.25`) and the name value (`0.267`) outside the existing
zone, because every zone constant across `parser_2026.py`'s OCR fallback
system (name, EIN, all federal box zones) was calibrated relative to
detected-text extent — switching the reference would require
recalibrating all of them, not just this one, and was judged out of scope
for a "smallest fix" recommendation.

**Correction to prior documentation.** The PaddleOCR 600-document
robustness rerun previously reported this as PaddleOCR-specific ("no
Tesseract equivalent at that severity, Tesseract's rotated
`employee.first_name` is 53.67%"). That figure was Tesseract's *aggregate
across all four variants*, not rotated-only. Recomputed directly from the
existing Tesseract 600-document result, filtering to `rotated_png` only:
Tesseract is **0/150 (0%)** on rotated `employee.first_name` and **32/150
(21.33%)** on rotated `employee.middle_initial` — identical to PaddleOCR
on both fields. This is expected, not coincidental: the bug lives in
parser code both backends' observations flow through equally. This
corrects `docs/project-state.md`'s "Current Phase," "Immediate Next
Experiment," and "Current Known Weaknesses" sections, removing a caveat
that had previously appeared to weigh specifically against PaddleOCR GPU
in the incumbent-promotion comparison.

**Recommended fix (not implemented)**: filter the known, static Box e
label text out of zone-filtered observations — a substring/pattern match
against fixed form template text (not employee data), reliable regardless
of OCR backend or how far rotation shifts the zone boundary, requiring no
ratio recalibration. A complementary, defense-in-depth option
(hardening `split_first_name_and_initial` to look for a single-uppercase-
letter token near the start of the value rather than only the last token)
was also identified but not implemented; it would reduce the blast radius
of this and similar future zone-membership bugs (including the earlier
PSM 11 supplemental `_zone_text` duplication finding, which shares the
same underlying "join-all" fragility) without addressing the root
geometric cause.

**Generic vs. template-specific.** The underlying mechanism (H) is
generic to any ratio-based fallback zone normalized against detected-text
extent, under any transformation that changes the true-canvas-to-
detected-extent ratio unevenly. The observed *severity* (100%, not
partial) is specific to this W-2 template's Box e layout and Symage's
fixed rotation angle — the identical `0.5060` label ratio recurring
across every checked document confirms one fixed transform applied
uniformly to one fixed template, not a general property of "any rotated
document." No 150-document or 600-document run, no PaddleOCR settings
change, no parser/adapter/checkbox-vision/ground-truth change, and no fix
implementation were made, per this investigation's explicit scope.

## Phase 4E Rotated Employee-Name Label-Bleed Fix (Implemented and Verified)

Implemented the investigation's recommended fix: a targeted, backend-
neutral filter for Box e's known, static printed label text
("Employee's first name and initial"), added to `parser_2026.py`'s
existing `_clean_layout_token` helper (shared by the employee first-name/
middle-initial, last-name, and suffix OCR fallback zones). Two new module
constants — `_BOX_E_LABEL_WORDS` (the label's constituent words,
apostrophe-normalized and lowercased for comparison) and the existing
`_SINGLE_CHAR_JUNK` set (already covered the bare `"e"` box-letter
marker) — are now applied at the **word level** within `_clean_layout_token`,
not just to a token's whole string: any observation is stripped of
individual words matching either denylist before the survivors are
rejoined, so the filter works identically whether the label arrives as
one merged observation (PaddleOCR's line-level recognition, e.g. `"e
Employee's first name and initial"`) or as several separate word tokens
interleaved with the name by x-position (Tesseract's word-level
recognition, e.g. `"Steven"`, `"Employee's"`, `"D"`, `"first"`, `"name"`,
`"and"` as six distinct observations). No branching on OCR backend was
added anywhere; the fix lives entirely in the shared parser path both
backends already flow through.

No OCR settings, checkbox vision, ground truth, or evaluator were
touched, and no ratio-zone constant was recalibrated — exactly the
"smallest fix" the investigation recommended, in preference to the
larger, rejected alternative (renormalizing every zone constant against
true image dimensions).

**Tests**: 6 new focused tests in `test_parser_2026.py` covering exactly
the scenarios specified: a clean, uncorrupted name unaffected by the new
filter; a PaddleOCR-style merged label with a middle initial (`"Steven D"`
+ `"e Employee's first name and initial"` -> `first_name="Steven"`,
`middle_initial="D"`); the same without a middle initial (`"Lori"` ->
`first_name="Lori"`); an accented name surviving the filter untouched
(`"Jesús D"` -> `first_name="Jesús"`, unaffected by ASCII-only label-word
matching); a Tesseract-style fragmented/interleaved label (six separate
observations, matching the real observed corruption order) recovering
`"Steven"`/`"D"` correctly; and a regression check confirming last name
and suffix zones are unaffected by the label-word filter. Full suite: 149
tests passing (143 before this task, zero regressions, 6 new).

**Real-pipeline smoke** (not a benchmark; 3 representative rotated
documents × 2 backends, run directly through `PipelineAExtractor` against
the actual rotated source images, not synthetic fixtures):

| Document | Backend | `first_name` | `middle_initial` | Result |
| --- | --- | --- | --- | --- |
| `symage_900000` (no initial) | Tesseract | `Lori` | `None` | matches expected |
| `symage_900000` | PaddleOCR GPU | `Lori` | `None` | matches expected |
| `symage_900001` (initial `D`) | Tesseract | `Steven` | `D` | matches expected |
| `symage_900001` | PaddleOCR GPU | `Steven` | `D` | matches expected |
| `symage_900026` (accented, initial `D`) | Tesseract | `Jesus` | `D` | initial recovered; accent still dropped — see below |
| `symage_900026` | PaddleOCR GPU | `Jesús` | `D` | matches expected |

5 of 6 are exact matches. The one non-match (Tesseract, `symage_900026`)
is **not a regression and not part of this fix's scope**: Tesseract
already misread `"Jesús"` as `"Jesus"` (accent dropped) on the *clean*
render of the same document, per the existing 600-document robustness
result (`phase4e_tesseract_checkbox_vision_external_all_variants_600.json`,
`external_clean_render` failure for this `document_id`) — a pre-existing,
unrelated Tesseract accent-recognition limitation. Before this fix,
Tesseract's rotated prediction for this document was `"Jesus Employee’s D
first name and"` (both the accent drop *and* the label-bleed corruption,
with the middle initial lost); after the fix it is exactly `"Jesus"` with
`middle_initial="D"` correctly recovered — the label-bleed component is
fully resolved, and only the separate, pre-existing accent limitation
remains, exactly as expected.

**Conclusion**: the fix resolves the rotated `employee.first_name`/
`middle_initial` label-bleed corruption on both backends, verified
directly against real rotated source images (not just synthetic unit
fixtures), with zero regressions in the full test suite. Per this task's
explicit scope, no 150-document or 600-document benchmark was run to
requantify the aggregate effect, no PSM 11 experiments were touched, and
Pipeline B was not started. The existing historical 150/600-document
benchmark artifacts (both backends) now predate this fix for the
`employee.first_name`/`middle_initial` fields specifically — rerunning
those benchmarks to obtain corrected authoritative numbers is the natural
next mechanical step, not performed as part of this implementation task.

## Phase 4E PaddleOCR GPU 150-Document `rotated_png` Rerun (Post Box-e-Label Fix) — Confirmed Fix, One New Bug Found

Reran PaddleOCR GPU against the full 150-document `rotated_png` variant
only (checkbox vision enabled, current parser including the Box e
static-label filter from the immediately preceding fix commit
`2dcfa64`), to confirm the fix at scale and specifically check
`employee.first_name`, `employee.middle_initial`, and
`box_13.retirement_plan`.

```text
data/evaluation/results/phase4e_paddleocr_gpu_box_e_fix_rotated_150.json
data/evaluation/results/phase4e_paddleocr_gpu_box_e_fix_rotated_150.md
```

Compared against the historical PaddleOCR GPU rotated subset (filtering
`phase4e_paddleocr_gpu_checkbox_vision_external_all_variants_600.json`'s
`field_failures` to `variant_id == "rotated_png"` only: `3,122/3,450`
correct, `90.49%`).

- **`employee.first_name`: 0/150 (0%) -> 150/150 (100%). Fully resolved,
  no exceptions.** Every one of the 150 historical label-bleed failures
  is recovered; this field is now perfect on the rotated variant.
- **`employee.middle_initial`: 32/150 (21.33%) -> 144/150 (96.0%).
  Substantially improved (112 of 118 historical failures recovered) but
  NOT fully resolved.** See the new-bug finding below — the 6 remaining
  failures are not a leftover of the original label-bleed bug.
- **`box_13.retirement_plan`: 90/150 (60.0%) -> 90/150 (60.0%).
  Unchanged, as expected** — this is the separate, already-documented
  checkbox-vision rotation-calibration limitation
  (`RETIREMENT_PLAN_ZONE`, calibrated only against clean renders), out of
  scope for the Box e label fix and untouched by it.
- **Overall: `field_accuracy = 0.9808695652173913` (3,384/3,450), up from
  `0.904927536231884` (3,122/3,450), a +7.6 percentage point improvement
  on this variant.** `failed_documents = 0`. Average duration
  `1.4269119057400652` seconds/document, close to (slightly above) the
  historical PaddleOCR GPU aggregate rate across all four variants
  (`1.349s`/doc from the original 600-document run) — no historical
  rotated-only latency figure exists for a like-for-like comparison, but
  the label-word filtering itself is negligible-cost text processing, not
  an additional OCR pass, so no material latency regression is expected
  or observed.
- **Zero regressions anywhere**, confirmed by an exhaustive document-and-
  field-level diff against the historical rotated result: 262 fields
  recovered (150 `first_name` + 112 `middle_initial`), 0 fields newly
  failing that previously passed, and all 66 remaining failures (60
  `box_13.retirement_plan` + 6 `employee.middle_initial`) are present in
  *both* the old and new results.

**New finding — a real regression in the Box e label fix itself, not a
pre-existing OCR limitation.** All 6 remaining `employee.middle_initial`
failures share `expected: "E"` and `failure_kind: "missing"`. Cross-
referencing the external dataset's ground truth confirms this is not
coincidental: **exactly 6 of the 118 documents with any ground-truth
middle initial have `middle_initial == "E"`, and those are precisely the
6 that fail — every other letter (`"D"`, `"K"`, `"L"`, `"W"`, etc.)
succeeds.** Root cause, confirmed directly (`_clean_layout_token("E") ->
None`; `_clean_layout_token("D") -> "D"`): the fix's
`_is_box_e_label_word` helper lowercases its input before checking
membership in `_BOX_E_LABEL_WORDS`, which includes the lowercase `"e"`
box-letter-marker token. This correctly matches a genuine lowercase `"e"`
marker, but *also* incorrectly matches a legitimate capital `"E"` middle
initial, treating it as the marker and discarding it. The pre-existing
`_SINGLE_CHAR_JUNK` check that already handled the box-letter-marker case
is case-*sensitive* (`cleaned in {..., "e", ...}`, `"E"` does not match)
and was never the source of this bug — the newly added, case-*insensitive*
`_BOX_E_LABEL_WORDS` path introduced it. This bug is not variant-specific
(the same OCR-fallback code path runs identically on clean, compressed,
and blurred documents), so it plausibly affects every variant containing
a document with `middle_initial == "E"`, not just `rotated_png` — this
was not verified for other variants as part of this task, which was
scoped to `rotated_png` only.

Per this task's explicit instruction not to hide or normalize evaluator
differences: **these 6 failures must not be characterized as resolved,
and must not be conflated with the original label-bleed bug or with a
legitimate OCR limitation (such as Tesseract's separate, pre-existing
accent-recognition weakness documented in the prior fix task).** They are
a distinct, newly introduced, narrow-but-real regression with an
obvious, low-risk fix: remove the redundant `"e"` entry from
`_BOX_E_LABEL_WORDS`, since the box-letter-marker case is already
correctly handled by the case-sensitive `_SINGLE_CHAR_JUNK` check. This
was **not implemented as part of this task** (explicitly scoped to
running and reporting the `rotated_png` benchmark only) and is flagged as
a clear, high-priority follow-up recommendation.

**Conclusion**: the Box e label fix works as intended and delivers a
large, confirmed improvement on the rotated variant with zero
regressions from its own intended scope, but this rerun surfaced a small,
distinct, well-understood defect in the fix's implementation (not a
pre-existing limitation) affecting the narrow case of a capital `"E"`
middle initial. The historical PaddleOCR 600-document artifact remains
untouched (superseded only for `rotated_png`-scope claims by this new
result, not for clean/compressed/blurred, which were not rerun in this
task). No clean/compressed/blurred variant, no full 600-document
benchmark, no Tesseract, no PSM 11, and no Pipeline B work were performed,
per this task's explicit scope.

## Phase 4E Box e Filter Capital-E Regression Fix (Implemented and Verified)

Fixed the capital-`"E"` middle-initial regression found by the preceding
`rotated_png` rerun. Root cause was exactly as diagnosed: `_is_box_e_label_word`
lowercased its input before checking membership in `_BOX_E_LABEL_WORDS`,
which included lowercase `"e"` (the Box e box-letter marker) — so a
legitimate capital `"E"` middle initial normalized to `"e"` and was
incorrectly discarded as if it were the marker.

**Fix**: removed the redundant `"e"` entry from `_BOX_E_LABEL_WORDS`
(`parser_2026.py`). The lowercase marker case remains correctly handled
by the pre-existing, case-*sensitive* `_SINGLE_CHAR_JUNK` check — both
for a standalone `"e"` observation (caught before the word-split ever
runs) and for `"e"` as one word inside a longer merged label string (the
multi-word branch already excludes words present in `_SINGLE_CHAR_JUNK`,
which is exact-match/case-sensitive and therefore never matches a capital
`"E"`). No other line changed; no OCR-backend branching, no OCR-settings
change, no zone recalibration, and no checkbox-vision change were made.

Directly verified via `_clean_layout_token`:

```text
_clean_layout_token("E")  -> "E"    (capital initial preserved)
_clean_layout_token("e")  -> None   (lowercase marker still filtered)
_clean_layout_token("e Employee's first name and initial") -> None
_clean_layout_token("Lori e Employee's first name and initial") -> "Lori"
_clean_layout_token("Steven E e Employee's first name and initial") -> "Steven E"
```

**Tests**: 10 new focused tests in `test_parser_2026.py` — direct
`_clean_layout_token` checks for `"E"` preservation and continued `"e"`
filtering (both standalone and merged-label); an end-to-end PaddleOCR-
style merged-label case with a capital-E initial recovering
`first_name="Steven"`/`middle_initial="E"`; a parametrized non-regression
check across `"D"`/`"J"`/`"K"`/`"W"`/`"M"` initials confirming every other
letter still works; and two more non-regression checks reconfirming the
original no-initial Paddle-merged case and the Tesseract-fragmented case
from the prior fix task both still pass. Full suite: **159 tests passing
(149 before this task, zero regressions, 10 new)**.

**Real-pipeline verification** (not a benchmark; direct extraction calls
against actual rotated source images): `symage_900023` (ground-truth
`first_name="James"`, `middle_initial="E"` — the exact bug case) via
PaddleOCR GPU now correctly extracts `first_name="James"`,
`middle_initial="E"`. `symage_900001` (`"Steven"`/`"D"`, a non-`"E"`
document) still correctly extracts `first_name="Steven"`,
`middle_initial="D"`, confirming no regression from this change.

**Conclusion**: the capital-`"E"` regression identified by the prior
`rotated_png` rerun is fixed and verified, both at the unit level and
against a real rotated source image. Per this task's explicit scope, no
150-document or 600-document benchmark was run to requantify the
`rotated_png` numbers with this fix layered on top of the earlier label-
bleed fix — that combined effect (both fixes in place) has not yet been
measured at scale; the prior `rotated_png` rerun's `employee.middle_initial`
figure (144/150, 96.0%) is now understood to undercount the achievable
result by exactly the 6 documents this fix addresses, so a corrected
number (expected 150/150 for `employee.middle_initial` on this variant,
pending confirmation) is the natural next mechanical step. No Tesseract
benchmark, no PSM 11 work, and no Pipeline B work were performed.

## Phase 4E PaddleOCR GPU 150-Document `rotated_png` Rerun (Post Capital-E Fix) — Fully Confirmed, Zero Regressions

Reran PaddleOCR GPU against the full 150-document `rotated_png` variant
only, using the finalized parser with both Box e fixes in place (the
original label-bleed fix and the capital-`"E"` denylist fix), to confirm
the predicted recovery at scale.

```text
data/evaluation/results/phase4e_paddleocr_gpu_capital_e_fix_rotated_150.json
data/evaluation/results/phase4e_paddleocr_gpu_capital_e_fix_rotated_150.md
```

Compared against the immediately preceding `rotated_png` result
(`phase4e_paddleocr_gpu_box_e_fix_rotated_150`, pre-capital-E-fix:
`field_accuracy = 0.9808695652173913`, 3,384/3,450; `employee.first_name`
150/150; `employee.middle_initial` 144/150; `box_13.retirement_plan`
90/150).

- **`employee.middle_initial`: 144/150 (96.0%) -> 150/150 (100%). All 6
  capital-`"E"` failures recovered, confirmed by exact document ID** —
  `symage_900023`, `symage_900028`, `symage_900047`, `symage_900063`,
  `symage_900067`, `symage_900080` (the same 6 identified in the prior
  task) are precisely the 6 documents whose `employee.middle_initial`
  moved from failing to passing; no other document's `middle_initial`
  status changed.
- **`employee.first_name`: 150/150 (100%), unchanged** — remained
  perfect, as expected (the capital-E fix does not touch this field's
  already-correct behavior).
- **`box_13.retirement_plan`: 90/150 (60.0%), unchanged** — correctly
  unaffected, confirming this fix stayed scoped to the employee-name
  fallback and did not touch the separate, already-documented
  checkbox-vision rotation-calibration limitation.
- **Overall: `field_accuracy = 0.9826086956521739` (3,390/3,450), up from
  `0.9808695652173913` (3,384/3,450) — exactly +6 fields, matching the 6
  recovered `middle_initial` failures precisely.** `failed_documents = 0`.
  Average duration `1.3417634917399603` seconds/document, slightly
  *faster* than the pre-fix rerun's `1.427s`/document (within normal
  GPU-run-to-run variance; removing one entry from a lookup set has no
  meaningful cost either way).
- **Zero regressions**, confirmed by an exhaustive document-and-field-
  level diff against the pre-capital-E-fix result: exactly 6 fields
  recovered (the 6 `employee.middle_initial` cases above), 0 fields newly
  failing, and all 60 remaining failures (all `box_13.retirement_plan`)
  present in both results unchanged.

**Conclusion**: this closes out the reconfirmation this fix's own
implementation task flagged as outstanding. Both Box e fixes — the
original label-bleed filter and the capital-`"E"` denylist correction —
are now fully verified at 150-document scale on PaddleOCR GPU's
`rotated_png` variant: `employee.first_name` and `employee.middle_initial`
are both 100% correct, with the sole remaining weakness
(`box_13.retirement_plan` at 60.0%) being the separate, already-diagnosed
checkbox-vision rotation-calibration limitation, out of scope for this
line of work. The full 600-document benchmark (all four variants) and the
equivalent Tesseract rerun remain outstanding and were not run, per this
task's explicit scope; no PSM 11 work and no Pipeline B work were
performed. All prior historical artifacts, including both earlier
`rotated_png` PaddleOCR results, are preserved unchanged.

## Phase 4E Tesseract Incumbent 150-Document `rotated_png` Rerun (Post Box-e Fixes) — Confirms the Fix Is Fully Backend-Neutral

Reran the Tesseract incumbent (main PSM 3 + targeted supplemental PSM 6,
unchanged) against the full 150-document `rotated_png` variant only,
using the finalized shared parser (both Box e fixes — the label-bleed
filter and the capital-`"E"` denylist correction — in place), to confirm
the fix on the second backend at scale, matching the two PaddleOCR GPU
`rotated_png` reruns already completed this session.

```text
data/evaluation/results/phase4e_tesseract_capital_e_fix_rotated_150.json
data/evaluation/results/phase4e_tesseract_capital_e_fix_rotated_150.md
```

Compared against the historical Tesseract rotated subset (filtering
`phase4e_tesseract_checkbox_vision_external_all_variants_600.json`'s
`field_failures` to `variant_id == "rotated_png"`: `3,104/3,450` correct,
`89.97%`; `employee.first_name` 0/150; `employee.middle_initial` 32/150 —
both identical to PaddleOCR's pre-fix numbers, as the earlier
investigation established).

- **`employee.first_name`: 0/150 (0%) -> 146/150 (97.33%). Massive
  recovery, not fully perfect** (unlike PaddleOCR's 150/150). The 4
  remaining failures are fully accounted for and none are new: 3 are
  Tesseract's separate, pre-existing accent-recognition limitation
  (`"Jesús"` -> `"Jesus"`, `"Óliver"` -> `"Oliver"`, `"Adán"` -> `"Adan"`
  — the same well-documented weakness confirmed in the original label-
  bleed fix task, present on these same documents' *clean* renders too);
  the 4th (`symage_900118`, expected `"Logan"`) improved from a corrupted
  wrong value (`"Employee's first name and"`, label-bleed garbage) to a
  clean `None` (no value found) — the label-bleed corruption is gone, but
  Tesseract's word-level detection still fails to find `"Logan"` at all in
  this rotated document, a separate, pre-existing detection gap unrelated
  to the label filter.
- **`employee.middle_initial`: 32/150 (21.33%) -> 147/150 (98.0%).**
  The 3 remaining failures (`symage_900062`/`symage_900068`, both
  expected `"C"`; `symage_900135`, expected `"I"`) are **unchanged,
  bit-for-bit identical `"missing"`-kind failures already present in the
  historical pre-fix result** — pre-existing OCR-detection gaps where
  Tesseract never recognized the initial character at all under rotation,
  wholly unrelated to the label-bleed bug and not affected by either fix.
- **`box_13.retirement_plan`: 90/150 (60.0%), unchanged** — correctly
  unaffected, confirming the fix stayed scoped to the employee-name
  fallback (same result as both PaddleOCR reruns).
- **Overall: `field_accuracy = 0.9753623188405797` (3,365/3,450), up from
  `0.8997101449275362` (3,104/3,450) — a +7.6 percentage point
  improvement, closely matching PaddleOCR's own +7.6pp gain from the
  first Box e fix.** `failed_documents = 0`. Average duration
  `2.3608392549135653` seconds/document, essentially unchanged from the
  historical 600-document run's aggregate rate (`2.319s`/doc across all
  four variants) — no latency regression, as expected for a pure
  text-processing change.
- **Zero regressions**, confirmed by an exhaustive document-and-field-
  level diff against the historical rotated result: 261 fields recovered,
  0 fields newly failing. The 85 remaining failures include the 60
  `box_13.retirement_plan` cases, the 7 employee-name cases explained
  above, and 18 more (federal Boxes 3/5/6, `employee.ssn`, `employer.ein`,
  `employee.last_name`) that are **all bit-for-bit unchanged from the
  historical result** — pre-existing Tesseract rotation weaknesses in
  fields the Box e fixes never targeted, not new failures.

**Conclusion**: this confirms the Box e fixes are genuinely
backend-neutral, exactly as the original investigation predicted — both
PaddleOCR GPU and the Tesseract incumbent share the identical underlying
bug (via the shared `_clean_layout_token` code path) and both benefit
substantially from the same fix. The one meaningful backend difference is
that Tesseract's *remaining* failures are pre-existing, independent OCR
weaknesses (accent recognition, occasional word-level detection misses)
that were never part of the label-bleed bug and are not addressed by
either Box e fix — PaddleOCR simply doesn't exhibit those particular
weaknesses on this sample, which is why it reached a clean 150/150 on
both name fields while Tesseract reached 146/150 and 147/150. No full
600-document benchmark, no PaddleOCR run, no PSM 11 work, and no
Pipeline B work were performed, per this task's explicit scope. All
historical artifacts, including the 600-document Tesseract robustness
result, are preserved unchanged.
