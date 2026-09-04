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
