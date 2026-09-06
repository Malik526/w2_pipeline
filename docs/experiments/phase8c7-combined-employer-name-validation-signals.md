# Phase 8C.7 - Combined Employer-Name Validation Signal Experiment

Offline evaluation phase: combine Phase 8C.5's address-leak heuristic and
Phase 8C.6's layout-span signal for `employer.name` and determine whether
combining them improves robustness without adding review volume. Nothing
here is wired into `w2_pipeline.validation`; no OCR, parser, checkbox,
validation, or routing code was touched, and no frozen artifact from any
prior phase was modified. Scoped to `employer.name` only.

## Method

This phase deliberately does **not** rerun OCR or recompute either
underlying signal. It is pure combination-logic evaluation over the two
already-computed, already-frozen per-document row artifacts:

```text
data/evaluation/results/phase8c5_employer_name_address_leak_rows.jsonl   (Signal A: address-leak)
data/evaluation/results/phase8c6_employer_name_layout_span_rows.jsonl   (Signal B: layout-span)
```

New code:
- `src/w2_pipeline/evaluation/combined_employer_name_signals.py` -- pure
  combination logic (`classify_agreement`, `combine_or`, `combine_and`,
  confusion-matrix scoring). Every function takes only the two
  already-computed signal booleans; none accepts a ground-truth or
  expected-value parameter, verified directly
  (`test_signal_functions_take_only_booleans_no_ground_truth_leakage`).
- `src/w2_pipeline/evaluation/run_combined_employer_name_signal_analysis.py`
  -- joins the two frozen row artifacts by `(document_id, variant_id)`,
  cross-checks their key sets and `correct` labels for exact agreement
  (a real mismatch stops the analysis rather than silently proceeding --
  none occurred), and scores all four strategies.

**Signals used exactly as previously defined, unaltered**:
- **Signal A (address-leak)**: Phase 8C.5's best candidate,
  `contains_street_number AND contains_road_suffix` (expanded suffix
  list) -- `C_expanded_number_and_suffix`.
- **Signal B (layout-span)**: Phase 8C.6's best candidate,
  `observation_count > 1`.

**Leakage boundary**: both signals were computed independently in their
own prior phases without ground truth; this phase only joins their
already-computed boolean outputs and, separately, each artifact's own
already-computed `correct` label -- ground truth never enters any new
computation here.

Output artifacts:
```text
data/evaluation/results/phase8c7_combined_employer_name_signals.json
data/evaluation/results/phase8c7_combined_employer_name_signals_rows.jsonl
```

## Measured Results

All 600 documents, 596 correct / 4 erroneous (the same 4 documents every
prior Phase 8C analysis identified).

| Strategy | TP | FP | FN | TN | Recall | Precision | False-review rate | Specificity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Address alone | 4 | 0 | 0 | 596 | 100% | 100% | 0.0% | 100% |
| Layout alone | 4 | 0 | 0 | 596 | 100% | 100% | 0.0% | 100% |
| **OR** (either fires) | 4 | 0 | 0 | 596 | 100% | 100% | 0.0% | 100% |
| **AND** (both must fire) | 4 | 0 | 0 | 596 | 100% | 100% | 0.0% | 100% |

**Agreement-state counts across all 600 documents**:

| State | Count |
|---|---:|
| Both fire | **4** |
| Address only | **0** |
| Layout only | **0** |
| Neither fires | 596 |

**All 4 known failures fire both signals.** Verified directly, not
assumed -- `symage_900033`, `symage_900045`, `symage_900082`, and
`symage_900146` (all `rotated_png`) each show `address_signal=True,
layout_signal=True`.

## Disagreement Analysis

**Zero disagreements anywhere in the 600-document dataset.** No document
produced `address=True, layout=False` or `address=False, layout=True`.
Reported explicitly, per the brief: there is nothing to manually inspect
in this dataset, because it does not contain a case where the two
signals differ.

Since the real dataset produced no disagreement cases, adversarial/
synthetic fixtures were used to exercise and verify the combination
logic's behavior *in the case a disagreement did occur* --
`test_address_only_disagreement_case_is_a_false_positive_for_address_alone`,
`test_layout_only_disagreement_case_is_a_false_positive_for_layout_alone`,
`test_or_strategy_maximizes_recall_across_disagreeing_true_positives`,
and `test_and_strategy_minimizes_false_positives_across_disagreeing_correct_documents`
construct exactly these synthetic scenarios and confirm OR/AND behave as
expected (OR catches a disagreeing true positive either signal alone
would have caught; AND suppresses a disagreeing false positive either
signal alone would have raised). This is architectural validation of the
combination *logic*, not evidence that such a case exists in this
dataset.

## Important Caveat (Stated Directly, Per The Brief)

**This dataset has only 4 positive `employer.name` failures, and both
signals fire on the exact same 4 and nowhere else. OR and AND therefore
have identical benchmark metrics on this measurement** -- 100% recall,
100% precision, 0% false-review rate, indistinguishable from either
signal alone. This is exactly the scenario the brief anticipated and
warned against manufacturing a false performance gain from. **No
performance improvement over either individual signal is claimed or
exists in this measurement.** The value of this phase is architectural:
understanding whether two independent evidence channels agreeing
completely on a small known sample says anything useful about future
robustness -- it does not, by itself, improve today's benchmark score.

## Robustness Reasoning (Conceptual, Kept Separate From Measured Evidence)

**What both signals measurably catch (evidence, not hypothesis)**: the
one defect shape present in this dataset -- `employer.name` merged with
an immediately-following street-address line under large rotation skew.
Both catch all 4 instances; neither has any measured advantage over the
other here.

**What only the semantic (address-leak) signal could plausibly catch**
(hypothetical, not observed in this dataset): a merge or corruption that
introduces address-shaped text into `employer.name` through some
mechanism *other* than a spatial multi-observation merge -- e.g. a
single OCR observation that itself contains garbled or concatenated
address text without a detectable geometric anomaly (an OCR engine that
merges text within one bounding box rather than across two). Layout's
`observation_count` signal would see one observation and stay silent;
address-leak inspects the text content regardless of how many
observations produced it.

**What only the layout (geometry) signal could plausibly catch**
(hypothetical, not observed in this dataset): any multi-observation
row-merge whose merged-in content is *not* address-shaped -- a
non-English employer name merged with an unrelated neighboring printed
label, a merge with a second company-identifier line, or any future
row-grouping defect that pulls in text with no street number or road
suffix at all. Address-leak's vocabulary-based rule would never fire on
non-address text; layout's `observation_count > 1` is content-agnostic
and would still catch the spatial anomaly.

**Kept explicitly separate from the measured section above**: none of
these hypothetical cases were observed or tested against real data in
this phase. They are stated as reasoning about *why* the signals are
architecturally independent (one inspects content, the other inspects
geometry), not as additional measured coverage.

## Production Decision Analysis

**Recommendation: C. Tiered policy**, as a forward-looking design
recommendation -- not implemented in this phase.

Reasoning, weighing the four factors the brief specifies:

- **Measured recall/false-review rate**: identical (100%/0%) for every
  strategy tested, so measured performance alone does not distinguish
  them on this dataset.
- **Likely robustness to future defect shapes**: this is where the
  strategies diverge conceptually. An OR-style tiered signal ("either
  fires -> flag for review, both fire -> higher-priority/higher-confidence
  review") preserves each signal's independent detection reach (Section
  "Robustness Reasoning") while still letting a document where *both*
  independent evidence channels agree be treated with more confidence
  than one where only a single, unconfirmed channel fired. A strict AND
  policy would silently lose whichever hypothetical defect shape only one
  signal can see, the moment such a case actually occurs -- underselling
  the two signals' complementary design even though it scores identically
  today.
- **Implementation complexity**: low for either OR or AND (two boolean
  checks); a tiered policy is only marginally more complex (the same two
  booleans, routed to two priority buckets rather than one).
- **Not choosing "two is better than one" reflexively**: per the brief's
  explicit instruction, this recommendation is not "because both signals
  passed, use both" -- it is because the *agreement state itself* (both
  vs. one vs. neither) is additional, free information a single combined
  boolean would discard, and preserving it costs nothing in either
  implementation complexity or (per the measured results) detection
  performance on this dataset.

**D (layout only) and E (semantic only) are not recommended**: both
signals are independently perfect on the only evidence available: there
is no measured basis in this phase to discard either one, and doing so
would give up the complementary reach reasoned about above for no
measured benefit.

**A (plain OR) and B (plain AND) are reasonable simpler fallbacks** if a
tiered review-priority mechanism does not exist in a future validation
architecture; OR is the safer of the two (never drops a
hypothetical single-signal detection), AND is safer only if false-review
volume becomes a binding constraint that current evidence does not show.

## Next Decision

**Is this evidence sufficient to promote an employer-name validation rule
later?** Partially. Both signals are individually strong per their own
phases' evidence (Phase 8C.5, Phase 8C.6), and this phase confirms
combining them costs nothing and preserves complementary reach. It does
**not**, on its own, resolve the open caveat both prior phases already
raised: all evidence so far rests on 4 positive examples from one
synthetic dataset and one specific defect shape.

**Is broader real-world/adversarial employer-name testing still needed
before promotion?** Yes, unchanged from Phase 8C.5/8C.6's own
conclusions. This phase adds architectural confidence (independent
signals, zero measured conflict, low combination complexity) but not
additional positive examples or defect-shape diversity -- a real-world or
adversarially-constructed employer-name corpus, ideally including at
least one genuine disagreement case, remains the natural prerequisite
before any production promotion decision.

## What Was Deliberately Not Done

- No production validation rule or routing logic was added or changed.
- Neither underlying signal (Phase 8C.5's address-leak heuristic, Phase
  8C.6's layout-span signal) was altered before or during combination
  testing.
- No performance improvement was claimed where the measured evidence
  shows none (OR/AND are identical to each other and to either signal
  alone on this dataset -- stated directly, not obscured).
- This phase was not expanded to any W-2 field other than `employer.name`.
- The frozen Phase 8B/8C.2/8C.3/8C.4/8C.5/8C.6 artifacts were not
  modified; this phase's own artifacts are new, separately-named files.

## Verification

17 new tests across
`tests/evaluation/test_combined_employer_name_signals.py` (12 tests:
all four agreement-state classifications, OR/AND truth tables,
confusion-matrix math on both real-shaped and adversarial
synthetic/disagreement fixtures constructed specifically to exercise
cases the real 600-document dataset does not contain, and two structural
safeguards -- no ground-truth parameter on any combination function, no
validation-package dependency) and
`tests/evaluation/test_run_combined_employer_name_signal_analysis.py`
(5 tests: row-joining by `(document_id, variant_id)`, rejection of
mismatched document sets or disagreeing correctness labels between the
two source artifacts, end-to-end combined-analysis correctness, and
explicit no-disagreements reporting). Full suite: **460 tests passing
(443 baseline + 17 new), zero regressions.**
