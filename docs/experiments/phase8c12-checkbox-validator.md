# Phase 8C.12 - Checkbox-Specific Validation for `box_13.retirement_plan`

Adds a dedicated validator for the Phase 8C.11 promoted anchor-relative
retirement-plan checkbox detector, consuming the structured
`Box13CheckboxEvidence` that phase preserved. This phase does not change
checkbox extraction, PaddleOCR configuration, the anchor-relative
detector or its calibrated `0.12` threshold, employer-name logic, or
canonical schema semantics; it adds one new deterministic rule set to
the existing Phase 6 validator.

## 1. Core Principle

A boolean is structurally valid even when wrong -- exactly why the
pre-8C.12 validator silently accepted all 60 `box_13.retirement_plan`
failures in the frozen Phase 8C.2 benchmark. This validator asks "was
this checkbox prediction produced with trustworthy visual evidence?"
instead of "is `retirement_plan` a valid bool?", and is symmetric:
`True` and `False` are judged identically, purely on evidence quality.

## 2. Evidence Wiring

Mirrors the Phase 8C.8 employer-name-signal pattern exactly:

```
ObservationSet.box_13_checkbox_evidence   (Phase 8C.11, per-document)
    -> ExtractionResult.box_13_checkbox_evidence   (new, this phase)
    -> PredictionRecord.pipeline_metadata["box_13_checkbox_evidence"]
       (new instrumented-run script, this phase)
    -> ExtractionSignals.checkbox_evidence_*   (new, this phase; nine
       primitive fields, not the extraction-side pydantic type)
    -> validation/rules.py's new rule
```

`ExtractionSignals` (and every other `w2_pipeline.validation` module)
deliberately never imports `w2_pipeline.extraction`
(`tests/validation/test_isolation.py` enforces this with AST-based
import inspection, unchanged and still passing) -- so
`Box13CheckboxEvidence`'s nine fields are duplicated onto
`ExtractionSignals` as plain `str`/`bool`/`float` fields
(`checkbox_evidence_detection_method`, `checkbox_evidence_fallback_used`,
`checkbox_evidence_anchor_found`, `checkbox_evidence_checkbox_found`,
`checkbox_evidence_anchor_distance_px`,
`checkbox_evidence_horizontal_alignment_offset_px`,
`checkbox_evidence_shape_score`, `checkbox_evidence_interior_ink_ratio`,
`checkbox_evidence_decision_margin`), the same reasoning that already
kept `employer_name_observation_count` a plain `int` rather than a
richer type.

The rule function never re-opens the source image, re-runs OCR, or
re-runs checkbox localization/classification -- it only reads
already-computed `ExtractionSignals` fields.

## 3. Issue Codes

All `error` severity (any error routes to `needs_review` under the
existing default `RoutingPolicy`); all fire independently of one
another (never suppressed by another already-fired issue), matching the
employer-name signal precedent.

| Code | Fires when |
|---|---|
| `retirement_plan_checkbox_evidence_missing` | No checkbox evidence at all, on an `ocr`/`mixed` route |
| `retirement_plan_checkbox_fallback_used` | `detection_method != "anchor_relative"` (covers both `fixed_zone_fallback` and the diagnostic `fixed_zone_disabled`) |
| `retirement_plan_checkbox_anchor_missing` | `anchor_found is False` |
| `retirement_plan_checkbox_not_found` | `checkbox_found is False` |
| `retirement_plan_checkbox_low_decision_margin` | `abs(decision_margin) < 0.05` |
| `retirement_plan_checkbox_geometry_anomaly` | `shape_score < 0.5` |

### Missing-evidence route scoping

`retirement_plan_checkbox_evidence_missing` only applies to
Pipeline A's `ocr`/`mixed` routes -- the ones Phase 8C.10/8C.11
instrument. Two routes are exempt by a **positive allow-list**, not a
default-deny fallback:

- **`native_pdf`**: `box_13.retirement_plan` comes from embedded-text-prefix
  reconstruction (`acquisition.py`'s `PdfTextMode.EMBEDDED_TEXT` branch),
  which never touches `checkbox_anchor.py` or `checkbox_vision.py` at
  all. "No evidence" there is a different mechanism, not a gap.
- **Pipeline B (`route="vlm"`)**: a different, generative pipeline
  (`extraction/pipeline_b/models.py` sets `route: str = "vlm"` as its
  own real default) that this evidence was never built for.
  `validate_w2_document` is explicitly backend-neutral by construction
  (see its module docstring); this rule must not penalize a pipeline
  the signal doesn't apply to.

An unset/unrecognized route is exempt the same way as `native_pdf`/`vlm`
-- only routes positively identified as in-scope are held to this
requirement. This was necessary to keep
`test_validate_w2_document_backend_neutral_for_pipeline_a_and_b_signals`
passing (Pipeline A's `route="ocr"` signals in that test were given
trusted checkbox evidence explicitly, matching what a real Phase 8C.11
caller would supply; Pipeline B's `route="vlm"` needed no change).

## 4. Offline Evidence Analysis

New script: `src/w2_pipeline/evaluation/run_checkbox_evidence_analysis.py`,
consuming `phase8c10_anchor_checkbox_rows.jsonl` directly (Phase 8C.10's
per-document evidence for all 600 documents). This is valid input for the
*promoted* detector, not stale data: `checkbox_anchor.py` is byte-for-byte
unmodified between Phase 8C.10 and 8C.11 (no retuning), and Phase 8C.11's
own production-path benchmark independently reproduced the identical
600/600 localization and 0/600 fallback result -- re-running the detector
would recompute values already known to be identical (deterministic, no
randomness), not surface new information.

Artifact: `data/evaluation/results/phase8c12_checkbox_evidence_analysis_600.json`.

### Decision-margin distribution

| Class | n | min | max | mean |
|---|---:|---:|---:|---:|
| Unchecked | 240 | -0.120 | -0.120 | -0.120 |
| Checked | 360 | +0.124 | +0.178 | +0.148 |

Unchecked's margin is a **hard constant**, not a distribution near the
boundary: every unchecked document has `interior_ink_ratio` exactly
`0.0` (no ink at all found), so `decision_margin = 0.0 - 0.12 = -0.12`
always. Checked never comes closer than `+0.124`. There is a clean,
unbroken **0.244-wide gap** with nothing observed inside it in either
direction -- this benchmark offers zero real near-boundary examples.

**Chosen margin: `0.05`.** Less than half the smallest real separation
observed in either direction (`0.12` unchecked, `0.124` checked
minimum), so it provably cannot fire on any of this benchmark's 600 real
documents (verified: 0/600 flagged at 0.05, and even at 0.10 or 0.119,
still 0/600 -- see the artifact's `near_threshold_margin_analysis`),
while remaining wide enough to catch a genuinely ambiguous real-world
interior ink ratio (roughly 0.07-0.17) this synthetic dataset cannot
produce. This is a conservative, principled buffer, not a value fit to
the benchmark's own perfect separation -- the brief's explicit warning
against exactly that.

### Shape-score / geometry distribution

| Signal | Observed range (all 600) |
|---|---|
| `shape_score` | 0.827 - 0.880 |
| `anchor_distance_px` | -2.0 - 0.0 |
| `horizontal_alignment_offset_px` | 0.0 - 3.0 |

Tight and stable, but resolution/DPI-specific to this one synthetic
renderer. `rotated_png` shows the weakest (but still far from
implausible) geometry: mean `shape_score` 0.833 vs. 0.867 for the other
three variants, and the largest `alignment_offset_px` (2-3px vs. 0-1.5px
elsewhere) -- consistent with rotation-induced OCR line-box noise, not a
localization failure.

**Implemented**: `shape_score < 0.5` (a broad structural floor -- aspect
ratio at least 2:1 -- deliberately far below this benchmark's own
0.827-0.880 range so it reflects genuine implausibility, not this one
renderer's specific geometry).

**Deliberately not implemented**: numeric thresholds on
`anchor_distance_px`/`horizontal_alignment_offset_px`. Both are raw
pixel offsets, not normalized by the anchor's own line height (which
validation does not receive), and specific to one fixed 2550x3300
synthetic-render DPI -- there is insufficient resolution variation in
this dataset to justify a production threshold for either that would
generalize to a differently-scanned real document. Both remain
preserved on `ExtractionSignals` for a future phase.

### Per-variant summary

| Variant | n | Incorrect | Mean `shape_score` | Mean `abs(decision_margin)` |
|---|---:|---:|---:|---:|
| `external_clean_render` | 150 | 0 | 0.860 | 0.134 |
| `rotated_png` | 150 | 0 | 0.833 | 0.122 |
| `compressed_jpeg` | 150 | 0 | 0.860 | 0.136 |
| `blurred_png` | 150 | 0 | 0.880 | 0.155 |

## 5. Synthetic Uncertainty Tests

The 600-document benchmark has zero real checkbox failures, so the
validator's negative path is exercised with constructed evidence at the
`ExtractionSignals` level (never by injecting ground truth into a
benchmark run). `tests/validation/test_rules.py` (Phase 8C.12 section, 19
new tests):

- Strong checked / strong unchecked evidence -> no checkbox issue
  (symmetric).
- No route / `vlm` / `native_pdf` with no evidence -> not flagged
  (positive allow-list).
- `ocr`/`mixed` route with no evidence at all -> `..._evidence_missing`.
- `fixed_zone_fallback` and `fixed_zone_disabled` -> both
  `..._fallback_used`.
- `anchor_found=False` / `checkbox_found=False` -> independent issues,
  both preserved together when both apply.
- Strong positive/negative margin -> passes; near-zero positive/negative
  margin -> `..._low_decision_margin`; deterministic boundary test just
  inside/at/outside `_NEAR_THRESHOLD_DECISION_MARGIN`.
- Malformed `shape_score` (0.2) -> `..._geometry_anomaly`; normal
  `shape_score` -> not flagged.
- A checkbox issue never suppresses employer-name issues, and vice
  versa (combined-routing style test, matching the Phase 8C.8
  precedent).
- `True`/`False` checkbox values produce identical issue sets under
  identical evidence -- no class prior.

## 6. Production-Path 600-Document Validator Effectiveness

New script:
`src/w2_pipeline/evaluation/run_pipeline_a_with_checkbox_evidence_signals.py`
(modeled directly on Phase 8C.8's
`run_pipeline_a_with_employer_name_signals.py`). Fresh instrumented run
of the real, unmodified `PipelineAExtractor` -- no checkbox-related
keyword argument passed anywhere, relying entirely on Phase 8C.11's
default-True promotion (`extractor.observation_acquirer.enable_anchor_relative_checkbox
is True` asserted directly) -- producing one `PredictionRecord` per
document with `pipeline_metadata` carrying both
`employer_name_observation_count` and `box_13_checkbox_evidence`.

**Stability check**: every field except `box_13.retirement_plan`
verified byte-identical to the frozen Phase 8C.2 prediction for all
600/600 documents (`documents_matching_frozen_phase8c2_excluding_retirement_plan:
600`, zero mismatches) before anything was scored. Artifacts:
`phase8c12_checkbox_signals_600_predictions.jsonl`,
`phase8c12_checkbox_signals_stability_600.json`.

`w2_pipeline.evaluation.validator_effectiveness_predictions` (extended
this phase to also thread `box_13_checkbox_evidence` from
`pipeline_metadata`, the same way it already threaded
`employer_name_observation_count`) was then run unchanged against this
predictions file:

| | Value |
|---|---:|
| Total documents | 600 |
| Correct documents | 596 |
| Erroneous documents | 4 |
| Accepted | 596 |
| Needs review | 4 |
| Correct accepted | 596 |
| Correct routed to review | 0 |
| Erroneous accepted | 0 |
| Erroneous routed to review | 4 |
| Error detection recall | 1.0 |
| False review rate | 0.0 |
| Automatic acceptance rate | 0.9933 |
| **Unsafe acceptance rate** | **0.0** |
| Review-queue precision | 1.0 |

Artifacts:
`data/evaluation/results/phase8c12_checkbox_validator_effectiveness_600.json`,
`data/evaluation/results/phase8c12_checkbox_validator_rows.jsonl`.

Matches the expected result from the brief exactly (measured, not
forced): the checkbox validator fired on **0 of 600 documents** (the
`validator_issue_taxonomy` contains only `employer_name_address_leak`
and `employer_name_layout_anomaly`, each on the same 4 documents, no
`retirement_plan_checkbox_*` code anywhere) -- because every one of the
600 promoted checkbox extractions is `anchor_relative`, 0 fallback, and
carries strong, non-ambiguous evidence, there is nothing for this
validator to catch or falsely flag on this benchmark. It adds zero
review volume and zero missed catches here; its value is the safety net
for evidence this dataset does not exercise (see Section 4).

## 7. Checkbox-Specific Behavior Summary

- Strong checked accepted: **yes** (596/596 correct-checkbox documents
  accepted, 0 checkbox issues).
- Strong unchecked accepted: **yes** (same evidence quality, same
  outcome -- symmetric by construction and by the dedicated unit tests).
- Fallback reviewed: **yes**, by construction and by dedicated unit
  tests (`fixed_zone_fallback`/`fixed_zone_disabled` both ->
  `retirement_plan_checkbox_fallback_used`); 0/600 fallback occurred on
  this benchmark, so this path is unexercised by the real 600-document
  data and is proven only by the synthetic tests.
- Missing evidence reviewed: **yes** on `ocr`/`mixed` (unit-tested);
  never triggered on the real benchmark, since every document had
  evidence.
- Synthetic near-threshold cases reviewed: **yes**, by the dedicated
  margin-boundary tests (Section 5); no real document in this benchmark
  is near the threshold to exercise this path naturally.

## 8. Employer-Name Regression Check

Identical to Phase 8C.8/8C.11: the same 4 `employer.name` failures
(`symage_900033/900045/900082/900146`, all `rotated_png`), still caught
100% by `employer_name_address_leak` + `employer_name_layout_anomaly`
together on all 4, 0% false-review rate, 0 unsafe acceptance from the
employer-name signals. No interaction with the new checkbox rules on
this benchmark (`overlap_between_classes.count: 0` -- no document fails
both `employer.name` and `box_13.retirement_plan`).

## 9. Source-Route Audit

| Route | Produces `Box13CheckboxEvidence`? | Detector | Validator behavior |
|---|---|---|---|
| Plain image (`AcquisitionRoute.OCR`, non-PDF input) | Yes, always (unless the default override disables it) | Anchor-relative by default; fixed-zone on fallback/override | Evidence-based: trusted evidence passes, weak/missing evidence (route in scope) reviews |
| Image-only PDF (`AcquisitionRoute.OCR`, PDF input) | **No** -- `acquisition.py`'s `_acquire_pdf` `IMAGE_ONLY` branch never populates `ObservationSet.box_13_checkbox_evidence` (Phase 8C.10/8C.11 only instrumented the plain-image path) | Fixed-zone only (`checkbox_vision.py`), unchanged since before Phase 8C.10 | Route reports `"ocr"` -- indistinguishable from plain-image at the `route` field alone, so a document on this route with no evidence is (correctly, conservatively) flagged `retirement_plan_checkbox_evidence_missing` |
| Mixed PDF (`AcquisitionRoute.MIXED`) | **No**, same reason as image-only PDF | Fixed-zone only for the OCR-routed pages | Same as image-only PDF: flagged `retirement_plan_checkbox_evidence_missing` if no evidence supplied |
| Native PDF (`AcquisitionRoute.NATIVE_PDF`) | No -- mechanically never runs any image-based checkbox detector | Text-prefix reconstruction from embedded PDF text only | Exempt by design (Section 3) -- a different, non-OCR mechanism, not a gap |
| Pipeline B (`route="vlm"`) | No -- out of scope entirely | N/A (generative) | Exempt by design (Section 3) -- backend-neutral validator must not penalize a pipeline this signal was never built for |

**This phase's own 600-document benchmark is 100% plain-image OCR
route** (the Symage dataset has no PDF documents), so the image-only/
mixed-PDF gap noted above is a real, documented architectural
observation, not something this benchmark's numbers could have
exercised either way. No extraction scope was widened to close this gap
-- per the brief, this phase is validator/safety-only. A caller on an
image-only/mixed PDF route today gets the same untrusted-by-default
routing an `ocr`-route document with a genuine fallback would get,
which is the conservative, safe default the brief asked for.

## 10. Performance

Measured directly (`w2_pipeline.validation.rules._check_retirement_plan_checkbox_evidence`
called standalone, and `validate_w2_document` end-to-end, both against
all 600 real Phase 8C.2 documents with synthetic trusted-evidence
signals):

| | Total (600 docs) | Mean/doc |
|---|---:|---:|
| Checkbox-validator rule only | 0.39 ms | 0.6 microseconds |
| Full validator (13 rules, incl. checkbox) | 17.4 ms | 29.0 microseconds |

Pure structured-data comparisons (`is False`, `abs(x) < y`, string
equality) -- no image processing, no OCR, no re-computation of anything
extraction already produced. The checkbox rule adds roughly 2-3% to the
already-microsecond-level Phase 6 validator total, consistent with the
"microseconds-level, incremental" expectation and with the Phase 8C.8
employer-name signals' own measured overhead.

## 11. Tests

19 new tests in `tests/validation/test_rules.py` (Section 5 above), plus
fixture updates required by the new default-restrictive rule (not
regressions -- deliberate contract tightening, same as the brief
intended):

- `tests/validation/test_validator.py`: the backend-neutrality test's
  `route="ocr"` Pipeline A signals now include trusted checkbox evidence
  (a real Phase 8C.11 caller would supply this); Pipeline B's `route="vlm"`
  needed no change (exempt route).
- `tests/validation/test_rules.py` /
  `tests/validation/test_integration_fixtures.py`: `ALL_RULE_NAMES`
  count bumped 12 -> 13.
- `tests/evaluation/test_validator_effectiveness_predictions.py`: the
  end-to-end counting test's three `extraction_route="ocr"`
  `PredictionRecord`s now carry trusted checkbox evidence in
  `pipeline_metadata`, since that test is about detectable/undetectable
  *non-checkbox* errors, not checkbox evidence.

`tests/validation/test_isolation.py` (validator imports no
`w2_pipeline.extraction`/`evaluation`/`ingestion`) is unchanged and still
passing -- confirms this phase introduced no forbidden dependency.

Full suite: **534 tests passing**, up from 515, **zero unintended
regressions** (every fixture change above reflects the new rule's
intended, documented behavior, not an accidental break).

## 12. Decision

**A. Strong safety layer.** Zero unsafe acceptance across the full
600-document benchmark (both before and after this phase -- the
employer-name signals already achieved this; the checkbox validator
adds a safety net without disturbing it), zero false review, negligible
(microsecond-level) latency. The checkbox rules fired on 0/600 documents
here because Phase 8C.11's promoted detector already produces
uniformly strong evidence on this dataset -- this phase's value is not
demonstrated by catching anything on this particular benchmark, but by
the synthetic-evidence tests proving the rules correctly reject
fallback, missing-localization, and near-threshold evidence when it
occurs. Not forced into this category: the measured 0/600 checkbox-issue
rate is the real, honest result of a detector that already tested
600/600 correct before this phase started.

## Artifacts

- `src/w2_pipeline/extraction/models.py` (`ExtractionResult.box_13_checkbox_evidence`)
- `src/w2_pipeline/extraction/pipeline_a.py` (wiring)
- `src/w2_pipeline/validation/models.py` (`ExtractionSignals.checkbox_evidence_*`)
- `src/w2_pipeline/validation/rules.py` (new rule, issue codes, thresholds)
- `src/w2_pipeline/evaluation/validator_effectiveness_predictions.py` (threading)
- `src/w2_pipeline/evaluation/run_checkbox_evidence_analysis.py`
- `src/w2_pipeline/evaluation/run_pipeline_a_with_checkbox_evidence_signals.py`
- `tests/validation/test_rules.py`, `test_validator.py`,
  `test_integration_fixtures.py`
- `tests/evaluation/test_validator_effectiveness_predictions.py`
- `data/evaluation/results/phase8c12_checkbox_evidence_analysis_600.json`
- `data/evaluation/results/phase8c12_checkbox_signals_600_predictions.jsonl`
- `data/evaluation/results/phase8c12_checkbox_signals_stability_600.json`
- `data/evaluation/results/phase8c12_checkbox_validator_effectiveness_600.json`
- `data/evaluation/results/phase8c12_checkbox_validator_rows.jsonl`
- `docs/contracts/validation-and-routing.md` (Checkbox Evidence Rules section)
