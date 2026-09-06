# Phase 8C.2 - Final PaddleOCR 600-Document Production-Candidate Run

**This is the final production-candidate extraction benchmark for the
selected backend (PaddleOCR GPU), run against the current
post-remediation code.** Same dataset, same 24-field evaluated coverage,
same evaluator as Phase 8B. No OCR setting, parser logic, checkbox logic,
or field coverage was changed before or during this run; the frozen
Phase 8B artifacts were not overwritten.

## Configuration

Identical to Phase 8B's PaddleOCR configuration:

| | Configuration |
|---|---|
| OCR backend | PaddleOCR |
| Device | GPU (RTX 3060) |
| Mode | default |
| Parser | Phase 8C.1 rotation fixes applied (unchanged since) |
| Checkbox vision | unchanged |
| `employer.name` fallback | Phase 8C.1 fixed (rotation label-bleed + lone box-letter-row bleed) |

Git commit `467f327792db2794a6c6eb83e6d5d26a4427d9c2` (Phase 8C.1
complete), dataset
`data/evaluation/external/symage-synthetic-us-forms-preview-final/manifest.jsonl`
(`generator_version = "symage-w2.phase8a.v2"`, 600 entries: 150 each of
`external_clean_render`, `compressed_jpeg`, `blurred_png`, `rotated_png`),
24 evaluated fields (Phase 8A, unchanged). Environment: `paddleocr==3.7.0`,
`paddlepaddle-gpu==3.3.1`, NVIDIA GeForce RTX 3060 (driver 610.62).

Result artifacts:
```text
data/evaluation/results/phase8c2_final_paddleocr_gpu_all_variants_600.json
data/evaluation/results/phase8c2_final_paddleocr_gpu_all_variants_600.md
data/evaluation/results/phase8c2_final_paddleocr_gpu_all_variants_600_predictions.jsonl
```

## Headline Result: Freeze Rule Satisfied

| Metric | Phase 8B (pre-remediation) | Phase 8C.2 (post-remediation) |
|---|---:|---:|
| Documents | 600 | 600 |
| Failed documents | 0 | 0 |
| Full-pipeline field accuracy (24 fields) | 98.54% (14,190/14,400) | **99.56% (14,336/14,400)** |
| Text/parser subsystem accuracy (23 fields, excl. `box_13.retirement_plan`) | 98.91% (13,650/13,800) | **99.97% (13,796/13,800)** |
| Clean accuracy | 100.0% | 100.0% |
| Compressed JPEG accuracy | 100.0% | 100.0% |
| Blurred accuracy | 100.0% | 100.0% |
| Rotated accuracy | 94.17% | **98.22%** |
| Avg seconds/document | 1.30 | 1.23 |
| Total field failures | 210 | **64** |

Every measured dimension improved or held steady; no dimension
regressed. All 210 -> 64 field-failure reduction is attributable
entirely to `employer.name` (see below) -- `box_13.retirement_plan` is
byte-for-byte unchanged from Phase 8B (540/600 correct both times),
confirming the checkbox-geometry issue was correctly left untouched.

## `employer.name`: Before And After Remediation

| | Phase 8B | Phase 8C.2 |
|---|---:|---:|
| Overall accuracy | 75.00% (450/600) | **99.33% (596/600)** |
| Rotated-variant accuracy | 0.0% (0/150) | **97.33% (146/150)** |
| Clean/compressed/blurred accuracy | 100.0% (450/450) | 100.0% (450/450) |

**The prior 150/150 label-capture failure is confirmed gone.** Zero
documents predict the printed Box c label text
(`"c Employer's name, address, and ZIP code"`) or a bare box-letter
marker (`"c"`) in this run -- both were the exact failure modes Phase
8C.1 fixed.

**All 4 remaining `employer.name` misses are the already-understood
row-merge residual**, exactly the same 4 documents identified during
Phase 8C.1's 150-document verification run (not a new finding):

| Document | Expected | Predicted |
|---|---|---|
| symage_900033 | `Elan Consulting Corp` | `Elan Consulting Corp 2861 Geneva Ponce De Leon Rd` |
| symage_900045 | `Bespoke Designs LLC` | `Bespoke Designs LLC 6878 Normandy Tullahoma Rd` |
| symage_900082 | `FutureReady Services` | `FutureReady Services 875 Francis Case Memorial Brg` |
| symage_900146 | `Global Insights Corp` | `Global Insights Corp 4522 Eastern Transportation Corridor` |

Identical document set and identical predicted values to Phase 8C.1's
diagnosis (see
`docs/experiments/phase8c1-employer-name-rotation-remediation.md`'s
"Residual" section): under especially large rotation skew, the answer
row and the immediately following street-address line's own drifted
words merge into one row in `_group_observation_rows`. Confirmed
pre-existing and already categorized, not a new defect -- no further
investigation needed.

## `box_13.retirement_plan`: Unaffected, As Required

540/600 correct (90.00%) in both Phase 8B and this run -- exactly the
same 60 failing documents (spot-checked: all 60 `rotated_png`, all
`expected: false, predicted: true`), confirming zero change to checkbox
detection logic. This is the pre-existing, already-documented
rotation-checkbox-geometry gap; per the brief, it was explicitly not
touched in Phase 8C.1 or this run.

## Full Per-Field Accuracy (24 Fields)

All 24 fields are 100.0% (600/600) except the two below -- every
identity, wage, and metadata field is perfect across all four variants:

| Field | Accuracy |
|---|---:|
| **employer.name** | **99.33% (596/600)** |
| box_13.retirement_plan | 90.00% (540/600) |
| (all other 22 fields) | 100.0% (600/600) each |

## Complete Failure Taxonomy

**64 total field failures, both fields, both entirely confined to
`rotated_png` (0 failures in clean/compressed/blurred):**

| Cause | Field | Count | Category |
|---|---|---:|---|
| Checkbox pixel-geometry does not track rotation (pre-existing, unchanged from Phase 8B) | `box_13.retirement_plan` | 60 | Checkbox visual-geometry error (pre-existing, documented, untouched) |
| Row-merge residual: answer row merges with part/all of the following address line under large rotation skew (pre-existing, diagnosed in Phase 8C.1, not fixed by design) | `employer.name` | 4 | Parser/layout error (known, reported, out of Phase 8C.1's scope) |

**No new systematic parser/layout failure appears.** Every failure in
this run maps exactly onto a category already known and documented
before this run started; nothing here required new investigation.

## Prediction Artifact Verification

- Exactly 600 `PredictionRecord` entries in the JSONL file.
- 100% `status: "success"` (0 document-level failures, matching the
  result JSON's `failed_documents: 0`).
- 600 unique `(document_id, variant_id)` keys -- one per manifest entry,
  none missing or duplicated.
- Every record carries a complete predicted `W2Document`,
  `extraction_route: "ocr"`, and a non-null `duration_seconds`.
- `PredictionRecord`'s schema has no ground-truth field, confirmed
  directly against the loaded records (`document_id`, `variant_id`,
  `pipeline_id`, `status`, `document`, `extraction_route`,
  `duration_seconds`, `message`, `pipeline_metadata` only).

## Freeze Decision: FROZEN

All freeze-rule conditions are satisfied:

- Clean/JPEG/blur remain effectively perfect (100.0% each, unchanged
  from Phase 8B). ✓
- Rotated `employer.name` remediation behaves exactly as expected: the
  reported 150/150 bug is gone, and the small residual is the
  already-diagnosed row-merge case, not a new failure mode. ✓
- Remaining failures are limited to already-understood residual layout
  cases (`employer.name` row-merge, 4 documents) and the separate,
  pre-existing checkbox-geometry issue (`box_13.retirement_plan`, 60
  documents, byte-for-byte unchanged from Phase 8B). ✓
- No new systematic defect appears anywhere in the 24-field, 600-document
  scan. ✓

**This is declared the final production-candidate extraction benchmark.
Extraction is frozen as of this run** (git commit recorded at run time:
`467f327792db2794a6c6eb83e6d5d26a4427d9c2`; this document's own commit is
the one immediately following). No further extraction tuning is
performed as a result of these numbers, per the brief's instruction: "Do
not fix anything automatically after this run."

## What Was Deliberately Not Done

- No OCR setting, parser logic, checkbox logic, or evaluated-field
  coverage was changed before, during, or after this run.
- The frozen Phase 8B benchmark artifacts
  (`phase8b_final_*_600.json/.md/_predictions.jsonl`) were not modified,
  regenerated, or replaced.
- The `employer.name` row-merge residual (4/600) and the
  `box_13.retirement_plan` rotation-geometry gap (60/600) were not
  patched, despite being fully diagnosed -- both are pre-existing,
  already-documented, and explicitly out of scope for this run.
- No repeated/retuned reruns were performed to chase a better score.

## Verification

Full suite unaffected by this phase (no source code changed, only new
result/report artifacts and documentation): 372 tests passing, same as
after Phase 8C.1. The result JSON and prediction JSONL parse cleanly and
were validated as shown above. No historical benchmark artifact was
modified. No PII/scratch files were generated (this dataset is entirely
synthetic, per project policy).
