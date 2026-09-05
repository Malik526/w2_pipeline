# Phase 6B - Employer Name Extraction Gap: Investigation And Remediation

This is the "what did we test and learn" record for Phase 6B, matching the
role the other `docs/experiments/*.md` files play. Triggered by a finding
in `docs/experiments/phase6-validation-feasibility.md`: Phase 6 validation
flagged `employer.name = null` on a real Pipeline A prediction for an
external Symage document, a gap invisible to every prior benchmark because
`employer.name` has never been in any Symage record's
`evaluated_field_paths`.

## Outcome: FIXED

Root cause identified, a smallest-safe backend-neutral fix implemented,
focused and full test suites pass, and real-document verification confirms
recovery on all 5 diagnostic documents with zero regressions on unrelated
fields.

## How Phase 6 Surfaced The Issue, And Why Prior Benchmarks Missed It

Phase 6's validator judges the `W2Document` a pipeline actually produced,
using only the canonical contract's own required-field rules -- it has no
concept of `evaluated_field_paths` (a benchmark-scoring detail) at all.
Every historical Pipeline A benchmark result in `docs/project-state.md`
excluded `employer.name` from scoring because the Symage adapter has never
authoritatively mapped it from the FUNSD annotations, so a systematic
extraction gap there could never move (or even appear in) any reported
accuracy number. The very first real document Phase 6 was pointed at
surfaced it immediately.

## Investigation

### 1. Is the employer name visibly present in the source image?

Yes. Confirmed via the Symage dataset's own evaluator-side FUNSD
annotations (`annotations/*.json`, never used at runtime -- inspected here
purely for diagnosis), which is available strictly for this kind of
investigation, not for injecting into ground truth or the pipeline. The
FUNSD `question` entity "Employer's name, address, and ZIP code" links to
an `answer` entity with a clean, deterministic multi-line text value, e.g.
for `symage_900001`:

```text
"Timberline Trading Co.\n105 Penland St\nMurphy, NC 28906"
```

Checked across all 5 diagnostic documents (`symage_900001` through
`symage_900004`, `symage_900006`) -- every one has this exact same
structure: employer name as the first line, street address second,
city/state/ZIP third.

### 2. Does PaddleOCR correctly recognize the text?

Yes, cleanly. Running `PaddleOcrAdapter.extract_image` directly (bypassing
the parser) on `symage_900001`'s clean-render image returned, among 78
total observations:

```text
text='Timberline Trading Co.' bbox=(162,414,504,453)
text='105 Penland St'         bbox=(164,454,398,488)
text='Murphy, NC 28906'       bbox=(163,489,448,529)
```

Three separate, correctly-recognized, already-line-reconstructed
observations (PaddleOCR's line-level recognition, as documented in
`docs/contracts/extraction-pipeline-a.md`) exactly matching the FUNSD
answer's three lines. **This rules out an OCR recognition failure
entirely** -- the text is present, correct, and cleanly segmented before
it ever reaches the parser.

### 3-5. Does the parser receive/select it? Is it excluded/filtered/joined/confused?

The observations reach the parser (nothing upstream drops them). The
defect is entirely in `_parse_employer` (`parser_2026.py`):

- The primary path (`_value_after_label(right_lines, "Name")`) requires a
  literal `"Name:"` prefix in reconstructed line text. The real 2026 W-2
  form's Box c has no such label in its printed value -- it is one
  combined, unlabeled "Employer's name, address, and ZIP code" block. This
  primary path matches the *internal* synthetic generator's own rendering
  convention (which does print literal `"Name: ..."`/`"Address 1: ..."`
  lines), but never matches the external Symage render's real-form layout.
- Compounding this, `_observations_in_x_range` splits "employee" (left,
  `x0 < 300`) from "employer" (right, `x0 >= 300`) using a **raw absolute
  pixel threshold**. On a 2550x3300-pixel external render, the entire Box
  c text block sits at `x0 ~= 162-171` -- comfortably *below* 300, so even
  if it had matched a label, it would have landed in the *employee*
  column, not the employer one. This threshold was evidently calibrated
  for the internal generator's own (much smaller, PDF-point-scale) two-
  column rendering, not for OCR-scale external images.
- `_parse_employee` already has a ratio-based OCR zone fallback
  (`_apply_ocr_employee_layout_fallbacks`, covering SSN/first/last/suffix)
  that recovers exactly this class of primary-path failure -- ratios of
  `_layout_extent(observations)` (the OCR-detected text extent) are
  resolution-independent, unlike the employee/employer x-range split.
  **`_parse_employer` had no equivalent fallback for `employer.name`** --
  only `employer.ein` had one (`_first_ein_from_ocr_layout`). This
  asymmetry is the root cause: nothing was ever wrong with *how* the name
  was read, only that no code path existed to read it from OCR layout at
  all.

### 6. Backend-neutral, or Paddle-specific?

Backend-neutral. Running actual Tesseract-backed `PipelineAExtractor`
(the project's default) on the same 3 documents (`symage_900001` through
`symage_900003`) showed the identical `employer.name = None` before the
fix and identical correct recovery after it. The root cause is entirely in
shared parser code (`_parse_employer`), not any OCR-backend-specific
behavior -- consistent with every other OCR-layout-fallback fix in this
project's history.

### 7. Root cause category

**Parser-side**: field-boundary selection (the x-range column split) and
missing zone-based fallback coverage for `employer.name` specifically. Not
OCR recognition, not coordinate confusion with the employer address (name
and address ARE visually adjacent lines in the same Box c block, which is
exactly why the fix isolates only the *first* line rather than the whole
block -- see "Fix" below), and not a dataset/rendering defect.

## Fix

`src/w2_pipeline/extraction/parser_2026.py`:

- Added `_first_row_text_in_zone(observations, zone)`: returns only the
  topmost printed line within a ratio zone (via the existing
  `_group_observation_rows` row-reconstruction), for zones that may
  contain more than one line -- unlike `_zone_text`, which joins every
  observation in a zone regardless of row and would concatenate all three
  Box c lines into one garbled string. Deliberately does **not** reuse
  `_clean_layout_token` (its Box e label-word denylist includes `"and"`
  and `"name"`, guarding against an unrelated rotated-label-bleed bug;
  reusing it here would risk silently dropping "and" from a real name like
  "Smith and Sons Inc.").
- Added `_apply_ocr_employer_layout_fallbacks(employer, observations)`,
  mirroring `_apply_ocr_employee_layout_fallbacks`'s existing pattern:
  fills `employer.ein` (unchanged logic, just relocated) and now
  `employer.name` via `_first_row_text_in_zone(observations, (0.04, 0.35,
  0.25, 0.33))` whenever the primary label-based path left it `None`.
  Never overrides an already-successful primary-path value.
- `_parse_employer` now calls this single fallback function instead of the
  previous EIN-only inline check.

**Zone calibration**: `(0.04, 0.35, 0.25, 0.33)` as ratios of
`_layout_extent(observations)` (matching every other OCR fallback zone in
this file), derived from the FUNSD answer boxes across all 5 diagnostic
documents (all had `x0 ~= 166`, `y0 ~= 419-421`, `y1 ~= 524-527`, with
`x1` varying 496-594 depending on name/address length) with generous
margin for longer employer names. The zone deliberately spans enough
vertical range to include the address lines too -- `_first_row_text_in_zone`
robustly isolates just the name regardless of how many lines follow,
without needing to guess an exact per-document line height.

**Preferred-characteristics checklist** (all satisfied): no Paddle-specific
or Tesseract-specific branch; no document-ID-specific logic; no hardcoded
answers; no benchmark-ground-truth dependency; the zone was calibrated
from FUNSD boxes and independently confirmed via real OCR output, not
guessed; no unrelated OCR setting changes; and (verified below) no
regression to existing employee/employer/address parsing.

## Testing

7 new tests in `tests/extraction/test_parser_2026.py`:

- `test_parser_recovers_employer_name_from_ocr_full_page_layout` -- the
  full realistic `symage_900001` fixture (identical to the pre-existing
  `test_parser_extracts_external_style_ocr_word_observations`, so the
  layout-extent-relative zone ratios match a real document exactly) plus
  the three Box c line observations; confirms `employer.name` recovered,
  `employer.address.address_line_1` still `None` (fix is scoped to name
  only), and EIN/employee SSN/name all unchanged.
- `test_parser_recovers_multiword_employer_name_with_and` -- a
  Tesseract-style word-fragmented "Smith and Sons Inc." name at the real
  employer-name pixel position, confirming multi-word names and the word
  "and" specifically survive intact.
- `test_parser_does_not_override_primary_path_employer_name` -- a
  primary-path `"Name:"` line present alongside Box c zone content;
  confirms the fallback never overrides an already-successful read.
- `test_parser_employer_name_fallback_absent_without_zone_observations` --
  no Box c observations at all; confirms `employer.name` stays `None`
  (no fabrication), matching the pre-fix, already-passing fixture that
  omits Box c.
- `test_first_row_text_in_zone_isolates_topmost_line_from_multiline_zone`,
  `test_first_row_text_in_zone_joins_fragmented_words_left_to_right`,
  `test_first_row_text_in_zone_returns_none_for_empty_zone` -- direct unit
  tests of the exact new mechanism.

Full suite: **275 tests passing (268 baseline + 7 new), zero regressions.**

## Real-Pipeline Verification

Ran actual `PipelineAExtractor` (not fixtures) against the 5 diagnostic
documents' real `external_clean_render` images, comparing employer output
before vs. after the fix:

| Document | `employer.name` (before) | `employer.name` (after) | `employer.ein` (after) |
|---|---|---|---|
| symage_900001 | `null` | `Timberline Trading Co.` | `75-5696876` (unchanged) |
| symage_900002 | `null` | `BlueWave Enterprises` | `51-6163111` (unchanged) |
| symage_900003 | `null` | `Infinity Enterprises Inc.` | `63-4467342` (unchanged) |
| symage_900004 | `null` | `Bright Horizons Corp` | `62-6885566` (unchanged) |
| symage_900006 | `null` | `Evergreen Solutions LLC` | `74-9289871` (unchanged) |

Every recovered name matches the FUNSD answer's first line exactly (see
"Investigation" step 1). `employer.address` remained `null` on every
document both before and after (unaffected, as intended -- out of this
fix's scope). Re-ran with the default Tesseract backend on 3 of the 5
documents (`symage_900001`-`symage_900003`): identical results, confirming
backend-neutrality. No 150/600-document benchmark was run -- this
5-document real-pipeline check is the extent of verification per the
brief's scope.

## Can `employer.name` Be Added To Symage `evaluated_field_paths`?

**Investigated, documented, not implemented here.** The FUNSD "answer"
entity linked to the "Employer's name, address, and ZIP code" question
provides exactly this structure:

```text
"<name>\n<street address>\n<city, state zip>"
```

Splitting on the first `\n` deterministically yields the employer name,
independent of any Pipeline A prediction -- confirmed identical to this
fix's recovered values across all 5 diagnostic documents. This satisfies
the brief's stated criteria (authoritative source annotation, deterministic
mapping, no dependency on the extractor being evaluated). However,
implementing it means changing `src/w2_pipeline/evaluation/external_symage.py`
(the FUNSD-to-canonical mapping adapter) and regenerating the external
dataset's ground truth/manifest via `prepare_external_dataset.py` -- a
benchmark-harness change, not a parser fix, and one that would affect
every existing external-benchmark comparison's field coverage. That is a
separate, appropriately-scoped follow-up task (per the brief: "the runtime
extraction fix and benchmark-ground-truth question are separate"), not
undertaken as part of this narrow investigation+remediation task.

## Remaining Limitations

- `employer.address` (street/city/state/ZIP) has the identical
  architectural gap -- no OCR zone fallback exists for it either -- but is
  out of this task's explicit scope (`employer.name` only). A follow-up
  could extend `_apply_ocr_employer_layout_fallbacks` with
  `_first_row_text_in_zone` calls for the second and third Box c lines
  using the same calibrated zone.
- `employer.name`/`employer.address` still cannot be benchmark-scored
  until the Symage adapter change described above is made.
- No 150/600-document benchmark was run to quantify the fix's effect on
  `employer.name` field accuracy at scale (deliberately out of scope); only
  the 5-document real-pipeline check above.
