# Phase 8C.10 - OCR-Anchor-Relative `box_13.retirement_plan` Checkbox Detector: PROMOTABLE (Opt-In, Not Auto-Promoted)

Replaces the fragile fixed-page-coordinate `RETIREMENT_PLAN_ZONE` used by
`checkbox_vision.py` with a detector that locates the printed
"Retirement plan" label in the OCR output already produced for the page,
derives a small search region relative to that label's own geometry, and
finds/classifies the checkbox inside that local region. No second OCR
pass, no `variant_id`/filename/ground-truth inspection at runtime, no
change to Paddle OCR configuration, general parser logic, employer-name
parsing, or any other field zone.

## 1. Motivation And Root-Cause Recap

Phase 8C.2's frozen 600-document baseline had 64 total field failures:
60 `box_13.retirement_plan` and 4 `employer.name` (both on `rotated_png`
documents). Phase 8C.9 directly diagnosed why the fixed-zone checkbox
detector fails identically before and after a rotation correction: its
zone ratios are calibrated against one specific canvas geometry (the
clean render), and every other variant's canvas proportions no longer
line up with that fixed rectangle -- the checkbox itself doesn't move
relative to the printed "Retirement plan" label that sits directly above
it, but it does move relative to the page's raw pixel dimensions. A
detector anchored to the label's own OCR-observed position, rather than
to fixed page ratios, should be immune to this by construction.

## 2. Real Geometry Investigation

Diagnosed directly (not assumed) using a custom ASCII pixel-density
visualization tool built for this phase (not committed -- diagnostic
only) against real clean and rotated document images. Two things had to
be resolved before the detector could be written:

- **`RETIREMENT_PLAN_ZONE`'s ratios are relative to the raw image file's
  own pixel dimensions** (`Image.open(path).size`), not the
  OCR-observation-based `_layout_extent` used elsewhere in the parser --
  an initial diagnostic script that used the OCR extent (2402x1591)
  instead of the actual image size (2550x3300) made the zone appear to
  be in the wrong location entirely.
- **The checkbox sits directly below the label's lower text line
  ("plan"), left-aligned, with a near-zero vertical gap** -- verified on
  both a clean render and a rotated document, confirming the *local*
  relationship between label and checkbox stays stable even though the
  *global* page position varies enormously across variants. This is the
  entire premise the phase depends on.

## 3. Implementation

New module: `src/w2_pipeline/extraction/checkbox_anchor.py`. Pillow-only
(no OpenCV/numpy), takes only `image_path` and the OCR `observations`
already produced for the page -- verified by signature inspection and an
AST-based import check (no `w2_pipeline.validation` dependency anywhere
in the module).

**Anchor matching** (`find_retirement_plan_anchor`): handles both the
merged case (a single OCR observation reading "Retirement plan") and the
real PaddleOCR shape, where "Retirement" and "plan" arrive as two
separate, vertically-stacked observations. Pairing requires the "plan"
observation to sit below (not above) "Retirement", within a horizontal
offset bounded by the label's own line height, and a vertical gap
bounded between `-0.75 * line_height` (loosened from an initial `-5px`
after real blurred-variant OCR output showed a genuine `-7px` line-box
overlap being incorrectly rejected) and `2 * line_height`. A `\bplan\b`
word boundary keeps "11 Nonqualified plans" from false-matching.

**Local search geometry** (`derive_checkbox_search_region`): a region
directly below the label's lower line, scaled by that line's own height
and width (`SEARCH_BELOW_HEIGHT_MULTIPLIER = 3.0`,
`SEARCH_HORIZONTAL_MARGIN_MULTIPLIER = 0.6`) -- position- and
scale-relative to the label, never a fixed page coordinate.

**Checkbox object localization** (`locate_checkbox_candidate`): finds
the checkbox's printed border first (identifies the object, not just
"dark pixels") via horizontal contiguous dark-pixel runs, requiring a
minimum run length scaled to the anchor's own line height (`max(
anchor_line_height * 1.0, 10.0)` -- an initial `crop_width * 0.5`
threshold was too strict, since the search region is deliberately wider
than the checkbox itself to tolerate horizontal alignment drift; this
was self-diagnosed against manually measured real pixel coordinates).
Top/bottom border rows are found this way, then left/right border
columns are found scanning between them. A `shape_score` measuring
deviation from a square aspect ratio is recorded as evidence.

**Interior-vs-border classification** (`compute_interior_ink_ratio`):
insets the located box by `_BORDER_INSET_FRACTION = 0.22` on each side
before computing the dark-pixel ratio, so the printed border itself is
never counted as a "mark" -- classification is based on interior ink
only, never total box-region ink.

**Provenance, never fabricated**: `RetirementPlanDetection` carries
`anchor_found`, `anchor`, `checkbox_found`, `checkbox`,
`interior_ink_ratio`, `retirement_plan`, and `decision_margin` as
distinct fields (no single collapsed "confidence" score). If the anchor
or checkbox cannot be localized, `retirement_plan` is `None` -- the
detector never falls back to guessing from the old fixed zone internally
; that fallback, when it happens, is the *caller's* explicit decision
(see Section 6).

## 4. Localization Results (Phase 8C.10A)

New script: `src/w2_pipeline/evaluation/run_anchor_checkbox_analysis.py`.
Ran directly against all 600 manifest documents using the real
`PaddleOcrAdapter` (single OCR pass; ground truth loaded only *after*
detection, for offline scoring).

| Variant | n | Anchor found | Checkbox found |
|---|---:|---:|---:|
| `external_clean_render` | 150 | 150/150 | 150/150 |
| `rotated_png` | 150 | 150/150 | 150/150 |
| `compressed_jpeg` | 150 | 150/150 | 150/150 |
| `blurred_png` | 150 | 150/150 | 150/150 |
| **Total** | **600** | **600/600 (100%)** | **600/600 (100%)** |

Cross-variant local geometry, measured directly (not assumed): anchor
distance stayed within -2px to 0px, checkbox width 43-44px, height
50-52px, `shape_score` 0.82-0.88 across all four variants of the same
underlying document -- confirming the local label-to-checkbox
relationship is stable exactly as the Section 2 investigation predicted,
even though the checkbox's absolute page position differs by hundreds of
pixels between `external_clean_render` and `rotated_png`.

Artifacts: `data/evaluation/results/phase8c10_anchor_checkbox_600.json`,
`..._rows.jsonl`.

## 5. Classification Results (Phase 8C.10B)

`interior_ink_ratio` showed complete, non-overlapping separation across
all 600 documents: **checked always 0.244-0.298, unchecked always
exactly 0.0** -- zero overlap, meaning any threshold between roughly
0.001 and 0.24 would classify perfectly. `DEFAULT_INTERIOR_INK_THRESHOLD
= 0.12` was chosen because it sits in the middle of that wide margin,
not because it was tuned to force a result.

Confusion matrix (600/600): TP 360, TN 240, FP 0, FN 0 -- **100%
accuracy**, identical across all four variants (150/150 each).

Cross-referenced by exact `document_id`/`variant_id` set comparison
against the frozen Phase 8C.2 `field_failures` list: **all 60 previously
failing `box_13.retirement_plan` documents are now fixed, and zero new
failures were introduced.**

## 6. Production Integration

`ObservationAcquirer` gained `enable_anchor_relative_checkbox: bool =
False` (default off, matching the Phase 8C.9 opt-in pattern) and
`checkbox_interior_ink_threshold: float = DEFAULT_INTERIOR_INK_THRESHOLD`.
When enabled, the plain-image acquisition path calls
`detect_retirement_plan` using the OCR observations already produced (no
second OCR pass -- verified by a dedicated test asserting the OCR
adapter is called exactly once). If the anchor/checkbox cannot be
localized, or the detector raises, it falls back explicitly to the
original fixed-zone `detect_box_13_retirement_plan_mark` -- which
detector actually ran is recorded in `ObservationSet.warnings`
("anchor-relative detection used" vs. "... fell back to fixed-zone
detector"), never silently inferred. Flag left off changes nothing about
the default code path (confirmed by a monkeypatch-based call-count
assertion: zero calls to the new detector when disabled).

## 7. Full-Pipeline Regression Check (600 Documents)

New script:
`src/w2_pipeline/evaluation/run_pipeline_a_with_anchor_checkbox.py`.
Identical OCR/parser/schema/evaluator to the frozen Phase 8C.2 run, only
`enable_anchor_relative_checkbox=True` differs; every field except
`box_13.retirement_plan` is compared byte-for-byte against the frozen
Phase 8C.2 prediction for the same `document_id`.

- **`non_checkbox_field_mismatches_vs_frozen_phase8c2`: empty (0 of
  600)** -- every non-checkbox field is bit-identical to the frozen
  baseline.
- **Total field accuracy: 14396/14400 = 99.972%**, up from Phase 8C.2's
  14336/14400 = 99.556%.
- `box_13.retirement_plan`: 0/600 incorrect (was 60/600).
- The 4 remaining failures are all `employer.name` on `rotated_png`,
  identical by exact `(document_id, variant_id)` set comparison to the
  frozen baseline's 4 `employer.name` failures -- pre-existing, unrelated
  to this phase, and explicitly out of scope (no employer-name parsing
  or validator logic was touched).

Artifacts:
`data/evaluation/results/phase8c10_full_pipeline_ab_benchmark_600.json`,
`..._rows.jsonl`.

## 8. Performance

Measured directly from `phase8c10_anchor_checkbox_rows.jsonl`'s
`detection_duration_seconds` field (anchor lookup + local checkbox
localization + interior classification, combined -- these are simple
Pillow crop/histogram operations, not independently expensive enough to
warrant splitting further):

- Mean: **0.056 seconds/document**, median 0.068s, max 0.096s.
- This is a small addition on top of the dominant per-document cost,
  which remains PaddleOCR itself (`duration_seconds` mean 1.32s/document,
  including OCR) -- the new detector adds roughly 4% incremental latency
  and does not introduce a second OCR pass.

## 9. Failure Taxonomy

Zero failures to classify: 600/600 anchor found, 600/600 checkbox found,
600/600 correctly classified. No `anchor_not_found`,
`checkbox_not_found`, `wrong_candidate_selected`,
`candidate_geometry_weak`, `classification_false_positive`,
`classification_false_negative`, or `OCR_anchor_error` cases occurred on
this 600-document set. This is reported honestly as an empty taxonomy,
not fabricated to appear more nuanced -- see Section 10 for the residual
risk this implies.

## 10. What Was Deliberately Not Done

- **Not promoted to default-on.** `enable_anchor_relative_checkbox`
  stays an explicit, off-by-default opt-in; no production caller enables
  it as part of this phase. The brief explicitly instructs against
  auto-promotion.
- **Not force-fit to 100% via overfitting.** The 600/600 result reflects
  the detector's actual behavior on this dataset's four variants
  (clean/rotated/compressed/blurred) at moderate rotation/compression/
  blur severities; no threshold or geometry constant was tuned against
  individual failing documents to close a gap -- the wide interior-ink
  separation margin (Section 5) supports this.
- **`employer.name`'s 4 remaining failures are untouched**, per the
  brief's explicit do-not list -- they are Phase 8C.9's already-documented,
  already-decided-against-fixing-via-deskew residual, not something this
  phase attempted.
- **A dedicated checkbox validator (confidence-based acceptance/rejection
  signal for `box_13.retirement_plan`, analogous to the employer-name
  validator signals from Phase 8C.5-8C.8) was not built.** This phase
  only replaces the detector; `AnchorMatch`, `CheckboxCandidate`, and
  `RetirementPlanDetection` deliberately preserve distinct evidence
  fields (`anchor_distance_px`, `shape_score`, `interior_ink_ratio`,
  `decision_margin`) rather than collapsing to one score, specifically so
  a future validator phase can consume them without re-deriving evidence
  from scratch.
- **No global deskew enabled or re-tuned**; Phase 8C.9's decision stands
  unchanged and independent of this phase.
- **More extreme rotation angles, additional real-world scan artifacts,
  or a non-synthetic dataset were not tested** -- this is a synthetic,
  four-variant dataset, and the 100% result should be read in that
  context, not as a guarantee against arbitrary real-world skew/damage.

## 11. Decision

**A. Strictly better than the fixed-zone baseline, evidence supports
promotion -- but not auto-promoted per the brief.** Every non-checkbox
field is bit-identical to the frozen Phase 8C.2 baseline; the only
behavior change is `box_13.retirement_plan`, which moves from 90.0%
(540/600) to 100% (600/600) correct with zero regressions anywhere else,
at roughly 4% incremental latency. The remaining open items are (a) a
human/product decision on whether to flip
`enable_anchor_relative_checkbox=True` in the production caller, and (b)
whether a dedicated checkbox validator (confidence-based, using the
preserved evidence fields) is still worth building before that flip --
recommended given this is a synthetic-dataset result, even though this
phase found no residual failures to justify it reactively.

## 12. Tests

`tests/extraction/test_checkbox_anchor.py` (20 tests): anchor matching
(merged/two-line/case-insensitive/whitespace-tolerant/word-boundary/
missing/below-not-above), local geometry (translates and scales with
label position/size, verified via exact pixel-offset arithmetic), candidate
detection and interior classification (empty box, checked vs. unchecked,
thick-border-not-counted-as-mark, no-checkbox-returns-none), full
end-to-end pipeline (checked, unchecked, never-fabricates-without-anchor),
and leakage/architecture safeguards (signature inspection confirming no
`variant_id`/filename/ground-truth parameter anywhere in the module;
AST-based import check confirming no `w2_pipeline.validation`
dependency).

`tests/extraction/test_acquisition.py` (+5 tests): flag-off leaves the
old code path completely untouched (monkeypatch call-count assertion),
flag-on uses the new detector and records the method in warnings,
checked/unchecked cases, fallback-when-anchor-not-found, and
never-triggers-a-second-OCR-call (adapter call-count assertion).

Full suite: **514 tests passing** (up from 489 before this phase),
**zero regressions**.

## Artifacts

- `src/w2_pipeline/extraction/checkbox_anchor.py`
- `src/w2_pipeline/evaluation/run_anchor_checkbox_analysis.py`
- `src/w2_pipeline/evaluation/run_pipeline_a_with_anchor_checkbox.py`
- `tests/extraction/test_checkbox_anchor.py`
- `data/evaluation/results/phase8c10_anchor_checkbox_600.json`
- `data/evaluation/results/phase8c10_anchor_checkbox_rows.jsonl`
- `data/evaluation/results/phase8c10_full_pipeline_ab_benchmark_600.json`
- `data/evaluation/results/phase8c10_full_pipeline_ab_benchmark_rows.jsonl`
