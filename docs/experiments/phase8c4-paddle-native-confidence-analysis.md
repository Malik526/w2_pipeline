# Phase 8C.4 - Propagate And Evaluate Native PaddleOCR Confidence

This is an instrumentation and evidence phase: does PaddleOCR's native
per-observation recognition confidence predict the extraction errors that
remain after Phase 8C.1/8C.2 remediation? No extraction decision, parser
behavior, validation rule, or routing logic was changed. OCR was not
tuned. No combined/derived confidence score was invented -- only the
engine's own real, already-emitted confidence values are used, exactly as
emitted (PaddleOCR) or linearly rescaled to the same 0..1 units
(Tesseract).

## 1. What PaddleOCR Actually Returns (Inspected, Not Assumed)

Ran the real installed `paddleocr==3.7.0` `PaddleOCR.predict()` directly
(bypassing the adapter) against a real document and printed the raw
result payload's keys:

```text
['input_path', 'page_index', 'model_settings', 'dt_polys', 'text_det_params',
 'text_type', 'textline_orientation_angles', 'text_rec_score_thresh',
 'return_word_box', 'rec_texts', 'rec_scores', 'rec_polys', 'rec_boxes']
```

`rec_scores` exists, is a `list[float]` parallel to `rec_texts`/`rec_boxes`
(same length, same order -- confirmed: 78/78 on the sample document), and
is already natively 0..1 (sample values: `0.9994`, `0.9997`, `0.9147`,
...). This is the real recognition confidence for each detected text box,
not a fabricated or inferred value.

Tesseract's TSV output was also inspected directly (not assumed from
documentation): its `conf` column is native **0..100** (sample values:
`92`, `89`, `96`; structural, non-word rows carry `-1` and were already
filtered before this phase, unrelated to this change).

## 2. Implementation

### Where confidence originates and how it is stored

`src/w2_pipeline/extraction/models.py`: `TextObservation` gained one new
optional field, `ocr_confidence: float | None`, constrained to `None` or
`[0.0, 1.0]` via Pydantic `ge`/`le` (verified directly: `None` passes,
`0.0`/`0.5`/`1.0` pass, `-0.01`/`1.01`/`100.0` raise `ValidationError`).
Default `None` -- fully backward compatible, and native-PDF-text
observations always leave it `None` (there is no OCR recognition step to
have a confidence for).

- `src/w2_pipeline/extraction/ocr_paddle.py`: `PaddleOcrAdapter.extract_image`
  now reads `rec_scores` alongside `rec_texts`/`rec_boxes` and attaches
  each score to its observation **by index**, not by `zip`, specifically
  so a missing or short `rec_scores` list can never drop or reorder a
  text observation -- confidence is best-effort metadata, never a
  condition for whether an observation exists. Values are stored exactly
  as PaddleOCR emits them.
- `src/w2_pipeline/extraction/ocr.py`: `parse_tesseract_tsv` now stores
  `conf / 100.0` as `ocr_confidence` -- a linear rescale of Tesseract's
  own real native value (never a fabricated one) so both backends share
  one comparable 0..1 scale. The existing `conf < 0` structural-row filter
  is unaffected (runs first, on the raw un-rescaled value).

**No parser decision depends on the new field.** Verified two ways: (a)
by construction -- no line in `parser_2026.py` was touched; (b) empirically,
by a new test (`test_parser_output_unchanged_when_observations_carry_ocr_confidence`)
that parses the identical realistic full-page fixture twice, once with
every observation's `ocr_confidence` set to `0.42` and once left `None`,
and asserts the resulting `W2Document` and warnings are byte-identical.

### How field-level confidence is derived

This is deliberately **evaluation-side, not production-side**. Threading
real-time provenance through every helper in `parser_2026.py`
(`_value_after_label`, `_first_row_text_in_zone`, `_first_regex_text_in_zone`,
the federal-box line parser, ...) would touch a large surface of a
parser Phase 8C.2 declared frozen, for a measurement-only question. New
module: `src/w2_pipeline/evaluation/field_confidence.py`. Given the
already-produced `W2Document` and the same `list[TextObservation]` the
parser saw, for each of a fixed set of 12 evaluated OCR-backed fields
(`employee.first_name`/`middle_initial`/`last_name`/`ssn`,
`employer.ein`/`name`, federal Boxes 1-6 -- `box_13.retirement_plan` is
deliberately excluded, see Section 8), it re-derives *which* observation(s)
plausibly produced that field's already-decided value:

1. Observations are sorted the same way the parser sorts them:
   `(page, bbox.y0, bbox.x0)`.
2. Every contiguous run of 1-4 observations is tried, smallest first, in
   two phases: first every run's *whole* joined text (space-separated for
   text fields, concatenated for money) is checked for an **exact**
   match against the field's value; only if no exact match exists
   anywhere is a looser **token-membership** fallback tried (the field's
   value appears as one whitespace-delimited token inside a run's joined
   text). Money-field comparison parses both sides as `Decimal` so
   `"$28,425.27"` and `Decimal("28425.27")` compare equal regardless of
   formatting.
3. If nothing matches, the field is reported unmatched -- no confidence
   value is ever fabricated for it.

**A real collision was found and fixed during this phase, not assumed
away**: on `symage_900001-...-rotated.png`, a Box 12 code letter `"D"`
sits far above the actual employee-name row and is an *exact*
single-observation match for `employee.middle_initial` (also `"D"`) --
without correction this would have won over the correct answer, which
PaddleOCR had merged into one observation, `"Steven D"` (confirmed by
direct inspection: the stray `"D"`'s row-center is 43.5px from
`last_name`'s row-center; the real `"Steven D"` is only 17.5px away).
Fix: `find_all_field_confidence_matches` anchors the
first-name/middle-initial/last-name search to a row-band around the
`last_name` match (chosen as the anchor for being the least
ambiguous/most distinctive of the three), which is a heuristic, not a
guarantee -- see "Known Limitations" below. A focused regression test
(`test_middle_initial_does_not_collide_with_unrelated_distant_single_letter`)
reproduces this exact real geometry.

`box_13.retirement_plan` (checkbox visual detector, not OCR text) is
excluded from `CONFIDENCE_ANALYSIS_FIELD_PATHS` entirely -- its
confidence signal is a separate, later concern (pixel-coverage margin,
skew, geometry quality), not conflated with OCR text confidence here.

### The fresh instrumented run

`src/w2_pipeline/evaluation/run_pipeline_a_confidence.py` is a new,
separate script -- **not** a replacement extraction benchmark and does
not touch `run_pipeline_a.py`, `PredictionRecord`, or any frozen artifact.
For each of the 600 manifest documents it calls
`ObservationAcquirer.acquire` then `parse_w2_2026_observations` directly
(the same two calls `PipelineAExtractor.extract_ingested` makes
internally, inlined here only so the intermediate, now
confidence-bearing `ObservationSet` can be kept), scores the result with
`compare_w2_documents` using the manifest's own `evaluated_field_paths`
(identical methodology to Phase 8C.2), and additionally runs
`find_all_field_confidence_matches`. PaddleOCR GPU, identical
configuration to Phase 8C.2.

## 3. Extraction Stability Check (Required Before Any Confidence Analysis)

| | Phase 8C.2 (frozen) | Phase 8C.4 (this run) |
|---|---:|---:|
| Documents | 600 | 600 |
| Failed documents | 0 | 0 |
| Total fields (24-field scope) | 14,400 | 14,400 |
| Correct fields | 14,336 | **14,336** |
| Field accuracy | 99.5556% | **99.5556%** |

**Bit-identical.** PaddleOCR is deterministic for a fixed input and
configuration, and this confirms it empirically rather than assuming it
-- no investigation was needed before proceeding to confidence analysis.

## 4. Per-Field Confidence: Correct vs. Incorrect

Source: `data/evaluation/results/phase8c4_paddle_confidence_rows.jsonl`
(600 rows, one per document, `--no-rows` summary in
`phase8c4_paddle_confidence_600.json`).

| Field | Correct: count / mean / median / min / p5 | Incorrect: count |
|---|---|---:|
| employee.first_name | 600 / 0.9973 / 0.99988 / 0.9352 / 0.9773 | 0 |
| employee.middle_initial | 472 / 0.9967 / 0.99980 / 0.9352 / 0.9694 | 0 |
| employee.last_name | 600 / 0.9994 / 0.99999 / 0.9015 / 0.9998 | 0 |
| employee.ssn | 600 / 0.9999 / 0.99999 / 0.9699 / 0.9999 | 0 |
| employer.ein | 600 / 0.9996 / 0.99999 / 0.9562 / 0.9999 | 0 |
| **employer.name** | **596** / 0.9980 / 0.99996 / 0.9691 / 0.9863 | **4 (see Section 5)** |
| box_1 wages | 600 / 0.9998 / 0.99998 / 0.9577 / 0.9999 | 0 |
| box_2 fed tax withheld | 600 / 0.9998 / 0.99998 / 0.9307 / 0.9999 | 0 |
| box_3 SS wages | 600 / 0.9998 / 0.99998 / 0.9562 / 0.9999 | 0 |
| box_4 SS tax withheld | 600 / 0.9999 / 0.99998 / 0.9756 / 0.9999 | 0 |
| box_5 Medicare wages | 600 / 0.9998 / 0.99998 / 0.9562 / 0.9999 | 0 |
| box_6 Medicare tax | 600 / 0.9999 / 0.99999 / 0.9900 / 0.9999 | 0 |

`employee.middle_initial`'s count is 472/600 because 128 documents
legitimately have no middle initial at all (confirmed directly against
ground truth, e.g. `symage_900006`: `"middle_initial": null`) -- reported
as "no value to search for," not a provenance-matching failure.

**The central, unavoidable fact this table shows: 11 of the 12 fields
have zero incorrect examples on this 600-document run.** PaddleOCR's
text recognition itself made no mistakes on any of these fields at this
scale (Phase 8C.2 already established this: only `employer.name` and the
separately-tracked `box_13.retirement_plan` have any failures at all). A
"confidence distinguishes correct from incorrect" comparison is
structurally impossible for 11 of 12 fields -- there is no incorrect
population to compare against. This is itself a finding, not a gap in
this analysis: it means, on this dataset, PaddleOCR recognition
confidence has never yet had an opportunity to demonstrate predictive
value, because recognition itself has not yet failed.

## 5. The `employer.name` Residual: Inspected Directly, Not Assumed

The reverse-value-matcher could not find contributing observations for
the 4 known row-merge failures automatically (the merged
name-plus-address value spans more observations than the matcher's
4-observation window, by design a conservative cap -- see Limitations).
Per the brief's explicit instruction, these 4 were inspected directly
against real PaddleOCR output instead of leaving the question
unanswered:

| Document | `employer.name` observation | Confidence | Merged-in address observation | Confidence |
|---|---|---:|---|---:|
| symage_900033 | `"Elan Consulting Corp"` | **1.0000** | `"2861 Geneva Ponce De Leon Rd"` | 0.9804 |
| symage_900045 | `"Bespoke Designs LLC"` | **1.0000** | `"6878 Normandy Tullahoma Rd"` | 0.9961 |
| symage_900082 | `"FutureReady Services"` | **1.0000** | `"875 Francis Case Memorial Brg"` | 1.0000 |
| symage_900146 | `"Global Insights Corp"` | **1.0000** | `"4522 Eastern Transportation Corridor"` | 0.9965 |

**Direct answer to the brief's key question**: Paddle remains highly
confident -- **because it correctly recognized the wrongly-grouped
text.** Both the true employer name and the address line the parser
mistakenly merged into it were read at or near perfect confidence in
every one of the 4 cases. This is not an OCR recognition failure at any
confidence level; it is purely the already-diagnosed (Phase 8C.1)
parser/layout row-merge defect, and native OCR confidence provides
**zero signal** to distinguish it from a correct extraction. This
directly parallels Phase 8C.3's finding that the Phase 6 structural
validator is equally blind to this same defect class, for the same root
reason: the produced value is well-formed, plausible, and (in this case)
backed by genuinely high-confidence OCR text.

## 6. Document-Level Threshold Analysis (Exploratory Only)

Document-level signal: minimum (and, for comparison, mean) OCR confidence
across the same 12 fields, per document. Erroneous = the document has an
`employer.name` mismatch (the only OCR-text-recognition-eligible error
class in this run; `box_13.retirement_plan` is excluded per Section 8).

**Minimum-confidence threshold sweep:**

| Threshold | Erroneous flagged | Recall | Correct flagged | False-review rate | Precision |
|---|---:|---:|---:|---:|---:|
| < 0.999 | 1/4 | 25.0% | 236/596 | 39.6% | 0.42% |
| < 0.995 | 0/4 | 0.0% | 138/596 | 23.2% | 0.0% |
| < 0.99 | 0/4 | 0.0% | 112/596 | 18.8% | 0.0% |
| < 0.95 | 0/4 | 0.0% | 11/596 | 1.8% | 0.0% |
| < 0.90 | 0/4 | 0.0% | 0/596 | 0.0% | undefined |
| < 0.80 | 0/4 | 0.0% | 0/596 | 0.0% | undefined |

**Mean-confidence threshold sweep:** strictly worse -- 0% recall at
*every* one of the same six thresholds (erroneous documents' mean
confidence across the 12 fields is 0.9997-1.0000 in all 4 cases, so no
practical mean threshold catches them without flagging nearly the entire
correct population first).

Two of the four erroneous documents (`symage_900033`, `symage_900045`)
have a minimum confidence of exactly **1.0000** across all 12 fields --
no threshold below 1.0 could ever flag them. The best achievable point on
this sweep, `< 0.999`, catches only 1 of 4 errors while incorrectly
flagging 236 of 596 correct documents (a 0.42% precision review queue).
Every stricter, more "reasonable" threshold catches zero errors while
still generating real false-review volume.

## Results Summary (Return-Block Answers)

**Whether extraction output remained stable**: yes, bit-identical to
Phase 8C.2 (14,336/14,400, verified before any confidence analysis).

**Confidence distribution on correct fields**: extremely high and tight
for all 12 fields -- medians 0.9998-1.0000, p5 typically above 0.97,
worst-case single observation minimums 0.90-0.99 (still high).

**Confidence distribution on incorrect fields**: only `employer.name` has
any incorrect examples (4/600); their confidence is 0.98-1.0000, several
points *within* the correct-field distribution's own p5-p25 range, not
below it. Incorrect and correct confidence distributions are not
meaningfully separable for this defect class.

**`employer.name` residual confidence behavior**: high confidence,
because the OCR recognition was genuinely correct -- the defect is purely
downstream parser row-merging, not recognition, so confidence carries no
signal about it (Section 5).

**Best exploratory thresholds and their recall/false-review tradeoffs**:
none are good. The best point found (min-confidence `< 0.999`) trades 25%
recall for a 39.6% false-review rate and 0.42% precision -- not a usable
operating point. Every other threshold tested is strictly worse (0%
recall).

**Whether native OCR confidence appears genuinely useful for routing**:
**no, not on this evidence.** For 11 of 12 fields there is no incorrect
population to even test against (PaddleOCR made zero recognition errors
on them at this scale). For the one field with real errors, confidence is
indistinguishable between correct and incorrect predictions because the
errors are not recognition errors. This is a clean negative result, not
an inconclusive one.

## Limitations

- **Reverse-matching is a heuristic, not true provenance.** It re-derives
  "which observation(s) plausibly produced this value" after the fact by
  exact/token-membership text matching, not by recording what the parser
  actually consulted in real time. A collision was found and fixed for
  the employee-name cluster (Section 2); other collision classes may
  exist for fields not exercised in this analysis and would not
  necessarily be caught by the same row-band heuristic.
- **The `_MAX_RUN_LENGTH = 4` window cap intentionally does not chase
  arbitrarily long merged values.** This is exactly why the 4
  `employer.name` failures were unmatched automatically -- their merged
  value (name + full street address, 6+ words) exceeds the cap. Rather
  than raise the cap generically (which would raise the false-positive
  risk for every other field), Section 5 investigated those 4 directly
  against real OCR output instead of leaving the question unanswered.
- **This measures PaddleOCR only, on one 600-document dataset where
  recognition itself essentially never fails.** It says nothing about
  whether confidence would be predictive on a harder dataset (heavier
  degradation, handwriting, non-English) where genuine recognition
  errors occur, or for Tesseract (whose confidence is populated and
  range-validated by this phase's model/adapter changes, but was not
  run through this same 600-document analysis).
- **`employee.middle_initial`'s 128 "unmatched" documents are a
  different thing from a matching failure** -- they are legitimately
  blank fields (verified against ground truth), correctly reported as
  "no value" rather than "value present but no source found."
- **`box_13.retirement_plan` is entirely excluded**, per the brief: it is
  produced by a separate pixel-based checkbox detector, not OCR text
  recognition, and mixing its (nonexistent) OCR confidence into this
  analysis would misrepresent both systems. Its own confidence signal
  (pixel-coverage margin, skew, geometry quality) is future, separate
  work.
- No combined/derived confidence score was created, and none is proposed
  here as a result -- the evidence in Section 6 argues against inventing
  one from native confidence alone before a genuine recognition-error
  population exists to validate it against.

## What Was Deliberately Not Done

- No parser, validation, or routing behavior was changed.
- No OCR configuration was tuned.
- No combined 0-100 "final confidence score" was invented.
- No new validation rule or routing threshold was promoted to production;
  the threshold sweep in Section 6 is exploratory evidence only.
- The frozen Phase 8B/8C.2/8C.3 artifacts were not modified.

## Verification

26 new/modified tests across
`tests/extraction/test_observation_models.py`,
`tests/extraction/test_ocr.py`, `tests/extraction/test_ocr_paddle.py`,
`tests/extraction/test_parser_2026.py`, and the new
`tests/evaluation/test_field_confidence.py`, covering: confidence range
validation (accepts `None` and `[0,1]`, rejects outside it); Tesseract's
0..100 -> 0..1 rescale and structural-row exclusion unaffected; Paddle's
index-based (never `zip`-based) score attachment surviving a missing or
short `rec_scores` list without dropping/reordering observations; parser
output byte-identical with and without confidence metadata present;
exact and token-membership field-value matching including money-field
formatting robustness; the real Box-12-code-letter collision and its
row-band-anchored fix; missing-value and unmatched-value handling
(neither fabricates a confidence); and full-field-set coverage. Full
suite: **405 tests passing (379 baseline + 26 new), zero regressions.**
