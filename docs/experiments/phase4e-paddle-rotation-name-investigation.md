# Phase 4E — Rotated Employee-Name Label-Bleed Investigation

Investigation only. No fix implemented, no 150/600-document benchmark run,
no incumbent change. This corrects a prior mischaracterization: the bug is
**not** PaddleOCR-specific — see "Correction to prior documentation" below.

## Summary

Under the `rotated_png` variant, `employee.first_name` fails on **150/150**
documents for **both** PaddleOCR GPU and Tesseract, and
`employee.middle_initial` fails on 118/150 for both — identical failure
counts on both backends. The corruption is not introduced by either OCR
engine's text recognition. It is introduced by the shared,
backend-neutral employee-name OCR fallback in `parser_2026.py`
(`_apply_ocr_employee_layout_fallbacks` / `_zone_text`), whose fixed
ratio-based target zone — calibrated against clean-render geometry —
also captures the printed Box e field label ("Employee's first name and
initial") once rotation shifts the page's detected-text extent enough to
move the label's normalized position across the zone's `y0 = 0.505`
boundary. `_zone_text` then joins the label text and the name value into
one string, and the downstream name-splitting heuristic
(`split_first_name_and_initial`) fails silently on the result, dropping
the middle initial in the process.

## Representative examples

Three documents were traced end-to-end: `symage_900000` (first name only,
no middle initial), `symage_900001` (first name + middle initial "D"),
and `symage_900026` (accented name "Jesús" + middle initial "D", to rule
out an accent-handling explanation).

| Document | Expected | Predicted `first_name` | Predicted `middle_initial` |
| --- | --- | --- | --- |
| `symage_900000` | `Lori` | `Lori e Employee's first name and initial` | *(n/a — no ground-truth initial)* |
| `symage_900001` | `Steven` / `D` | `Steven D e Employee's first name and initial` | *(missing)* |
| `symage_900026` | `Jesús` / `D` | `Jesús D e Employee's first name and initial` | *(missing)* |

## Where the corruption first appears

### Step 1 — Raw PaddleOCR `predict()` output (before any adapter code runs)

Ran `PaddleOCR(...).predict()` directly on the rotated source images and
inspected `res["rec_texts"]`/`res["rec_boxes"]` — PaddleOCR's own
detection+recognition output, upstream of `PaddleOcrAdapter`. For
`symage_900000-...-p0_rotated.png` (2664×3388 true image, GPU inference):

```text
index 39: "e Employee's first name and initial"   bbox [197, 822, 657, 871]
index 46: "Lori"                                    bbox [186, 882, 257, 926]
```

These are **two separate, correctly-recognized entries** with distinct,
non-overlapping bounding boxes (label bottom `y1=871`, value top `y0=882`
— an 11px gap, no overlap). PaddleOCR's text detector did not merge the
label and the value into one region, and its recognizer read each
correctly (`"Lori"` alone, not `"Lori e Employee's..."`). **Paddle's raw
native output is already correct — this rules out root causes A (text
recognition) and B (text detection/bounding boxes).**

For `symage_900001-...-p0_rotated.png`, PaddleOCR recognized the name
value as a single merged unit, `"Steven D"` — this is normal,
expected PP-OCRv6 line-level recognition behavior (it groups visually
adjacent words on one text line into one recognition), not a defect; the
label, again, is a separate entry.

### Step 2 — Adapter conversion (`PaddleOcrAdapter.extract_image`)

`ocr_paddle.py` converts each `(text, box)` pair from `rec_texts`/
`rec_boxes` into one `TextObservation` with the box's four floats used
directly as `x0, y0, x1, y1` — no coordinate transform, no merging, no
reordering. Comparing the adapter's output `TextObservation`s to the raw
`rec_texts`/`rec_boxes` confirms a 1:1, unmodified passthrough. **This
rules out root cause C (adapter coordinate conversion) and D (observation
ordering) — the adapter is not implicated.**

### Step 3 — Zone-ratio computation and membership (`parser_2026.py`)

The employee-name OCR fallback (`_apply_ocr_employee_layout_fallbacks`)
extracts the name via `_zone_text(observations, (0.04, 0.28, 0.505, 0.550),
discard_tiny_artifacts=True)`. The zone ratio is checked against
`_layout_extent(observations)` — the maximum detected-text `x1`/`y1`
across *all* observations on the page (not the true image's pixel
dimensions).

Computed directly from the raw Paddle output on the same document:

| | Clean render | Rotated |
| --- | ---: | ---: |
| True image size (`PIL.Image.size`) | 2550×3300 | 2664×3388 |
| Detected-text extent (`_layout_extent`) | 2401×1591 | 2452×1674 |
| Label ("e Employee's...") `y` ratio | **0.4852** (outside zone) | **0.5060** (**inside zone**) |
| Name value `y` ratio | 0.5170 (inside zone) | 0.5394–0.5400 (inside zone) |

On the clean render, the label's normalized `y` position (`0.4852`) sits
safely below the zone's `y0 = 0.505` floor and is correctly excluded. On
the rotated image, the same label — now positioned differently on a
larger true canvas, and normalized against a detected-text extent that
grew by a different proportion — lands at `0.5060`, just **inside** the
zone. This numeric result was reproduced identically (same extent, same
`0.5060` label ratio to four decimal places) across four independent
documents (`symage_900000`, `900001`, `900002`, `900003`), confirming the
effect is driven by the fixed rotation transform applied uniformly to the
template, not by per-document content variance.

**`_zone_text` then does exactly what it is designed to do**: it collects
every observation whose center falls in the zone, sorts by `x0`, and
joins them with spaces. For `symage_900001`, the zone now contains two
observations — `"Steven D"` (`x0=189`) and `"e Employee's first name and
initial"` (`x0=197`) — joined in that order: `"Steven D e Employee's first
name and initial"`, an exact match to the observed corrupted prediction.
Neither observation is dropped by the existing junk-token filter
(`_clean_layout_token`): its exact-match denylist already includes a bare
`"e"` (evidence this filter was built with Tesseract's word-level
tokenization in mind, where the box-letter marker arrives as its own
isolated token), but PaddleOCR's line-level recognition merges `"e"` into
the full label sentence, so the denylist's exact-match check never fires.

**Root cause located: F (employee-name zone selection)**, driven by **H
(rotation normalization / coordinate-space assumption)** — the zone
boundary itself is correctly implemented and was correctly calibrated for
clean-render geometry, but the calibration silently breaks under rotation
because ratio-based zones normalized against *detected-text extent*
(not true image dimensions) are not rotation-invariant. E (word/line
reconstruction, i.e. `_group_observation_rows`) is not implicated — the
employee-name fallback does not use row grouping at all; it reads the
flat, zone-filtered observation list directly.

### Would normalizing against true image dimensions fix it?

No — checked directly. Using the *true* image height (3388px) instead of
detected-text extent (1674px) for the rotated document, both the label
(`y` ratio `0.25`) and the name value (`y` ratio `0.267`) fall *outside*
the existing zone (`0.505–0.550`), because every zone constant throughout
`parser_2026.py`'s OCR fallback system (name, EIN, all federal box zones)
was originally calibrated relative to detected-text extent, not true
pixel dimensions. Switching the normalization reference without
recalibrating every zone constant would break zone matching entirely,
not just for this field. This is the same detected-extent-vs-true-pixel
distinction already documented for the legacy OCR-token Box 13 fallback
zones (see `docs/experiments/pipeline-a-extraction-history.md`, Box 13
visual checkbox calibration notes) — the same class of instability,
independently rediscovered here for the employee-name zone.

## Why the middle initial disappears

`_apply_ocr_employee_layout_fallbacks` passes the zone-joined string to
`split_first_name_and_initial` (`contracts/employee_name.py`), which
splits on whitespace and checks only the **last** token:

```python
def _is_middle_initial(value: str) -> bool:
    token = value.rstrip(".")
    return len(token) == 1 and token.isalpha() and token.isupper()
```

For the corrupted string `"Steven D e Employee's first name and
initial"`, the whitespace-split parts are `["Steven", "D", "e",
"Employee's", "first", "name", "and", "initial"]`. The last part,
`"initial"`, is not a single uppercase letter, so `_is_middle_initial`
returns `False` and the function falls through to
`return " ".join(parts), None` — the entire string (including the
already-correct `"D"` in the middle) becomes `first_name`, and
`middle_initial` is `None`. This is not a separate bug: it is the direct,
mechanical consequence of the zone corruption above, using an
initial-detection heuristic that only ever looks at the final token — a
reasonable design for a clean two-or-three-word zone, but one with no
resilience to trailing junk tokens appended after the true initial.

## Rule in/out

| Cause | Verdict | Evidence |
| --- | --- | --- |
| A. Paddle text recognition | **Ruled out** | Raw `rec_texts` shows `"Lori"` recognized correctly, alone |
| B. Paddle text detection/bboxes | **Ruled out** | Label and value have distinct, non-overlapping, correctly-positioned boxes |
| C. Adapter coordinate conversion | **Ruled out** | `TextObservation` fields are an unmodified 1:1 passthrough of `rec_texts`/`rec_boxes` |
| D. Observation ordering | **Ruled out** | Corruption is zone membership, not order; order only determines join sequence (value-then-label, matching `x0` sort) |
| E. Word/line reconstruction | **Ruled out** | The employee-name fallback does not use `_group_observation_rows`; it reads the flat observation list |
| F. Employee-name zone selection | **Confirmed — primary mechanism** | Label's normalized `y` ratio crosses the zone's `0.505` floor only under rotation (`0.4852` clean vs. `0.5060` rotated) |
| G. Parser name splitting | **Confirmed — secondary, explains the missing initial** | Last-token-only heuristic silently fails once junk tokens trail the true initial |
| H. Rotation normalization / coordinate-space assumption | **Confirmed — root cause of F** | True image canvas grows under rotation (2550×3300 → 2664×3388) while zone ratios are normalized against detected-text extent, which grows by a different, uncorrelated proportion |

## Correction to prior documentation

Prior project-state.md / CHANGELOG entries (from the PaddleOCR GPU
600-document robustness rerun) characterized this as **"PaddleOCR GPU's
rotated-image `employee.first_name` complete failure (0/150)... a newly
discovered weakness with no Tesseract equivalent at that severity
(Tesseract's rotated `employee.first_name` is 53.67%)."** That 53.67%
figure was Tesseract's **aggregate across all four variants**
(clean+compressed+rotated+blurred), not the rotated-only figure. Recomputed
directly from `phase4e_tesseract_checkbox_vision_external_all_variants_600.json`,
filtering to `variant_id == "rotated_png"` only:

```text
Tesseract  rotated-only employee.first_name:    0/150   (0.0%)
PaddleOCR  rotated-only employee.first_name:    0/150   (0.0%)
Tesseract  rotated-only employee.middle_initial: 32/150 (21.33%)
PaddleOCR  rotated-only employee.middle_initial: 32/150 (21.33%)
```

**Both backends fail identically** — not a coincidence, but the expected
consequence of a bug in the shared, backend-neutral parser fallback that
both OCR backends' observations flow through equally. This is corrected
in `docs/project-state.md` as part of this investigation (see below); it
removes what was previously reported as a PaddleOCR-specific caveat in the
incumbent-promotion comparison.

## Generic to rotated documents, or specific to this template?

Both, in different senses:

- **The underlying mechanism (H) is generic**: any OCR fallback zone in
  `parser_2026.py` normalized against detected-text extent is a candidate
  for the same failure mode under any transformation (rotation, and
  potentially others) that changes the true-canvas-to-detected-extent
  ratio unevenly across the page. The Box 13 rotated checkbox weakness
  (documented separately, `RETIREMENT_PLAN_ZONE`, also calibrated only
  against clean renders) is plausibly a relative of this same class of
  bug, though it uses a different, true-image-relative calibration
  approach (`checkbox_vision.py`) and was not re-examined here.
- **The specific, total (150/150) severity is template- and
  rotation-angle-specific**: the identical `0.5060` label ratio and
  identical `2452×1674` detected extent recurring across every checked
  document confirm this stems from Symage's `rotated_png` variant
  applying one fixed rotation transform uniformly to one fixed W-2
  template layout. A different rotation angle, or a different form
  template with the Box e label positioned elsewhere relative to the
  zone boundary, could produce a different failure rate (partial rather
  than total) or no failure at all. The zone boundary crossing observed
  here is a knife-edge case for this exact template/angle combination,
  not evidence that any rotation of any document would fail this
  severely.

## Smallest evidence-supported fix recommendation

**Recommended**: add a targeted filter that recognizes and discards the
known, static, printed Box e label text
(`"Employee's first name and initial"`, and its common OCR variants —
e.g. Tesseract's curly-apostrophe `"Employee's"` vs. straight-quote
readings) wherever it appears inside a zone-filtered observation, whether
as a whole observation (PaddleOCR's line-level case) or via the existing
single-character junk check (already partially handles Tesseract's
word-level case). This is a substring/pattern match against a *known,
fixed piece of form template text* — not employee data — so it is
reliable regardless of which OCR backend produced it or how far rotation
shifted the zone boundary. It is backend-neutral (fixes both PaddleOCR
and Tesseract, which share the identical failure) and does not require
recalibrating any ratio-zone constant.

**Not recommended as the primary fix**: renormalizing zone ratios against
true image dimensions instead of detected-text extent. This is the more
architecturally "correct" long-term fix (and is already how
`checkbox_vision.py` operates), but it would require recalibrating every
existing zone constant across the OCR fallback system, not just the
employee-name zone, since all of them share the same detected-extent
convention today — a much larger, riskier change than this investigation
was scoped to recommend as "smallest."

**Complementary, defense-in-depth option**: harden
`split_first_name_and_initial`/`_is_middle_initial` to scan for a
single-uppercase-letter token anywhere near the start of the value
(immediately after the first name-like token) rather than only checking
the last whitespace-split token, so a trailing junk suffix — from this
bug, from unrelated OCR noise, or from the earlier-discovered PSM 11
supplemental duplication issue (`_zone_text` join-based fallback) — does
not silently erase an otherwise-recoverable middle initial. This does not
address root cause F/H and would not fully fix `first_name` on its own,
but would reduce the blast radius of any future zone-membership bug of
this shape.

None of these fixes were implemented as part of this investigation, per
its explicit scope.
