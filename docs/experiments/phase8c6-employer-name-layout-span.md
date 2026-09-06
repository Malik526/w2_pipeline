# Phase 8C.6 - Employer Name Layout-Span Signal Experiment

Offline validation experiment, independent of Phase 8C.5's address-leak
heuristic: can pure spatial/geometry evidence -- with **zero** inspection
of the text's semantic content (no street numbers, no road-suffix words,
no ZIP patterns) -- detect the known `employer.name` row-merge residual?
Nothing here is wired into `w2_pipeline.validation`; this is evidence
only, and it was not combined with Phase 8C.5's signal in this phase.

No OCR was tuned, no parser/checkbox/routing logic was touched, and the
frozen Phase 8C.2 benchmark artifacts were not modified. Extraction was
re-run (deterministic PaddleOCR, same configuration Phase 8C.2/8C.4 used)
only because raw OCR bounding-box geometry -- not just the final
predicted string -- is required and was never saved by any prior phase.

## 1. Provenance: The Smallest Safe Way To Capture Geometry For The 4 Known Failures

Phase 8C.4's reverse-value-matcher (`field_confidence.py`) could not
automatically reconstruct the 4 known `employer.name` failures, because
their merged value (name + full street line) exceeds that matcher's
deliberately small, fixed observation-window cap. Per this phase's
explicit instruction, that cap was **not** silently raised.

Instead, `src/w2_pipeline/evaluation/employer_name_layout_signals.py`
takes a different, more principled approach specific to this one field:
it reuses `_observations_in_zone` and `_group_observation_rows` from
`w2_pipeline.extraction.parser_2026` -- **the exact same two functions
the production `employer.name` fallback itself calls** -- read-only, with
the exact same zone tuple `(0.04, 0.35, 0.25, 0.33)` copied from
`_apply_ocr_employer_layout_fallbacks`. Neither function was modified.
Confirmed directly against the real failing document `symage_900033`
before building anything further:

```text
zone observations: ["c Employer's name, address, and ZIP code",
                     'Elan Consulting Corp', '2861 Geneva Ponce De Leon Rd']
row 0: "c Employer's name, address, and ZIP code"   (n=1)
row 1: 'Elan Consulting Corp 2861 Geneva Ponce De Leon Rd'   (n=2)
```

Row 1's joined text is *exactly* the real predicted value -- because the
row-grouping merge is the real root cause (Phase 8C.1) this phase
measures the geometric footprint of, not an approximation of it. A
row-group is unbounded in size by construction (however many
observations the parser's own tolerance merged), so no window-size cap
was ever needed here, unlike Phase 8C.4's approach. Every one of the 4
known failures matched this way -- **0 unmatched cases anywhere in the
600-document run**, a strictly better provenance-coverage result than
Phase 8C.4's field-confidence matcher achieved for this same field.

This coupling (the hardcoded zone tuple must track
`_apply_ocr_employer_layout_fallbacks`'s own zone if it ever changes) is
documented directly in the module's docstring, not hidden.

## 2. Raw Layout Signals Measured

No semantic content is inspected anywhere in this module (verified by a
structural test that the module does not import Phase 8C.5's
`employer_name_heuristics`). For the matched row-group:

- `observation_count` -- how many OCR observations the row-group contains.
- `vertical_span_px` / `vertical_span_ratio` -- `y_max - y_min` across the
  row's observations, raw and normalized by page height.
- `zone_span_ratio` -- `vertical_span_ratio` expressed as a fraction of
  the calibrated employer-name zone's own height (`0.33 - 0.25 = 0.08`
  of page height) -- how much of the "expected single line" zone the
  matched content actually consumes.
- `max_center_y_gap_px` / `_ratio` -- the largest gap between consecutive
  observations' vertical centers within the row.
- `tight_sub_row_count` -- a secondary, read-only diagnostic: re-clusters
  the *same* row's observations with a small, fixed (not
  height-scaled) 15px tolerance, to estimate how many real physical
  print lines were likely merged, independent of whatever
  per-observation-height-scaled tolerance caused the actual over-merge in
  production. Purely measurement; changes nothing about what the parser
  decided.

New instrumented run script:
`src/w2_pipeline/evaluation/run_employer_name_layout_analysis.py`
(mirrors Phase 8C.4's `run_pipeline_a_confidence.py` pattern: not a
replacement benchmark, calls `ObservationAcquirer.acquire` then
`parse_w2_2026_observations` directly to retain the intermediate
`ObservationSet`). **Leakage boundary**: signals are computed from the
prediction and its own observations alone; ground truth is loaded and
compared only afterward, purely to label correctness.

Source: re-ran PaddleOCR GPU, same configuration as Phase 8C.2, on all
600 manifest documents.

Output artifacts:
```text
data/evaluation/results/phase8c6_employer_name_layout_span.json
data/evaluation/results/phase8c6_employer_name_layout_span_rows.jsonl
```

## 3. Correct vs. Incorrect: Raw Distributions

596 correct, 4 erroneous (the same 4 documents every prior Phase 8C
analysis identified: `symage_900033`, `symage_900045`, `symage_900082`,
`symage_900146`, all `rotated_png`). **All 600 matched** -- zero
unmatched cases in either group.

| Signal | Correct: min / median / mean / p95 / max | Incorrect (all 4 values) |
|---|---|---|
| `observation_count` | 1 / 1 / 1.0 / 1 / **1** | **2, 2, 2, 2** |
| `vertical_span_px` | 31 / 40 / 41.5 / 52 / **56** | **85, 85, 86, 87** |
| `vertical_span_ratio` | 0.0195 / 0.0251 / 0.0257 / 0.0311 / **0.0335** | **0.0508, 0.0508, 0.0514, 0.0520** |
| `zone_span_ratio` | 0.244 / 0.314 / 0.321 / 0.388 / **0.418** | **0.635, 0.635, 0.642, 0.650** |
| `max_center_y_gap_px` | 0 / 0 / 0.0 / 0 / **0** | **32, 33, 34.5, 34.5** |
| `tight_sub_row_count` | 1 / 1 / 1.0 / 1 / **1** | **2, 2, 2, 2** |

**This is complete, non-overlapping separation on every single signal.**
The correct-name distribution's maximum never approaches the
incorrect-case minimum on any of the six metrics -- `observation_count`
and `tight_sub_row_count` are simply always `1` for every one of the 596
correct predictions and always `2` for every one of the 4 incorrect
ones; `vertical_span_px`'s worst-case correct value (56) sits nowhere
near the best-case incorrect value (85), a 29px gap with no overlap.
**This was not assumed going in** -- the brief explicitly warned not to
assume this outcome, and the full 600-document measurement confirms it
directly.

## 4. Threshold Sweep

Each candidate tested independently, not combined (per the brief):

| Candidate | Threshold | TP | FP | FN | TN | Recall | Precision | False-review rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A: `vertical_span_px` | `> 50` | 4 | **66** | 0 | 530 | 100% | 5.7% | 11.07% |
| A: `vertical_span_px` | `> 60` / `70` / `80` | 4 | **0** | 0 | 596 | 100% | 100% | **0%** |
| B: `max_center_y_gap_px` | `> 5` through `> 25` | 4 | 0 | 0 | 596 | 100% | 100% | **0%** |
| **C: `observation_count`** | **`> 1`** | **4** | **0** | 0 | 596 | **100%** | **100%** | **0%** |
| D: `zone_span_ratio` | `> 0.42` through `> 0.55` | 4 | 0 | 0 | 596 | 100% | 100% | **0%** |
| E: `tight_sub_row_count` | `> 1` | 4 | 0 | 0 | 596 | 100% | 100% | **0%** |

Every candidate achieves perfect separation **except** an over-aggressive
absolute-pixel threshold on `vertical_span_px` (`> 50`), which sits
*below* the correct population's own natural maximum (56) -- see Section
5.

## 5. False-Positive Inspection

**Every candidate at a reasonable threshold: zero false positives.**
Only the deliberately-too-aggressive `vertical_span_px > 50` test
produced any (66, across 66 distinct correct documents, all
`rotated_png`, e.g. `symage_900004` / `"Bright Horizons Corp"` at 52px,
`symage_900149` / `"Pristine Green Technologies LLC"` at 54px).

**Cause, determined directly, not assumed**: these are **benign,
ordinary single-line names whose own natural OCR-detected line height
under rotation** (51-56px) happens to exceed the chosen threshold (50px)
-- not multiline merges, not fragmentation, not a provenance-matching
artifact, and not a real layout anomaly. Every one of these 66 rows has
`observation_count == 1` and `max_center_y_gap_px == 0`, structurally
identical in shape to every other correct row -- only the specific
absolute-pixel cutoff was placed carelessly, inside the correct
population's own natural range rather than in the (much larger) gap
between it and the incorrect population's minimum. This is a distinct,
fifth false-positive category beyond the four the brief listed
(multiline/long names, rotation effects, fragmentation, provenance
artifacts): **threshold miscalibration relative to natural single-line
variance** -- trivially avoidable by placing any absolute-pixel threshold
between 60 and 80 instead of at 50, or by preferring `observation_count`
(a natural integer boundary with no calibration risk at all) or
`zone_span_ratio` (resolution-independent) over an uncalibrated absolute
pixel cutoff.

## 6. Best Candidate

**`observation_count > 1`** -- the row-group that produced the predicted
`employer.name` contains more than one OCR observation.

| | |
|---|---:|
| 4 known errors caught | **4 / 4** |
| Correct names falsely flagged | **0 / 596** |
| Recall | **100.0%** |
| Precision | **100.0%** |
| False-review rate | **0.0%** |

Chosen over the other perfect-scoring candidates for being the simplest
possible condition with **no threshold-calibration risk whatsoever** --
it is a natural integer boundary (one observation vs. more than one), not
a magic pixel or ratio value that could drift with page resolution, DPI,
or a different rendering pipeline. `zone_span_ratio > 0.45` is the
strongest *resolution-independent, continuous* alternative if a
non-binary signal is ever preferred (e.g. for combining with other
continuous signals in a future phase).

## 7. Comparison With Phase 8C.5 (After Isolated Results Were Complete)

| | Phase 8C.5 (address-leak) | Phase 8C.6 (layout-span) |
|---|---:|---:|
| 4/4 caught | yes | yes |
| False positives / 596 | 0 | 0 |
| Recall | 100% | 100% |
| Precision | 100% | 100% |
| False-review rate | 0% | 0% |
| Requires English address vocabulary | yes | **no** |
| Requires a calibrated numeric threshold | no (word/pattern match) | no, for the recommended candidate (`observation_count > 1`) |

**Does layout detect the same 4?** Yes, exactly the same 4 documents,
with the same perfect recall/precision/false-review numbers as the
address-leak heuristic.

**Does layout catch anything the address heuristic conceptually would
not?** Yes, in principle, even though it happens not to matter on this
600-document set: layout is content-agnostic. It would still fire on a
hypothetical row-merge that pulled in a *non-address* neighboring line
(e.g. two adjacent unrelated printed labels merging under a different
rotation angle) -- exactly the case Phase 8C.5's own report flagged as
outside the address-leak heuristic's reach. Conversely, the address-leak
heuristic could in principle catch a value merged from a non-adjacent
zone that nonetheless contains address-shaped text pasted in some other
way (not a geometry anomaly) -- though no such case exists in this
dataset either.

**Does layout create more false positives?** No -- identical (zero) at
every reasonable threshold tested here. Layout's *bad* threshold choice
(`vertical_span_px > 50`) produced more false positives than anything
seen in Phase 8C.5, but that is a miscalibration artifact of one
poorly-chosen absolute-pixel cutoff, not evidence that the signal family
itself is noisier -- the recommended, calibration-free candidate
(`observation_count > 1`) has none.

**Is there evidence combining the two could add robustness?** Plausibly,
yes: the two signals are measuring genuinely independent evidence
(semantic content vs. spatial geometry) and neither's false-positive
mode overlaps with the other's on this dataset (there are none to
overlap). A combined signal could in principle raise confidence further
or extend coverage to defect shapes neither alone would catch (a
non-address merge that also isn't spatially anomalous seems unlikely to
exist, but was not tested). This is not run in this phase, per the
brief.

## Decision: A. Strong Standalone Signal

Per the brief's framework: layout-span evidence catches all known
errors, at zero false-review cost, using the recommended candidate. It
is at least as strong as Phase 8C.5's address-leak heuristic, and more
general (no assumption about employer-name vocabulary or language, and
no dependency on a calibrated numeric threshold).

**Caveats, matching the same honesty standard as Phase 8C.5**: evaluated
against only 4 positive examples -- a small sample, even though the
zero-overlap margin is large (a 29px gap on `vertical_span_px` alone).
It is scoped to the currently-known defect shape (two physical lines
merged into one row-group); it would not distinguish a row-merge from a
genuinely long, multi-word but single-line company name if one ever
rendered wide enough to visually wrap OCR-detection into two boxes for
an unrelated reason (not observed in this dataset, but not structurally
ruled out either). Not promoted to production validation in this phase.

**Is a combined Phase 8C.7 experiment justified?** Yes, tentatively: both
signal families independently achieve perfect separation on this
dataset, which is itself informative (this specific defect shape is
"easy" to detect from either angle), but a combined signal is the
natural next step to test for added robustness against defect shapes
neither alone was designed for, before any production promotion
decision.

## What Was Deliberately Not Done

- Phase 8C.5's address-leak heuristic was not used or combined with this
  signal (verified structurally: this phase's module does not import
  it).
- No production validation rule was added or changed.
- No OCR, parser, or checkbox logic was touched (the two reused parser
  functions are called exactly as production calls them, never modified).
- No layout-span cap or tolerance was silently raised to force a match --
  the zone/row-grouping reuse approach avoided needing to.
- The frozen Phase 8B/8C.2/8C.3/8C.4/8C.5 artifacts were not modified.

## Verification

12 new tests across
`tests/evaluation/test_employer_name_layout_signals.py` (10 tests:
single- and multi-observation span/gap/sub-row calculations using real
diagnosed geometry and tolerance math, page-height normalization,
unmatched/`None`/empty handling, and two structural safeguards -- no
import of Phase 8C.5's semantic heuristic module, and no new dependency
from the production parser back into this phase's evaluation code) and
`tests/evaluation/test_run_employer_name_layout_analysis.py` (2 tests:
end-to-end run on a small synthetic fixture, and limit/variant
filtering). Full suite: **443 tests passing (431 baseline + 12 new),
zero regressions.**
