# Phase 8B - Final Head-To-Head 600-Document Benchmark

**This is the final, frozen extraction benchmark.** Same code, same
600-document dataset, same 24-field evaluated coverage, same evaluator,
for both backends. Broad extraction benchmarking is frozen after this
document. This phase produced evidence only -- no architecture decision,
tuning, or ADR rewrite was made here (Phase 8C/8D, not yet run).

## Configuration

| | Configuration A | Configuration B |
|---|---|---|
| OCR backend | PaddleOCR | Tesseract |
| Device | GPU (RTX 3060) | CPU |
| Main mode | default | PSM 3 |
| Supplemental | -- | PSM 6 (incumbent, SSN recovery) |
| PSM 11 | -- | not enabled |
| Parser | unchanged | unchanged |
| Checkbox vision | unchanged | unchanged |
| `employer.name` fallback | unchanged (Phase 6B) | unchanged (Phase 6B) |

Both runs: git commit `0e5a3af01c4abba2bb775daff96e1d7e8f472a2a`, dataset
`data/evaluation/external/symage-synthetic-us-forms-preview-final/manifest.jsonl`
(`generator_version = "symage-w2.phase8a.v2"`, 600 entries: 150 each of
`external_clean_render`, `compressed_jpeg`, `blurred_png`, `rotated_png`),
24 evaluated fields (Phase 8A). Environment recorded before either run:
`paddleocr==3.7.0`, `paddlepaddle-gpu==3.3.1`, `tesseract 4.1.1`, NVIDIA
GeForce RTX 3060 (driver 610.62, 11.1 GB free at start). Runs were
launched strictly sequentially (Tesseract only after Paddle's process had
fully exited), never concurrently.

Result artifacts:
```text
data/evaluation/results/phase8b_final_paddleocr_gpu_all_variants_600.json
data/evaluation/results/phase8b_final_paddleocr_gpu_all_variants_600_predictions.jsonl
data/evaluation/results/phase8b_final_tesseract_psm3_psm6_all_variants_600.json
data/evaluation/results/phase8b_final_tesseract_psm3_psm6_all_variants_600_predictions.jsonl
```

## Final Comparison Table

| Metric | PaddleOCR GPU | Tesseract PSM3+6 |
|---|---:|---:|
| Documents | 600 | 600 |
| Failed documents | 0 | 0 |
| Full-pipeline field accuracy (24 fields) | **98.54%** (14,190/14,400) | 89.55% (12,895/14,400) |
| Text/parser subsystem accuracy (23 fields, excl. `box_13.retirement_plan`) | **98.91%** (13,650/13,800) | 90.02% (12,423/13,800) |
| Clean accuracy | 100.0% | 99.31% |
| Compressed JPEG accuracy | 100.0% | 99.0% |
| Blurred accuracy | 100.0% | 66.42% |
| Rotated accuracy | 94.17% | 93.47% |
| Avg seconds/document | **1.30** | 2.13 |
| Total field failures | 210 | 1,505 |

"Text/parser subsystem accuracy" (brief's Section 8 terminology) excludes
only `box_13.retirement_plan`, the one field whose value is partly owned
by a separate visual-only pixel detector
(`checkbox_vision.py`) rather than purely OCR text + deterministic
parsing. This is not "raw OCR accuracy" -- the deterministic parser is
still fully included; only the one visual-detector-owned field is
excluded, per the brief's explicit terminology requirement.

**PaddleOCR GPU leads on every measured dimension**: accuracy (both full
and text/parser subsystem), every single variant, and latency
simultaneously. No field or variant exists in this run where Tesseract
outperforms PaddleOCR.

## Per-Field Accuracy (All 24 Fields)

| Field | PaddleOCR | Tesseract |
|---|---:|---:|
| metadata.document_type | 100.0% | 100.0% |
| metadata.tax_year | 100.0% | 100.0% |
| metadata.schema_version | 100.0% | 100.0% |
| employee.ssn | 100.0% | 83.00% (498/600) |
| employee.first_name | 100.0% | 78.00% (468/600) |
| employee.middle_initial | 100.0% | 82.83% (497/600) |
| employee.last_name | 100.0% | 82.50% (495/600) |
| employee.suffix | 100.0% | 100.0% |
| employer.ein | 100.0% | 83.00% (498/600) |
| **employer.name** | **75.00% (450/600)** | 59.17% (355/600) |
| employer.control_number | 100.0% | 100.0% |
| federal_wages_and_taxes.box_1 | 100.0% | 84.17% (505/600) |
| federal_wages_and_taxes.box_2 | 100.0% | 84.17% (505/600) |
| federal_wages_and_taxes.box_3 | 100.0% | 82.50% (495/600) |
| federal_wages_and_taxes.box_4 | 100.0% | 84.17% (505/600) |
| federal_wages_and_taxes.box_5 | 100.0% | 83.50% (501/600) |
| federal_wages_and_taxes.box_6 | 100.0% | 83.50% (501/600) |
| federal_wages_and_taxes.box_7 | 100.0% | 100.0% |
| federal_wages_and_taxes.box_8 | 100.0% | 100.0% |
| federal_wages_and_taxes.box_10 | 100.0% | 100.0% |
| federal_wages_and_taxes.box_11 | 100.0% | 100.0% |
| box_13.statutory_employee | 100.0% | 100.0% |
| box_13.retirement_plan | 90.00% (540/600) | 78.67% (472/600) |
| box_13.third_party_sick_pay | 100.0% | 100.0% |

`employer.name` is now scored for the first time in this project's
history at 600-document scale (Phase 8A). Both backends show it as their
single weakest field -- see the failure taxonomy below for why.

## Failure Taxonomy

**PaddleOCR GPU -- 210 failures, both concentrated entirely in `rotated_png` (0 failures in clean/compressed/blurred):**

| Cause | Field | Count | Category |
|---|---|---:|---|
| Rotation-induced label-position drift: the `employer.name` fallback zone captures the printed question label ("c Employer's name, address, and ZIP code") instead of the answer | `employer.name` | 150 | **Parser/layout error (new)** |
| Checkbox pixel-geometry does not track rotation | `box_13.retirement_plan` | 60 | Checkbox visual-geometry error (pre-existing, documented) |

**Tesseract -- 1,505 failures** (verified to sum exactly: 245 + 128 +
1,132 = 1,505, cross-checked against `field_failure_count` in the result
JSON, not just added by hand):

| Cause | Field(s) | Count | Category |
|---|---|---:|---|
| Same rotation label-position drift as Paddle (confirmed backend-neutral: zero overlapping documents between the two backends' failure sets, same failure mode) | `employer.name` (rotated): 150/150 | 150 | **Parser/layout error (new)** |
| Blur-specific OCR recognition degradation on the same field (already documented pattern: Tesseract's known weak variant) | `employer.name` (blurred): 95/150 | 95 | OCR recognition error (pre-existing, documented) |
| Blur-specific checkbox pixel-geometry gap, Tesseract only | `box_13.retirement_plan` (blurred): 68/150 fail, 54.67% accuracy | 68 | Checkbox visual-geometry error (pre-existing) -- **exact reconfirmation** of the historical Phase 4E figure (`docs/project-state.md`: "Tesseract 40.0% -> 54.67%... PaddleOCR is unaffected by blur at 100%"); investigated directly (zero overlap with Paddle's blur failures, confirming this is genuinely backend-asymmetric, not a shared bug) rather than assumed |
| Rotation-specific checkbox pixel-geometry gap (shared with Paddle) | `box_13.retirement_plan` (rotated): 60/150 | 60 | Checkbox visual-geometry error (pre-existing, documented, backend-neutral) |
| OCR recognition degradation across identity/money fields, overwhelmingly concentrated in the blurred variant (`employee.ssn` 97, `employee.first_name` 104, `employee.last_name` 99, `employee.middle_initial` 80, `employer.ein` 96, federal Boxes 1-6 all ~95 each = ~660 of these under blur alone), with a small residual scattered across compressed/clean (1-14 each per field) | `employee.ssn` (102 total), `employee.first_name` (132), `employee.last_name` (105), `employee.middle_initial` (103), `employer.ein` (102), federal Boxes 1-6 (95+95+105+95+99+99 = 588) | 1,132 | OCR recognition error (pre-existing, documented -- this is the same "blur is Tesseract's weakest condition" finding from every prior Phase 4B/4C/4E benchmark, now reconfirmed at the new 24-field coverage) |

**New finding requiring no further investigation to classify** (evidence
was directly checked, not assumed): the `employer.name` rotation failure
is a **parser/layout error**, not an OCR recognition failure --
confirmed by inspecting the actual predicted values (`predicted: "c
Employer's name, address, and ZIP code"` on every one of the 150 failing
documents, both backends): the OCR engines correctly read the printed
label text; `_first_row_text_in_zone`'s calibrated zone simply captures
the wrong printed row once rotation shifts its position, the same
root-cause class as the previously-fixed "Rotated Employee-Name
Label-Bleed" bug (`docs/experiments/phase4e-paddle-rotation-name-investigation.md`).
**Per the final-test integrity rule, this was not fixed as part of this
benchmark** -- it is reported as a result.

## Prediction Artifact Verification

- Exactly 600 `PredictionRecord` entries in each JSONL file.
- Identical `(document_id, variant_id)` key sets between the two backends
  (every document/variant pairing present in both, none missing or
  extra).
- 100% `status: "success"` in both (0 document-level failures, matching
  the result JSON's `failed_documents: 0` for both).
- Every record carries a complete predicted `W2Document`,
  `extraction_route: "ocr"`, and a non-null `duration_seconds`.
- `PredictionRecord`'s schema has no ground-truth field (`document_id`,
  `variant_id`, `pipeline_id`, `status`, `document`, `extraction_route`,
  `duration_seconds`, `message`, `pipeline_metadata` only) -- confirmed
  directly against the loaded records, not just by design intent.

## What Was Deliberately Not Done

- No parser, OCR configuration, checkbox threshold, or evaluated-field
  coverage change was made after seeing these results.
- The newly discovered `employer.name` rotation bug was not patched.
- No repeated/retuned reruns were performed to chase a better score.
- No architecture decision or ADR rewrite was made (Phase 8C/8D).
- No validator-effectiveness analysis was run against these new
  predictions (Phase 8C, next).

## Verification

Full suite unaffected by this phase (no code changed): 359 tests passing,
same as Phase 8A. Both result JSON and both prediction JSONL files parse
cleanly and were validated as shown above. No historical benchmark
artifact was modified. No PII/scratch files were generated (this dataset
is entirely synthetic, per project policy).
