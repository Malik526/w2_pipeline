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
