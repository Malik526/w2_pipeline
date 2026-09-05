# Phase 8 - Validator Effectiveness Analysis

Answers one question the Phase 6/7 work left open: when Phase 6's
deterministic validator has no ground truth to check against (as in real
production use), how well does it actually catch real extraction errors?
This is an evaluation-side analysis only -- it does not change the shipped
`validate_w2_document` behavior.

## Method

Tool: `src/w2_pipeline/evaluation/validator_effectiveness.py`
(`python -m w2_pipeline.evaluation.validator_effectiveness <result.json> <manifest.jsonl> [--variant-id ...]`).

No OCR or VLM inference was re-run. Two already-committed Pipeline A
benchmark result artifacts were reused as-is:

```text
data/evaluation/results/phase4e_tesseract_capital_e_fix_rotated_150.json   (150 docs, rotated_png)
data/evaluation/results/phase4e_tesseract_checkbox_vision_external_all_variants_600.json (--variant-id blurred_png, 150 docs)
```

Neither artifact stores the full predicted `W2Document` -- only
field-level failures. Since the evaluator only ever records a failure
where `predicted != expected`, every field path *not* mentioned in a
document's `field_failures` is, by construction, exactly equal to ground
truth. This tool exploits that: it takes each document's real ground
truth, overlays exactly the recorded failures back onto it, and the
result is the real historical prediction, field-for-field, with zero
inference re-run.

**Ordering (the leakage boundary this analysis has to respect):**

```text
reconstructed PREDICTED document
    -> validate_w2_document()      <- ground truth never passed in here
    -> accepted / needs_review
    -> THEN compared against ground truth to label "was this actually wrong?"
```

`tests/evaluation/test_validator_effectiveness.py::test_validator_only_ever_receives_the_reconstructed_prediction_not_ground_truth`
enforces this structurally (spies on the validator call and asserts it
never receives the ground-truth object where the two differ).

## The `employer.name` Confound (Immediately Reproduced)

The very first run of this analysis reproduced the Phase 6B finding at
scale: **every one of the 150 documents** -- correct predictions included
-- tripped `required_field_missing` on `employer.name`, because Symage
ground truth has that field `null` for every record (see
`docs/experiments/phase6b-employer-name-investigation.md`). Raw numbers
before accounting for this: `false_review_rate = 1.0`,
`automatic_acceptance_rate = 0.0` on both datasets below -- not a
meaningful measurement, just this one already-understood gap dominating
everything. Both result files below report **raw** (unadjusted) and
**adjusted** (excluding only `employer.name`'s `required_field_missing`
issue, nothing else) numbers side by side, so the confound is visible
rather than hidden. This is the clearest possible illustration of why
Phase 6 production validation matters even with a "complete" benchmark:
the benchmark's own field coverage gap would have been invisible without
it, and is now directly measurable.

## Results

```text
data/evaluation/results/phase8_validator_effectiveness_rotated_150.json
data/evaluation/results/phase8_validator_effectiveness_blurred_150.json
```

**Rotated variant** (150 documents, 76 with at least one real error --
predominantly a `box_13.retirement_plan` boolean flip on 60 documents,
plus a handful of accent-recognition name misreads):

| Metric | Adjusted |
|---|---:|
| Erroneous documents | 76 |
| Correct documents | 74 |
| Error-detection recall | **9.2%** (7/76 caught) |
| False-review rate | **0.0%** (0/74 wrongly flagged) |
| Automatic-acceptance rate | 95.3% |

**Blurred variant** (150 documents, 109 with at least one real error --
predominantly missing/garbled SSN, EIN, names, and money fields under
heavy image degradation):

| Metric | Adjusted |
|---|---:|
| Erroneous documents | 109 |
| Correct documents | 41 |
| Error-detection recall | **88.1%** (96/109 caught) |
| False-review rate | **0.0%** (0/41 wrongly flagged) |
| Automatic-acceptance rate | 36.0% |

## Interpretation

**False-review rate is 0.0% on both datasets.** Every correctly-extracted
document was accepted automatically; the validator never second-guessed a
document that didn't need it (once the one known ground-truth confound is
accounted for). This is the property that matters most for throughput:
the validator does not create needless review work.

**Recall is highly error-profile-dependent, and that is expected, not a
flaw.** Rotated-variant errors in this dataset are almost entirely
*plausible-looking* value swaps: a `True`/`False` checkbox flip is a
structurally valid boolean either way, and an accent misread
(`"Jesús"` -> `"Jesus"`) is a structurally valid name either way. Phase 6
has no rule that can tell a correct boolean from an incorrect one, or a
correct name from a misspelled one -- that would require either ground
truth (which production never has) or a much richer model of "what this
specific employer's data should look like" that this phase deliberately
does not build. Blurred-variant errors are overwhelmingly *missing or
malformed* critical fields (SSN, EIN, money), which format and
required-field rules catch directly -- hence the 88% recall there.

**This is exactly the limitation the brief asked to be stated plainly:**
a plausible-but-wrong value can pass format validation. This analysis
puts a real, measured number on how often that actually happens for this
system's current error profile, rather than leaving it as a hypothetical
caveat.

## What This Does Not Prove

- This is not a claim about Pipeline A's overall quality (that's the
  existing Phase 4/4E benchmark results); it is a claim about how well
  Phase 6 validation routes Pipeline A's actual historical errors.
- Only two of four degradation variants were analyzed (rotated and
  blurred -- the two with the richest, most contrasting error profiles
  available in already-committed artifacts). Clean/compressed variants
  have very few real errors to measure recall against at all (Tesseract
  clean-150 is 99.28% accurate) and were not separately analyzed here.
- The `employer.name` adjustment is scoped to that one field only; no
  other required-field rule was found to have a similar universal
  ground-truth confound in either dataset (confirmed by the `raw` vs.
  `adjusted` numbers differing by exactly the `employer.name` count).
