# Phase 8C.1 - Rotated `employer.name` Parser/Layout Bug: Remediation

This is the "what did we test and learn" record for Phase 8C.1, matching
the role the other `docs/experiments/*.md` files play. Triggered by a
finding reported (not fixed) in
`docs/experiments/phase8b-final-extraction-benchmark.md`'s failure
taxonomy: the frozen final 600-document benchmark discovered that
`employer.name` fails on 150/150 `rotated_png` documents, identically on
both PaddleOCR and Tesseract.

This is a **narrow remediation task**. Per the brief: the frozen Phase 8B
benchmark results are not rewritten or replaced, OCR is not tuned, the
evaluated field set is not changed, and Box 13 checkbox rotation geometry
(a separate, pre-existing, already-documented failure class) is not
touched here.

## Outcome: FIXED

Root cause confirmed by direct diagnosis against the real failing image
(not assumed from the Phase 8B report alone), a smallest-safe
backend-neutral fix implemented, focused and full test suites pass, and
real-pipeline verification on 4 real rotated documents (both the exact
diagnosed document and 3 others) confirms recovery with zero regressions.

## Background: Why This Wasn't Caught Before Phase 8B

`employer.name`'s only OCR recovery path is the Phase 6B fallback,
`_apply_ocr_employer_layout_fallbacks`'s zone-based
`_first_row_text_in_zone(observations, (0.04, 0.35, 0.25, 0.33))` call
(see `docs/experiments/phase6b-employer-name-investigation.md`). Phase 6B
verified that fix against 5 real documents' `external_clean_render`
variant only, and `employer.name` was not added to any benchmark's
`evaluated_field_paths` until Phase 8A -- so no prior run ever scored this
field against the `rotated_png` variant at any scale until Phase 8B's
final 600-document run. The bug existed the entire time; nothing before
Phase 8B could have surfaced it.

## Investigation

### 1. Is this an OCR recognition failure?

No. Every one of the 150 failing documents' `PredictionRecord`
(`phase8b_final_paddleocr_gpu_all_variants_600_predictions.jsonl` /
the Tesseract equivalent) shows the exact same predicted string:

```text
c Employer's name, address, and ZIP code
```

That is the form's own printed Box c label, read correctly, character for
character -- not garbled, truncated, or misrecognized text. This
immediately rules out an OCR engine problem.

### 2. Where does the label text come from, geometrically?

Ran `PaddleOcrAdapter.extract_image` directly (bypassing the parser) on
the real rotated image
`data/evaluation/external/symage-synthetic-us-forms-preview-final/documents/symage_900001-irs_w2_single_page_2026-p0_rotated.png`.
Filtering for text near Box c, ratio-normalized against
`_layout_extent` (`max_x=2452`, `max_y=1674`):

```text
text="c Employer's name, address, and ZIP code" x0r=0.0746 x1r=0.3108 y0r=0.2497 y1r=0.2820
text='Timberline Trading Co.'                  x0r=0.0722 x1r=0.2125 y0r=0.2909 y1r=0.3202
text='105 Penland St'                          x0r=0.0734 x1r=0.1692 y0r=0.3154 y1r=0.3411
text='Murphy, NC 28906'                        x0r=0.0734 x1r=0.1900 y0r=0.3363 y1r=0.3650
```

Both the label row (`y0r=0.2497-0.2820`) and the true answer row
(`y0r=0.2909-0.3202`) fall inside the calibrated zone
`(0.04, 0.35, 0.25, 0.33)`, with the label positioned topmost. Under
rotation, the printed label drifts a few points closer to the top of the
zone than it sits on the clean (non-rotated) render this zone was
originally calibrated against -- close enough to land inside the same
zone as the answer, rather than above it.

### 3. Does the parser receive/select the label in preference to the answer?

Yes -- this is the entire defect. Before this fix,
`_first_row_text_in_zone` always returned the single topmost row in a
zone (`min(rows, key=vertical_center)`), with no way to distinguish "the
field's own label, which happens to sit in this zone under rotation" from
"the field's actual answer." Since the label row sits above the answer
row in the rotated render, it always won.

### 4. Backend-neutral, or Paddle-specific?

Backend-neutral, confirmed two ways:
- Both backends show identical 150/150 failures on `rotated_png` with the
  identical predicted string, in the frozen Phase 8B artifacts.
- The Phase 8B report already checked for document-ID overlap between the
  two backends' failure sets on this field and found none among the
  rotation failures overlapping in cause (same failure *mode*, backend-
  neutral, per the failure taxonomy) -- consistent with the defect living
  entirely in shared parser code (`_first_row_text_in_zone`,
  `_apply_ocr_employer_layout_fallbacks`), not OCR-backend-specific
  behavior.

### 5. Root cause category and relationship to prior findings

**Parser/layout error**, not OCR recognition, not a dataset defect. Same
root-cause *class* as the earlier-fixed "Rotated Employee-Name
Label-Bleed" bug documented in
`docs/experiments/phase4e-paddle-rotation-name-investigation.md`: under
rotation, a field's own printed label can drift into the same calibrated
zone as its answer. The earlier Box e fix solved this for employee name
via a token-level denylist inside `_clean_layout_token` (filtering words
like `"name"`/`"and"` out of individual tokens). That mechanism was
deliberately **not** reused here (see `_first_row_text_in_zone`'s
docstring and the Phase 6B doc): the employee-name denylist would strip
"and" from a real multi-word employer name like "Smith and Sons Inc.".
Box c needed a row-level (not token-level) discriminator instead.

## Fix

`src/w2_pipeline/extraction/parser_2026.py`:

- Generalized `_first_row_text_in_zone` with an optional `skip_row:
  Callable[[str], bool] | None = None` keyword parameter. Rows are now
  iterated in top-to-bottom order, returning the first row for which
  `skip_row` is `None` or returns `False`, instead of unconditionally
  returning the single topmost row. Passing nothing (`skip_row=None`)
  preserves the exact prior behavior for every other caller/zone.
- Added `_looks_like_employer_name_label_row(row_text: str) -> bool`,
  matching only when a row's text contains **both** `"employer"` and
  `"zip code"` (case-insensitive substring check on the whole
  reconstructed row, not individual tokens). Requiring both markers
  together keeps a false positive on a real employer name effectively
  impossible: no real company name is going to contain both "employer"
  and "zip code" in the same 3-8 word answer line.
- `_apply_ocr_employer_layout_fallbacks`'s `employer.name` branch now
  passes `skip_row=_looks_like_employer_name_label_row` to
  `_first_row_text_in_zone`. No other branch (EIN, Box 13, employee
  fallbacks) is touched -- the fix is scoped to exactly the one call site
  that produced the reported failures.

**Zone geometry is unchanged.** This is a selection-logic fix within the
existing calibrated zone, not a re-calibration -- consistent with "do not
tune OCR" and "smallest safe fix."

**Preferred-characteristics checklist** (all satisfied): no Paddle-
specific or Tesseract-specific branch; no document-ID-specific logic; no
hardcoded answers; no dependency on the frozen Phase 8B benchmark's
ground truth; the discriminator is a structural property of the printed
label text (present on every 2026 W-2 form, not this dataset
specifically), not derived from any specific document; no unrelated OCR
setting, zone-geometry, or checkbox change; and (verified below) no
regression to any existing employee/employer parsing path.

## Testing

9 new tests added to `tests/extraction/test_parser_2026.py`:

- `test_parser_recovers_employer_name_when_rotated_label_precedes_answer_in_zone`
  -- end-to-end reproduction of the real bug: the realistic
  `symage_900001` full-page fixture plus a merged PaddleOCR-style label
  observation positioned topmost in the zone (using the real diagnosed
  pixel geometry), plus the three real Box c line observations. Confirms
  `employer.name` recovers to `"Timberline Trading Co."`, not the label.
- `test_parser_recovers_employer_name_when_rotated_label_fragmented_precedes_answer`
  -- identical scenario with the label split into Tesseract-style word
  fragments instead of one merged line, confirming the fix is
  backend-neutral at the word-fragment-reconstruction level too.
- `test_first_row_text_in_zone_skips_rows_matched_by_skip_row_predicate`
  -- direct unit test of the new `skip_row` mechanism in isolation.
- `test_first_row_text_in_zone_skip_row_none_preserves_old_topmost_behavior`
  -- confirms omitting `skip_row` reproduces the exact prior behavior
  (the topmost row wins even if it is the label), so every pre-existing
  caller and zone is unaffected.
- `test_looks_like_employer_name_label_row_matches_the_real_printed_label`
  -- confirms the detector matches the real label text, case-insensitively.
- `test_looks_like_employer_name_label_row_does_not_match_real_employer_names`
  (parametrized over 4 names, including adversarial ones containing just
  one marker word each -- `"Employer Solutions Group LLC"`, `"ZIP Line
  Logistics Inc."`) -- guards the false-positive side explicitly.

Full suite: **368 tests passing (359 baseline + 9 new), zero regressions.**

## Real-Pipeline Verification

Ran actual `PipelineAExtractor` with the real PaddleOCR GPU backend
(the same backend/config used for the Phase 8B run) against 4 real
`rotated_png` documents, including the exact document used for diagnosis:

| Document | `employer.name` (after fix) |
|---|---|
| symage_900000 | `Advantage Recruiting LLC` |
| symage_900001 | `Timberline Trading Co.` |
| symage_900002 | `BlueWave Enterprises` |
| symage_900003 | `Infinity Enterprises Inc.` |

All 4 recover the correct name instead of the Box c label. No 600-document
re-run was performed -- per the final-test integrity rule, the frozen
Phase 8B artifacts are not regenerated or replaced by this task; a future,
separately-scoped benchmark (Phase 8C.2 or later) may re-run the full
600-document comparison against this fix if a new, explicitly-versioned
benchmark is desired.

## What Was Deliberately Not Done

- The frozen Phase 8B benchmark result files
  (`phase8b_final_*_600.json/.md/_predictions.jsonl`) were not modified,
  regenerated, or replaced.
- No OCR engine, mode, or configuration was changed.
- No evaluated-field-set change was made (still the 24 fields frozen in
  Phase 8A).
- `box_13.retirement_plan`'s rotation checkbox-geometry gap (documented in
  the same Phase 8B failure taxonomy, 60/150 failures on both backends)
  was left untouched -- a separate, pre-existing, already-categorized
  visual-detector issue, out of this task's scope.
- No new 600-document benchmark run was performed to quantify the fix's
  effect on `employer.name` field accuracy at scale; only the 4-document
  real-pipeline check above and the focused/full test suites.

## Remaining Limitations

- The fix addresses only `employer.name`'s rotation label-bleed. If a
  future rotation variant shifts the label into an even earlier row
  position (e.g. above `b Employer identification number (EIN)`'s own
  zone) or shifts the answer itself out of the calibrated zone entirely,
  this specific discriminator would not help -- it only handles "label
  and answer both land in the zone, label first," which is exactly what
  was observed across all 150 real failing documents.
- `employer.address` (street/city/state/ZIP) still has no equivalent
  fallback at all (pre-existing gap, noted in the Phase 6B doc, out of
  scope here).
- A fresh 600-document benchmark re-run to produce an updated, separately
  versioned comparison against this fix is a natural follow-up but was
  intentionally not done as part of this narrow remediation.
