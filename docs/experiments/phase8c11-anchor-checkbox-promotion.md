# Phase 8C.11 - Promote Anchor-Relative `box_13.retirement_plan` Checkbox Detector to Default

Promotes the Phase 8C.10 OCR-anchor-relative `box_13.retirement_plan`
checkbox detector from an explicit opt-in
(`enable_anchor_relative_checkbox=False` by default) to
`ObservationAcquirer`'s normal production default. This is a promotion +
regression-verification phase only: no PaddleOCR configuration change, no
non-checkbox parser change, no employer-name change, no deskew, no
retuning of the anchor-relative detector or its calibrated
`DEFAULT_INTERIOR_INK_THRESHOLD = 0.12`, no new validator rules.

## 1. What Changed

`ObservationAcquirer.__init__`'s `enable_anchor_relative_checkbox`
default flipped from `False` to `True`
(`src/w2_pipeline/extraction/acquisition.py`). No other constructor
behavior changed, and the detector module
(`extraction/checkbox_anchor.py`) is untouched byte-for-byte from Phase
8C.10.

Because every production caller already constructs `ObservationAcquirer`
without passing this flag --
`PipelineAExtractor.__init__`'s `ObservationAcquirer()` default and
`run_pipeline_a.py`'s `_pipeline_a_extractor` -- both now use the
anchor-relative detector automatically. No caller code changed. This was
verified directly: a 20-document smoke run through the unmodified
`run_pipeline_a.py` CLI (`--ocr-backend paddleocr --paddle-device gpu`)
reached 20/20 on `box_13.retirement_plan` with zero code changes to the
CLI or `PipelineAExtractor`.

The Phase 8C.10 evaluation scripts that already explicitly passed
`enable_anchor_relative_checkbox=True`
(`run_pipeline_a_with_anchor_checkbox.py`) or never used the flag at all
(`run_anchor_checkbox_analysis.py`, which calls `detect_retirement_plan`
directly) are unaffected and were left untouched, along with their
existing Phase 8C.10 artifacts.

## 2. Structured Evidence Preserved for Phase 8C.12

`ObservationSet` gained a new field, `box_13_checkbox_evidence:
Box13CheckboxEvidence | None`
(`src/w2_pipeline/extraction/models.py`), populated for every OCR-routed
plain-image acquisition. It carries each Phase 8C.10 evidence signal as
a **discrete field**, not collapsed into one confidence score:

- `detection_method`: `"anchor_relative"`, `"fixed_zone_fallback"`, or
  `"fixed_zone_disabled"`.
- `fallback_used`: `True` only for `"fixed_zone_fallback"` -- a
  diagnostic disable is not a fallback, since nothing failed.
- `anchor_found`, `checkbox_found`
- `anchor_distance_px`, `horizontal_alignment_offset_px`, `shape_score`
- `interior_ink_ratio`, `decision_margin`

This is in addition to (not a replacement for) the existing
human-readable `ObservationSet.warnings` entries ("anchor-relative
detection used" / "... fell back to fixed-zone detector"), which are
unchanged. Both are populated from the same underlying
`RetirementPlanDetection` Phase 8C.10 already produced -- no new
detection logic, only a new place to carry its output structurally so
Phase 8C.12's checkbox validator can consume it without re-deriving
evidence from scratch or string-parsing warnings.

## 3. Fallback Behavior (Preserved, Unmodified)

Fallback logic in `_detect_box_13_visual_marks_for_image` is unchanged
from Phase 8C.10: if the anchor-relative detector raises, or cannot
localize the anchor or the checkbox candidate, `ObservationAcquirer`
falls back explicitly to the original fixed-zone
`detect_box_13_retirement_plan_mark`, recording which detector actually
produced the result. Passing `enable_anchor_relative_checkbox=False`
remains a supported diagnostic/backward-comparison override that
reproduces the pre-8C.11 fixed-zone-only behavior; it is not expected to
be used by production callers going forward.

## 4. Production-Path 600-Document Benchmark

New script:
`src/w2_pipeline/evaluation/run_pipeline_a_promoted_checkbox_benchmark.py`.
Unlike Phase 8C.10's A/B runner (which explicitly passed
`enable_anchor_relative_checkbox=True` to prove the detector itself
works), this script constructs `ObservationAcquirer` **exactly the way
ordinary production callers do** -- no checkbox-related keyword argument
at all -- specifically to prove the *default* constructor now produces
the anchor-relative detector's behavior, not just the special-cased A/B
runner. Same PaddleOCR GPU backend and manifest as the frozen Phase 8C.2
baseline and the Phase 8C.10 experiment.

| Variant | n | `retirement_plan` correct |
|---|---:|---:|
| `external_clean_render` | 150 | 150/150 |
| `rotated_png` | 150 | 150/150 |
| `compressed_jpeg` | 150 | 150/150 |
| `blurred_png` | 150 | 150/150 |
| **Total** | **600** | **600/600 (100%)** |

- **Total field accuracy: 14396/14400 = 99.972%** -- identical to the
  Phase 8C.10 experimental result.
- **`non_checkbox_field_mismatches_vs_frozen_phase8c2`: empty (0 of
  600)** -- every non-checkbox field remains bit-identical to the frozen
  Phase 8C.2 prediction.
- **Remaining 4 failures are `employer.name` on `rotated_png`**, and are
  the *exact same four document IDs* as Phase 8C.2's frozen residual:
  `symage_900033`, `symage_900045`, `symage_900082`, `symage_900146`
  (all `rotated_png`) -- verified by direct set comparison against
  `phase8c2_final_paddleocr_gpu_all_variants_600.json`'s
  `field_failures`. No new failures, no fixed failures beyond the
  checkbox detector this phase promotes.

Artifacts:
`data/evaluation/results/phase8c11_promoted_anchor_checkbox_600.json`,
`data/evaluation/results/phase8c11_promoted_anchor_checkbox_rows.jsonl`.

## 5. Fallback Audit (All 600 Documents)

Read directly from each document's `box_13_checkbox_evidence.detection_method`:

- **Anchor-relative used: 600/600.**
- **Fallback used: 0/600.**
- `fallback_document_ids`: empty.

No document triggered `fixed_zone_fallback` or raised during detection.
This matches Phase 8C.10's localization result (600/600 anchor found,
600/600 checkbox found) exactly, as expected since the detector itself
is unmodified.

## 6. Comparison to Phase 8C.10

| | Phase 8C.10 (A/B, flag explicitly `True`) | Phase 8C.11 (production default, no flag passed) |
|---|---:|---:|
| `retirement_plan` correct | 600/600 | 600/600 |
| Total field accuracy | 14396/14400 (99.972%) | 14396/14400 (99.972%) |
| Non-checkbox mismatches vs. frozen 8C.2 | 0 | 0 |
| `employer.name` failures | 4 (`rotated_png`) | 4 (`rotated_png`), same 4 document IDs |
| Fallback count | n/a (not measured by that script) | 0/600 |
| New warnings/fallbacks | -- | None |

Both runs reach identical checkbox and full-field outcomes. Phase 8C.11
additionally confirms the *ordinary* production/default path -- not only
the purpose-built A/B script -- reproduces this result, and adds the
explicit fallback audit that Phase 8C.10's runner did not report.

## 7. Performance

Detector-only latency is unchanged from Phase 8C.10 (unmodified code,
remeasured from `phase8c10_anchor_checkbox_rows.jsonl`'s
`detection_duration_seconds`, since re-running the isolated-detector
script would exercise identical, unretuned logic): **mean 0.056s/doc,
median 0.068s, max 0.096s.**

End-to-end (acquire + parse) latency, measured from the promoted
production-path benchmark:

| | Mean | Median | Min | Max |
|---|---:|---:|---:|---:|
| Phase 8C.2 baseline (frozen) | 1.229s | -- | -- | -- |
| Phase 8C.10 A/B experiment | 1.308s (steady-state, excl. 1st doc) | 1.302s | -- | 7.416s (1st-doc warmup) |
| **Phase 8C.11 promoted default** | **1.267s (steady-state, excl. 1st doc) / 1.280s (all 600)** | **1.200s** | 1.052s | 8.900s (1st-doc warmup) |

The single outlier in each run (7.4s and 8.9s respectively) is the first
document's PaddleOCR model-load/warmup cost, not steady-state behavior;
excluding it, all three runs cluster within normal run-to-run variance
(~1.2-1.3s/doc). Promotion introduces no measurable end-to-end
regression.

## 8. Tests

`tests/extraction/test_acquisition.py` updated (net +1 test, 6 in the
anchor-relative block, up from 5):

- `test_anchor_relative_checkbox_used_by_default_no_flag_required` --
  replaces the old "disabled by default" test; asserts a bare
  `ObservationAcquirer(ocr_adapter=...)` call (no flag) uses the
  anchor-relative detector, and that `box_13_checkbox_evidence.detection_method
  == "anchor_relative"` with `fallback_used is False`.
- `test_anchor_relative_checkbox_disabled_override_never_calls_new_detector`
  -- `enable_anchor_relative_checkbox=False` still exercises the old
  fixed-zone path exclusively (monkeypatch call-count assertion,
  unchanged mechanism from Phase 8C.10's "disabled by default" test) and
  records `detection_method == "fixed_zone_disabled"`.
- `test_anchor_relative_checkbox_unchecked_case`,
  `test_anchor_relative_checkbox_never_triggers_a_second_ocr_call` --
  updated to rely on the new default rather than passing the flag
  explicitly.
- `test_anchor_relative_checkbox_falls_back_when_anchor_not_found` --
  updated to assert the new structured `detection_method ==
  "fixed_zone_fallback"` / `fallback_used is True` / `anchor_found is
  False` fields, in addition to the existing warning-text assertion.
- `test_anchor_relative_checkbox_falls_back_when_checkbox_not_found`
  (new) -- an anchor-only image (no checkbox border drawn) exercises the
  other fallback branch, asserting `anchor_found is True`,
  `checkbox_found is False`.

`tests/extraction/test_checkbox_anchor.py` (Phase 8C.10's 20 detector
unit/architecture tests) is untouched -- the detector itself did not
change. Non-checkbox extraction tests and employer-name validator tests
are untouched.

Full suite: **515 tests passing**, up from 514, **zero regressions**.

## 9. Decision

**Promoted.** Phase 8C.10's evidence (600/600 checkbox classification,
zero non-checkbox regressions, ~4% incremental latency) fully supports
default-on production behavior, and this phase's independent
production-path benchmark reproduces that result exactly through the
ordinary `ObservationAcquirer()`/`PipelineAExtractor()`/`run_pipeline_a.py`
construction path, with zero fallback triggers and zero new warnings
across all 600 documents. The fixed-zone detector remains in the
codebase as an explicit, measurable fallback for the plain-image path
and as the unchanged primary mechanism for image-only/mixed PDF routes
(out of Phase 8C.10/8C.11's scope). A dedicated checkbox validator
consuming the newly-structured `Box13CheckboxEvidence` fields remains
Phase 8C.12, not built here.

## Artifacts

- `src/w2_pipeline/extraction/acquisition.py` (default flip, structured
  evidence wiring)
- `src/w2_pipeline/extraction/models.py` (`Box13CheckboxEvidence`,
  `ObservationSet.box_13_checkbox_evidence`)
- `src/w2_pipeline/evaluation/run_pipeline_a_promoted_checkbox_benchmark.py`
- `tests/extraction/test_acquisition.py`
- `data/evaluation/results/phase8c11_promoted_anchor_checkbox_600.json`
- `data/evaluation/results/phase8c11_promoted_anchor_checkbox_rows.jsonl`
- `docs/contracts/extraction-pipeline-a.md` (promotion note)
- `docs/architecture-decision-record.md` (resolved known-limitation entry)
