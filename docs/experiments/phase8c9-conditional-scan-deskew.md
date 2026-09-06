# Phase 8C.9 - Conditional Small-Angle Scan-Deskew Experiment

Offline preprocessing experiment: can image-derived small-angle deskew
eliminate the remaining rotation-driven checkbox and `employer.name`
failures without regressing already-correct clean/JPEG/blur documents?
No OCR/parser/checkbox logic was tuned; deskew is implemented as a new,
opt-in preprocessing step (`enable_conditional_deskew=False` by default)
that never inspects `variant_id`, filename, dataset labels, or ground
truth -- only real image pixel content. **Verdict: harmful overall,
despite fully solving `employer.name`.** Not promoted. Documented
honestly per the brief's explicit instruction not to accept a rotated
improvement that causes meaningful regressions elsewhere.

## 1. Detection Method

`src/w2_pipeline/extraction/deskew.py`, using only Pillow (already a
declared project dependency -- no OpenCV/numpy dependency introduced):
a two-stage (coarse 1-degree, then fine 0.1-degree) grid search over
candidate rotation angles, scoring each candidate by how sharply banded
its horizontal ink-density profile is (real printed text/table rows
produce sharp horizontal ink bands when aligned; a misaligned page
produces a blurred profile). The angle producing the sharpest profile is
the correction: `image.rotate(result, expand=True)` brings the page into
alignment.

**An OCR-bounding-box row-slope method was tried first and rejected**,
with direct evidence, not merely a preference: reusing
`_group_observation_rows` (calibrated for narrow, pre-filtered zones like
Box c) across a whole two-column page chain-merged same-height text from
unrelated columns into false "rows" with wildly inconsistent slopes
(directly inspected: slopes from -0.058 to +0.074 across "rows" that
were actually unrelated field pairs like `'OMB No. 1545-0029' + 'FAST!
Use'`). The projection-profile method needs no OCR output at all (runs
before OCR, on the raw image) and was verified directly against real
diagnosed rotated documents, matching the OCR-box-slope method's rough
magnitude on the one case both could measure (~2-3 degrees).

Verified empirically, not assumed:
- Sign convention: rotating a synthetic image by `+5.0` degrees, the
  detector recovers `-5.0` (the exact inverse) -- confirmed both on a
  synthetic test image and against a real diagnosed rotated document.
- Real documents: `symage_900001-...-rotated.png` -> `-2.10` degrees;
  `symage_900033-...-rotated.png` -> `-2.00` degrees (see Section 2).

This targets small-angle *form* skew only (roughly +/-1 to +/-8 degrees,
per the brief), not 90/180/270-degree orientation -- a different,
unaddressed problem.

## 2. Establishing The Normal/Upright Distribution (Before Any Correction)

New script: `src/w2_pipeline/evaluation/run_skew_detection_scan.py`. Ran
the detector against all 600 real source images, uncorrected --
`variant_id` was attached to each row only *after* detection, for this
script's own offline analysis, exactly as the brief requires.

| Variant | n | Angle range | Mean \|angle\| | Would trigger (>0.75 deg) |
|---|---:|---|---:|---:|
| `external_clean_render` | 150 | exactly 0.000 for all 150 | 0.000 | 0/150 |
| `compressed_jpeg` | 150 | exactly 0.000 for all 150 | 0.000 | 0/150 |
| `blurred_png` | 150 | exactly 0.000 for all 150 | 0.000 | 0/150 |
| `rotated_png` | 150 | -2.100 to -2.000 | 2.088 | 150/150 |

**Complete, non-overlapping separation with zero natural noise in the
"normal" population** -- every clean/JPEG/blur document detects at
*exactly* 0.000 degrees (this synthetic dataset's renders are pixel-perfect
upright with no natural scan variance at all), and every rotated
document detects a consistent ~2.0-2.1 degrees.

**Threshold chosen: 0.75 degrees.** Given the zero-noise normal population,
literally any threshold `> 0` would perfectly separate this one dataset
-- exactly the pitfall the brief warned against picking a threshold for.
0.75 degrees was chosen instead for a substantive reason: it sits at
roughly 7.5x the detector's own fine-search resolution (0.1 degrees) and
a large margin below the real rotated population's 2.0-degree floor,
so it would not fire on plausible real-world scan jitter this synthetic
dataset happens not to exhibit, while still triggering on the actual
rotated population with a wide (1.25-degree) safety margin. Average
detection latency: **0.160 seconds/document** (measured directly across
all 600 images).

## 3. Real-Document Verification (Before The Full 600-Document Run)

Directly verified against real documents before committing to the full
benchmark, per the brief's own investigative discipline:

| Document | Field | Before correction | After correction | Ground truth |
|---|---|---|---|---|
| symage_900033 | `employer.name` | `Elan Consulting Corp 2861 Geneva Ponce De Leon Rd` | **`Elan Consulting Corp`** | `Elan Consulting Corp` |
| symage_900000 | `box_13.retirement_plan` | `True` | `True` (unchanged) | `False` |
| symage_900033 | `box_13.retirement_plan` | `True` | `True` (unchanged) | `False` |

`employer.name` genuinely fixed on the first real test. `box_13` was
**not** fixed -- inspected immediately rather than assumed away: the raw
ink-coverage ratio in the checkbox zone actually got *worse* after
correction (0.0916 uncorrected -> 0.1097 with `expand=True` / 0.1186
without expand, vs. a 0.09 threshold), and, suspiciously, nearly
*identical* across three different documents regardless of their real
answer -- strong evidence the zone is landing on a shared printed
structural element (a table border/gridline), not the variable checkbox
mark. Root cause: `RETIREMENT_PLAN_ZONE` was calibrated against the
*clean render's* specific canvas (2550x3300px); the raw `rotated_png`
variant's own canvas is already a different size (2664x3388px)
*independent of rotation angle*, and `expand=True`'s further canvas
growth (to 2782x3480px) shifts the zone's ratio-relative position again
-- restoring rotation alone does not restore the clean render's exact
canvas geometry the checkbox zone was calibrated against.

**This second finding -- that a single previously-clean document
(`symage_900001`, not one of the 4 known `employer.name` failures)
picked up 11 new field errors after correction -- triggered an immediate
stop-and-investigate before proceeding to the full run**, per this
project's standing discipline. See Section 5.

## 4. Full 600-Document Benchmark: Phase 8C.2 vs. Phase 8C.2 + Deskew

New script: `src/w2_pipeline/evaluation/run_pipeline_a_with_deskew.py`.
Identical PaddleOCR configuration, parser, checkbox logic, canonical
schema, 24 evaluated fields, and evaluator (`compare_w2_documents` with
each entry's own `evaluated_field_paths`) as Phase 8C.2 -- the only
variable is the new conditional-deskew preprocessing step.

| Metric | Phase 8C.2 (frozen) | Phase 8C.9 (+ deskew) |
|---|---:|---:|
| Full-pipeline field accuracy | **99.56%** (14,336/14,400) | **88.49%** (12,743/14,400) |
| `external_clean_render` | 100.0% | 100.0% (unchanged) |
| `compressed_jpeg` | 100.0% | 100.0% (unchanged) |
| `blurred_png` | 100.0% | 100.0% (unchanged) |
| `rotated_png` | 98.22% | **53.97%** (1,943/3,600) |

**Clean/JPEG/blur: perfectly preserved, exactly as required.** Zero
documents triggered correction in these 450 documents (matching Section
2's distribution exactly), so they are byte-for-byte the same pipeline
run as Phase 8C.2 for these variants.

**Rotated: catastrophic regression.** All 150 rotated documents
triggered correction (100% trigger rate, matching the measured
distribution). Every single one of the 150 corrected documents now has
at least one field error (0 of 150 are error-free, down from the vast
majority being error-free before), averaging **11.05 field errors per
document** out of 24 evaluated fields, with a maximum of 13.

### Per-Field Breakdown (Sampled 15 Rotated Documents, Confirmed Systemic)

| Field | Failures |
|---|---:|
| `employee.last_name` | 15/15 |
| `employee.ssn` | 15/15 |
| `employee.suffix` | 15/15 |
| `employer.ein` | 15/15 |
| `federal_wages_and_taxes.box_1` | 15/15 |
| `federal_wages_and_taxes.box_2` | 15/15 |
| `federal_wages_and_taxes.box_4` | 15/15 |
| `federal_wages_and_taxes.box_6` | 15/15 |
| `federal_wages_and_taxes.box_7` | 15/15 |
| `federal_wages_and_taxes.box_8` | 15/15 |
| `federal_wages_and_taxes.box_3` | 8/15 |
| `box_13.retirement_plan` | 7/15 (matches the pre-existing ~40% baseline rate) |

**This is systemic, not an isolated document's quirk.** Ten of the 24
evaluated fields fail on essentially every corrected document.

### Root Cause, Directly Diagnosed (Not Assumed)

Inspecting `symage_900001`'s actual post-correction OCR output: the raw
text is read *correctly* (`"1 Wages, tips, other compensation"` and
`"$114,858.00"` are both present, legible, and individually accurate).
The failure is **field-to-label misassignment**: several federal-box
values ended up shifted by one box-pair (the value that belongs to Box 1
was assigned to Box 3, Box 2's to Box 4, and so on), `employee.ssn` and
`employer.ein` came back `None` entirely, and `employee.suffix` picked
up bled-in label text (`"Suff."`). This is the same root cause class as
the checkbox failure in Section 3: the OCR full-page zone-based
fallbacks in `parser_2026.py` (calibrated against a specific
clean-render canvas geometry, and already separately tolerant of the
*uncorrected* rotated variant's own consistent ~2-degree tilt) are not
calibrated for the *corrected* image's different canvas
proportions/margins (from `expand=True`'s canvas growth on top of the
rotated variant's own already-different native canvas size). Restoring
rotation angle alone does not restore the exact canonical geometry these
zones expect.

### `employer.name`: A Complete, Confirmed Win

| | Phase 8C.2 (rotated only) | Phase 8C.9 + deskew (rotated only) |
|---|---:|---:|
| `employer.name` correct | 146/150 (97.33%) | **150/150 (100.0%)** |

**All 150 rotated documents' `employer.name` are correct after deskew --
including all 4 previously-known row-merge residuals.** Restoring
rotation genuinely and completely eliminates the row-merge defect
class, confirming the Phase 8C.1 diagnosis (a rotation-skew-dependent
row-grouping-tolerance defect) at the root-cause level, not just via a
downstream detection heuristic (Phase 8C.5/8C.6/8C.7/8C.8).

### `box_13.retirement_plan`: Confirmed Unchanged, Not Merely Similar

| | Phase 8C.2 | Phase 8C.9 + deskew |
|---|---:|---:|
| Correct (rotated only) | 90/150 (60.0%) | 90/150 (60.0%) |
| Failing document IDs | 60 documents | **the identical 60 documents** (verified by exact set comparison, zero symmetric difference) |

Deskew has **zero measurable effect** on the checkbox class, positive or
negative -- confirmed by identical failing-document-ID sets, not just a
coincidentally matching count.

## 5. Regression Investigation (Required Before Accepting Any Result)

Per the brief's explicit instruction ("If any previously-perfect
population regresses, inspect..."): the single-document finding in
Section 3 (`symage_900001` gaining 11 new field errors) was investigated
immediately, before the full 600-document run was even launched.
Diagnosis (Section 4, "Root Cause") ruled out:
- **Deskew triggering unnecessarily**: no -- `symage_900001-rotated.png`
  genuinely has ~2.1 degrees of real skew (confirmed via the same
  distribution scan that found 0.000 degrees for every clean/JPEG/blur
  document); the trigger was correct.
- **Interpolation degradation / clipping**: no -- the raw OCR text values
  themselves are read correctly and completely; nothing was clipped or
  garbled at the character level.
- **Angle-estimation noise**: no -- the estimated angle (-2.1 degrees) is
  consistent and matches the independently-measured rotated population's
  distribution exactly.

The actual cause -- calibrated-zone misalignment against a corrected
image whose canvas geometry differs from what those zones expect -- was
confirmed directly (Section 4) rather than left as a guess.

## 6. Performance

| | Value |
|---|---:|
| Skew detection latency (mean, all 600 docs) | 0.160 s |
| Average extraction duration, deskew pipeline (OCR + parse, all 600) | 1.759 s |
| Average extraction duration, Phase 8C.2 baseline (OCR + parse only) | ~1.23 s |
| Implied total latency delta | **+0.53 s/document average** (detection always-on, plus a corrected image adds negligible transform time; OCR itself still runs exactly once per document either way) |

The added latency is dominated by the always-on detection pass (0.16s),
not by the correction transform itself (fast) or a second OCR pass
(never needed -- detection runs on raw pixels before OCR, so exactly one
OCR pass occurs per document regardless of trigger status). Given the
accuracy outcome below, this cost is moot -- deskew is not recommended
regardless of its latency profile.

## 7. Decision: C. Harmful / Unstable (Overall) -- Despite A Genuine, Confirmed Win On `employer.name`

Per the brief's decision framework, this cannot be classified as a
"strong preprocessing fix" (option A) or even "useful but incomplete"
(option B), because it actively **regresses** a large previously-correct
field population -- exactly the disqualifying condition the brief named
explicitly ("Do NOT accept a rotated improvement that causes meaningful
regressions elsewhere"). The `employer.name` result on its own would
qualify as option A for that field specifically, but the same mechanism
that fixes it (restoring rotation) breaks ten other fields' calibrated
zone assumptions, and does nothing at all for the checkbox class this
phase was also asked to investigate.

**Conditional scan-deskew, as implemented here, should NOT become the
new preprocessing baseline.** Not promoted; `enable_conditional_deskew`
remains an explicit, off-by-default opt-in with no default-path callers.

**Is checkbox-specific remediation still required?** Yes, unchanged --
deskew provides no help for `box_13.retirement_plan` at all (identical
60/150 failures).

**Do the employer-name validators (Phase 8C.5/8C.6/8C.7/8C.8) remain
useful safety layers?** Yes, explicitly preserved and unmodified in this
phase, per the brief's instruction -- they remain the production
mechanism for catching this exact defect class without the extraction
regression this preprocessing approach introduces.

## What Would Be Needed To Make Deskew Viable (Not Attempted Here)

Not pursued in this phase (would be new scope, and risks the explicit
"do not tune parser/OCR/checkbox" constraint if done carelessly): a
genuine fix would need to normalize the *entire* page geometry back to
the clean render's exact canvas proportions (not just correct the
rotation angle) before OCR -- e.g. detecting the actual form content's
bounding box and rescaling/cropping to a canonical canvas size, rather
than a bare `rotate(angle, expand=True)`. That is a materially larger,
separately-scoped preprocessing redesign, not a small deskew addition.

## What Was Deliberately Not Done

- The two employer-name validation rules (Phase 8C.8) were not removed,
  modified, or bypassed.
- No OCR configuration, parser extraction decision, or checkbox
  detection logic was changed or tuned.
- Deskew was not promoted to a default-enabled behavior; it remains an
  explicit opt-in with no production caller.
- The frozen Phase 8B/8C.2/8C.3/8C.4/8C.5/8C.6/8C.7/8C.8 artifacts were
  not modified; this phase's artifacts are new, separately-named files.
- No attempt was made to "fix" the checkbox or federal-box zone
  misalignment by retuning their calibrated zones -- that would violate
  the explicit "do not tune checkbox/parser" constraint and was correctly
  out of scope.

## Verification

12 new tests in `tests/extraction/test_deskew.py`: upright-image
near-zero detection; skewed-image correct-magnitude detection; sign
convention (a synthetic image rotated by a known angle recovers the
exact inverse); trigger-threshold behavior at both sides of the
boundary; original-path reuse (byte-identical path object, no new file)
when no correction triggers; triggered correction produces a new,
non-clipped (canvas-expanded) file; deterministic repeated estimates;
idempotence (a corrected image, run through the detector again, finds
near-zero residual skew and does not trigger a second correction); and
two structural safeguards confirming neither `estimate_skew_angle_degrees`
nor `deskew_image_if_needed` accepts any `variant_id`/filename/ground-truth
parameter. Full suite: **489 tests passing (477 baseline + 12 new), zero
regressions.**
