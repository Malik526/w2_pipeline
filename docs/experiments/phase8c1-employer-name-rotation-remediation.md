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

## Outcome: FIXED (the reported bug); one distinct, rarer defect found and reported, not fixed

Root cause of the reported 150/150 label-bleed bug confirmed by direct
diagnosis against the real failing image (not assumed from the Phase 8B
report alone). Two fixes were needed -- one per backend's OCR output
shape -- both backend-neutral in code (no Paddle-specific or
Tesseract-specific branch). Full 150-document `rotated_png` verification
on both backends (not just a handful of documents) confirms
`employer.name` recovers from 0/150 to 149/150 (Tesseract) and 146/150
(PaddleOCR), zero test regressions. The small residual on both backends
is a distinct, rarer defect (see below), deliberately not fixed here as
it falls outside this task's narrow scope.

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
- `_looks_like_employer_name_label_row` also returns `True` for a row
  whose entire text is a single alphabetic character -- added after
  150-document Tesseract verification surfaced a second, related defect;
  see "A Second, Tesseract-Specific Defect Found At Scale" below for why.

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

13 new tests added to `tests/extraction/test_parser_2026.py`, across both
fixes:

**First fix (label row skip):**
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

**Second fix (lone box-letter row skip), added after 150-document
Tesseract verification surfaced the second defect:**
- `test_parser_recovers_employer_name_when_box_letter_marker_forms_its_own_row`
  -- end-to-end reproduction using the real Tesseract pixel geometry from
  `symage_900001-...-rotated.png` (scaled to the shared fixture's own
  layout extent), with the label's word tokens drifting enough that "c"
  forms its own row between the (skipped) label row and the real answer.
  Confirms recovery to `"Timberline Trading Co."`.
- `test_looks_like_employer_name_label_row_matches_a_lone_box_letter_marker`
  -- direct unit test that a bare `"c"`/`"C"` row is now skipped.
- `test_looks_like_employer_name_label_row_lone_letter_rule_only_matches_single_char`
  (parametrized) -- confirms the rule fires only for a true single
  character, never for a real employer name.

Full suite: **372 tests passing (359 baseline + 13 new), zero
regressions.**

## Real-Pipeline Verification

### First pass: 4-document spot check (PaddleOCR)

Ran actual `PipelineAExtractor` with the real PaddleOCR GPU backend
(the same backend/config used for the Phase 8B run) against 4 real
`rotated_png` documents, including the exact document used for diagnosis:

| Document | `employer.name` (after fix) |
|---|---|
| symage_900000 | `Advantage Recruiting LLC` |
| symage_900001 | `Timberline Trading Co.` |
| symage_900002 | `BlueWave Enterprises` |
| symage_900003 | `Infinity Enterprises Inc.` |

All 4 recovered the correct name instead of the Box c label.

### Second pass: full 150-document `rotated_png` scale check, both backends

A 4-document spot check is not sufficient to claim "backend-neutral at
scale," and Tesseract's word-level fragmentation is structurally
different from PaddleOCR's merged-line output (see "A Second,
Tesseract-Specific Defect Found At Scale" below) -- so this task ran the
full `w2_pipeline.evaluation.run_pipeline_a` CLI (the same tool Phase 8B
used) filtered to `--variant-id rotated_png` only (150 documents), once
per backend, with the exact Phase 8B OCR configuration (PaddleOCR GPU;
Tesseract PSM 3 + supplemental PSM 6), `--save-predictions` capturing
full per-document predictions. Written to **new**, separately-named
artifacts -- the frozen Phase 8B `..._600.*` files were never touched:

```text
data/evaluation/results/phase8c1_verify_paddleocr_gpu_rotated_150.json
data/evaluation/results/phase8c1_verify_paddleocr_gpu_rotated_150.md
data/evaluation/results/phase8c1_verify_paddleocr_gpu_rotated_150_predictions.jsonl
data/evaluation/results/phase8c1_verify_tesseract_psm3_psm6_rotated_150.json
data/evaluation/results/phase8c1_verify_tesseract_psm3_psm6_rotated_150.md
data/evaluation/results/phase8c1_verify_tesseract_psm3_psm6_rotated_150_predictions.jsonl
```

| Metric | PaddleOCR GPU | Tesseract PSM3+6 |
|---|---:|---:|
| Rotated documents | 150 | 150 |
| Failed documents | 0 | 0 |
| `employer.name` accuracy (before this task's fix, per Phase 8B) | 0.0% (0/150) | 0.0% (0/150) |
| `employer.name` accuracy (after fix) | **97.33% (146/150)** | **99.33% (149/150)** |
| Overall rotated field accuracy (all fields, this variant only) | 98.22% | 97.61% |

Both backends go from complete, systematic failure to near-complete
recovery on the exact bug this task targeted. Neither backend reaches
100% -- see the next section for the residual, which is a related but
distinct defect, not the one reported in Phase 8B.

## A Second, Tesseract-Specific Defect Found At Scale

The 4-document PaddleOCR-only spot check above was not enough to
guarantee the fix generalizes: PaddleOCR reports Box c's label as **one
merged line observation** ("c Employer's name, address, and ZIP code"),
so it always lands in a single row and `_looks_like_employer_name_label_row`
catches it outright. The initial 150-document Tesseract run (before this
second defect was found and fixed) showed **0/150 still correct** --
identical to the pre-fix number -- because Tesseract reports each word as
its **own** observation, including the printed Box c letter marker
("c") as a separate one-character observation from the rest of the
label's words.

Diagnosis (direct `TesseractOcrAdapter.extract_image` inspection of
`symage_900001-...-rotated.png`, the same document used for the original
diagnosis): under rotation skew, each word's vertical center drifts by a
different amount depending on its horizontal position in the line.
`_group_observation_rows` merges words into a row only if each one falls
within a tolerance of the row's running average center (tolerance scales
with that word's own height). As the label's five multi-character words
("Employer's", "name,", "address,", "and", "ZIP", "code") merge into one
row, the running average center drifts across roughly 20 pixels; the
short, small "c" token's own tolerance (its height is much smaller,
around 15-16px) is no longer wide enough to absorb that accumulated
drift, so "c" fails to merge and forms its **own** one-word row --
positioned between the (already correctly skipped) label row and the
real answer row. `_looks_like_employer_name_label_row`'s two-marker check
does not match a bare "c", so this new row was returned verbatim as
`employer.name` on all 150/150 Tesseract rotated documents.

**Fix**: `_looks_like_employer_name_label_row` (same function, no new
call sites) now also returns `True` for a row whose full text is a
single alphabetic character -- the printed box-letter marker every W-2
box carries ("a" through "f" etc.), never a legitimate `employer.name`
value on its own. Re-running the same 150-document Tesseract check after
this second fix: `employer.name` accuracy went from 0/150 to 149/150 (the
table above already reflects the post-fix number).

This finding is exactly why the brief's instinct to verify "at scale," not
just on a handful of hand-picked documents, mattered: the first fix
verified correctly on 4 PaddleOCR documents and looked complete, but a
structurally different backend surfaced a related defect the small
sample never could.

## Residual: One Distinct, Rarer, Multi-Line-Merge Defect (Not Fixed Here)

Both backends' 150-document runs above still show a small number of
residual `employer.name` failures -- **not** the label-bleed bug this
task targeted, and confirmed backend-neutral by direct inspection
(`symage_900146` fails on *both* backends):

| Document | Backend | Expected | Predicted |
|---|---|---|---|
| symage_900033 | PaddleOCR | `Elan Consulting Corp` | `Elan Consulting Corp 2861 Geneva Ponce De Leon Rd` |
| symage_900045 | PaddleOCR | `Bespoke Designs LLC` | `Bespoke Designs LLC 6878 Normandy Tullahoma Rd` |
| symage_900082 | PaddleOCR | `FutureReady Services` | `FutureReady Services 875 Francis Case Memorial Brg` |
| symage_900146 | PaddleOCR | `Global Insights Corp` | `Global Insights Corp 4522 Eastern Transportation Corridor` |
| symage_900146 | Tesseract | `Global Insights Corp` | `Global Insights Corp Corridor` |

Direct inspection of `symage_900146`'s Tesseract observations confirmed
the mechanism: it is the *same underlying fragility* in
`_group_observation_rows`'s tolerance-under-rotation-skew, but the
opposite direction from the fix above -- here, the **answer row and the
following address line's own drifted words merge into one row**, instead
of correctly staying separate. PaddleOCR's coarser merged-line output
makes it merge the entire next line rather than a single trailing word.

**Deliberately not fixed in this task.** This is a structurally distinct
defect from the one Phase 8B reported and this task was chartered to fix
(a row that shouldn't merge, merging -- rather than a label row winning
over an answer row), it is much rarer (4/150 and 1/150 respectively, vs.
the original 150/150), and a safe fix would need to either loosen/tighten
`_group_observation_rows`'s shared tolerance (a change with blast radius
across every zone and field in the parser, not scoped to `employer.name`)
or add a second, differently-shaped `employer.name`-specific heuristic --
either of which is new scope beyond "remediate the rotated employer.name
label bug," which is now complete. Reported here as a result, the same
way Phase 8B reported (without fixing) the original bug.

## What Was Deliberately Not Done

- The frozen Phase 8B benchmark result files
  (`phase8b_final_*_600.json/.md/_predictions.jsonl`) were not modified,
  regenerated, or replaced. Verification used new, separately-named
  `phase8c1_verify_*_rotated_150.*` artifacts instead (see "Real-Pipeline
  Verification" above).
- No OCR engine, mode, or configuration was changed.
- No evaluated-field-set change was made (still the 24 fields frozen in
  Phase 8A).
- `box_13.retirement_plan`'s rotation checkbox-geometry gap (documented in
  the same Phase 8B failure taxonomy, 60/150 failures on both backends)
  was left untouched -- a separate, pre-existing, already-categorized
  visual-detector issue, out of this task's scope.
- No full 600-document benchmark re-run was performed to produce an
  updated, official comparison superseding Phase 8B's numbers; the
  150-document `rotated_png`-only runs above exist purely to verify this
  fix at the scale the original bug was found at, not to replace or
  extend the frozen benchmark.
- The residual multi-line-merge defect found during this verification
  (4/150 PaddleOCR, 1/150 Tesseract, both on `symage_900146`) was
  diagnosed and reported but deliberately not fixed -- see "Residual"
  above for why it is out of this task's scope.

## Remaining Limitations

- The fix addresses only `employer.name`'s rotation label-bleed (both the
  merged-line and lone-box-letter-row shapes it takes across backends).
  If a future rotation variant shifts the label into an even earlier row
  position (e.g. above `b Employer identification number (EIN)`'s own
  zone) or shifts the answer itself out of the calibrated zone entirely,
  this specific discriminator would not help.
- The residual multi-line-merge defect (documented above, 4/150 and
  1/150) remains: under sufficiently large rotation skew, the answer row
  can still merge with part or all of the following address line. A
  proper fix likely requires reworking `_group_observation_rows`'s
  tolerance to account for accumulated per-row skew directly, rather than
  per-token height alone -- a larger, shared-subsystem change
  appropriately scoped to its own future task.
- `employer.address` (street/city/state/ZIP) still has no equivalent
  fallback at all (pre-existing gap, noted in the Phase 6B doc, out of
  scope here).
- A fresh 600-document benchmark re-run to produce an updated, separately
  versioned comparison against these fixes is a natural follow-up but was
  intentionally not done as part of this narrow remediation.
