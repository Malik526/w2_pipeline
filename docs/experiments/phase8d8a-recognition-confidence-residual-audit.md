# Phase 8D.8A — Recognition-Confidence Residual Error Audit

**Status: evaluation only. Production behavior unchanged.**

Baseline commit `de2b1a7`. Implemented on branch
`experiment/phase8d8a-confidence-audit`.

## Phase Question

Can native PaddleOCR recognition confidence separate the two remaining
residual OCR-substitution errors from correct OCR-derived fields strongly
enough to support safe review routing, evaluated **at document-routing
level composed with the existing production validator** — not just by
comparing the two bad tokens' scores against a distribution in isolation?

This is the same instrumentation Phase 8C.4 built and validated on a
different failure class (`employer.name` row-merge, where OCR was
genuinely correct and confidence rightly showed no signal). This phase
applies it, unmodified, to a failure class where confidence is actually
plausible: true character-level recognition substitutions.

## Baseline (Verified From Committed Artifacts)

`data/evaluation/results/phase8d1b_validator_effectiveness_600.json`,
confirmed by direct inspection before this phase started:

| Metric | Value |
|---|---:|
| Documents | 600 |
| Erroneous documents | 17 |
| Routed to review | 15 |
| Unsafe accepted | 2 |
| Error detection recall | 88.2% |
| False review rate | 0.0% |
| Unsafe acceptance rate | 0.33% |
| Review-queue precision | 100% |

This phase's own fresh instrumented run reproduces these exact numbers
(see "Extraction/Validator Stability" below) before any confidence
analysis is trusted.

## What Already Existed (Audited, Not Duplicated)

- `TextObservation.ocr_confidence` (Phase 8C.4): populated by
  `PaddleOcrAdapter.extract_image` from Paddle's native `rec_scores`,
  index-attached, `[0,1]`-validated.
- `field_confidence.find_all_field_confidence_matches` (Phase 8C.4):
  reverse-matches a field's parsed value to its contributing
  observation(s). Its default field set has no address fields; this
  phase passes its own wider `field_paths` argument (no edit to that
  frozen module).
- `w2_pipeline.extraction.signals.build_extraction_signals` (Phase 8D.4,
  centralized from Phase 8D.1B's original inline mapping): the
  canonical `ExtractionResult -> ExtractionSignals` mapping, including
  the Phase 8D.1B address-evidence fields
  (`employer_address_evidence_*`/`employee_address_evidence_*`) the
  production `_check_address_extraction_evidence` validator rule reads.
  **An earlier draft of this phase's runner hand-rolled a partial
  signals mapping that omitted these fields and silently reproduced the
  pre-8D.1B validator baseline (13 unsafe-accepted, 23.5% recall)
  instead of current production behavior (2 unsafe-accepted, 88.2%
  recall) — caught by this phase's own stability check, fixed by
  switching to the shared helper.** See "Known Limitations."

New for this phase:

- `src/w2_pipeline/evaluation/recognition_confidence_residual_audit.py` —
  pure, unit-tested analysis helpers (field signal derivation, threshold
  flagging, document-level routing composition, routing metrics,
  threshold sweep, non-ASCII audit).
- `src/w2_pipeline/evaluation/run_recognition_confidence_residual_audit.py` —
  one fresh instrumented PaddleOCR GPU run that produces, per document,
  raw-observation confidence, the real validator's routing decision, and
  ground-truth correctness, all from a single OCR pass.

## Field Scope

22 fields: Phase 8C.4's original 12 (employee identity/SSN, employer
EIN/name, federal Boxes 1-6) + 10 address fields — `employer.address.*`
and `employee.address.*`, each × `address_line_1`/`city`/`state`/
`postal_code`/`country`. `address_line_2` is excluded for both parties:
no manifest entry's `evaluated_field_paths` ever includes it, so no
ground truth exists to label a prediction there correct or incorrect.
`box_13.retirement_plan` stays excluded throughout — a separate
pixel-based checkbox detector, not OCR text recognition.

## Known Residuals: Confirmed Confidence Values

| Document | Variant | Field | Expected | Predicted | Native confidence |
|---|---|---|---|---|---:|
| symage_900027 | blurred_png | employer.address.address_line_1 | `369 Pennsylvania Ave N` | `369 Pennsylvania Áve N` | **0.9864** |
| symage_900061 | compressed_jpeg | employer.address.address_line_1 | `9992 S Jefferson St` | `9992 Š Jefferson St` | **0.9752** |

Both are single-observation matches (`selected_reason: "ok"`, no
ambiguity, no multi-run merge) — the confidence is unambiguously the
score PaddleOCR assigned to the exact text that became the field's
value. Full 4-variant confidence table for both documents is in
`data/evaluation/results/phase8d8a_recognition_confidence_audit.json`
(`known_residuals`).

**These are also the only two unsafe-accepted documents in the full
600-document benchmark**, and the only two incorrect OCR-derived-field
observations with a recoverable confidence anywhere in the run
(`all_incorrect_observations`, 2 entries, identical to
`address_incorrect_observations`) — confirming the brief's Section 9
question directly: on this benchmark, every true OCR recognition error
is an address-line character substitution.

## Confidence Distributions (600 Documents, Real Data)

### Correct address observations (`employer`/`employee` `address_line_1`)

| N | min | p1 | p5 | median | mean | max |
|---:|---:|---:|---:|---:|---:|---:|
| 3,551 | 0.9035 | 0.9658 | 0.9800 | 0.9998 | 0.9968 | 1.0000 |

### Incorrect address observations

Both residuals — no distribution statistics are meaningful for n=2, so
both are reported directly: **0.9752**, **0.9864**.

### All correct OCR-derived field observations (22-field scope)

| N | min | p1 | p5 | median | mean | max |
|---:|---:|---:|---:|---:|---:|---:|
| 10,619 | 0.9015 | 0.9691 | 0.9893 | 0.9999 | 0.9984 | 1.0000 |

### All incorrect OCR-derived field observations

Identical to the address-incorrect set — 0.9752 and 0.9864 are the only
two recognition errors in the entire benchmark.

**Both residual confidences sit inside the correct-address distribution,
not below it**: 0.9752 is between p1 (0.9658) and p5 (0.9800) — roughly
the correct population's bottom 1-5th percentile; 0.9864 is above p5,
comfortably inside the bulk of the correct distribution. Unlike Phase
8C.4's `employer.name` case (confidence ≈1.0000 for both correct and
incorrect, zero separation), there **is** some real separation here —
but it is a tail overlap, not a clean gap.

## Threshold Sweep (Full 22-Field Scope, `selected` Aggregation)

Full sweep (29 thresholds, all three aggregation variants) in
`data/evaluation/results/phase8d8a_recognition_confidence_thresholds.json`.
**All three aggregation variants (`selected`/`min`/`mean`) produce
identical results on this dataset** — every matched field in all 600
documents is a single-observation window (10,621 "ok" matches, 0
ambiguous multi-observation, 0 missing-confidence), so there is never a
case where `selected` differs from `min`/`mean`; Section 16's
variant-choice question has an empirical non-answer here: the variants
never disagree.

Representative thresholds, composed with the real production validator
(OR-composition: needs-review if either the validator or the candidate
rule flags it):

| Threshold | Residual errors caught | New false reviews | Recall | Unsafe acceptance | Autoaccept | Review precision |
|---:|---:|---:|---:|---:|---:|---:|
| ≤0.90 (baseline, no confidence signal) | 0/2 | 0 | 88.2% | 0.33% | 97.5% | 100% |
| 0.97 (just below first bad score, 0.9752) | 0/2 | 83 | 88.2% | 0.33% | 83.7% | 15.3% |
| 0.98 (catches the Š case only) | 1/2 | 189 | 94.1% | 0.17% | 66.0% | 7.8% |
| 0.99 (catches both) | 2/2 | 351 | 100% | 0.0% | 39.0% | 4.6% |
| 0.999 | 2/2 | 533 | 100% | 0.0% | 8.7% | 3.1% |

Cost climbs steeply and immediately: even the threshold that catches
*neither* residual (0.97) already forces 83 correct documents into
review (14.2% false-review rate) for zero recall gain, because the
general correct-field confidence distribution's tail starts well above
0.97.

## Composition With The Current Validator

The current validator (Phase 8D.1B's address-evidence rule) already
catches 15/17 erroneous documents with **zero** false review — it is
structurally blind only to these two well-formed-but-mis-recognized
address lines (`usable_row_count == 3`, i.e. "looks complete," per
`docs/experiments/phase8d1b-address-safety-and-box12-slot-semantics.md`).
Composing a confidence threshold on top therefore has nothing "free" to
gain: every document the confidence rule would newly flag at any
practical threshold is a document the validator already correctly
accepted. This is the central document-level finding, not just "the two
bad tokens had lower scores in isolation."

### Narrower scope: address-only fields, not all 22

Restricting the candidate rule to only the 10 address fields (excluding
identity/EIN/federal-box fields) reduces but does not eliminate the
cost: at threshold 0.99 (catches both residuals), new false reviews drop
from 351 (22-field scope) to 294 (address-only), autoaccept rises from
39.0% to 48.5% — still a materially expensive tradeoff for 2 caught
errors. Full sweep saved in this report's evidence; not promoted to a
permanent artifact (exploratory only, per the brief's Section 16 cap on
formula variants).

## False-Review Audit (Section 13)

At threshold 0.98 (189 newly-routed documents) and 0.99 (351), **every
single newly-routed document is genuinely correct** (`has_error: false`
in 100% of cases at both thresholds) — the candidate rule never
accidentally helps by coincidentally flagging an error the validator
missed elsewhere; it only adds cost. The triggering fields are broadly
distributed across the entire evaluated surface, not concentrated in
addresses:

At threshold 0.98 (189 documents), top triggering fields:

| Field | Count |
|---|---:|
| employer.address.postal_code | 46 |
| employee.address.address_line_1 | 40 |
| employer.address.address_line_1 | 36 |
| employee.address.postal_code | 33 |
| employee.first_name | 31 |
| employee.middle_initial | 31 |
| employer.name | 10 |
| employee/employer.address.state | 10 each |
| employer.ein | 6 |

At threshold 0.99 (351 documents), the same pattern holds at larger
scale, with `employer.name` rising to 57 occurrences. Full per-document
detail (document ID, variant, exact triggering field(s), value,
confidence) is preserved for every threshold in
`phase8d8a_recognition_confidence_thresholds.json`
(`thresholds[].newly_routed_only_by_confidence[].triggering_fields`).

**What occupies the low-confidence tail**: ordinary, correctly-recognized
text under blur/compression/rotation degradation — postal codes, street
addresses, first names, EINs — not a narrow or unusual category. A
threshold aggressive enough to catch the two residuals inevitably also
catches a broad cross-section of otherwise-unremarkable correct fields.

## Unicode / Non-ASCII Observation Audit (Section 14)

14 non-ASCII OCR-derived observations found across the 600-document
benchmark: 12 are legitimate accented employee first names (`Jesús`,
`Óliver`, `Adán`, each appearing once per variant, 4 variants each), all
correct, all with confidence **0.9950-0.9999** — comfortably above even
the higher residual error (0.9864). The other 2 are the residuals
themselves. **Legitimate accented text is not itself a source of
false-review cost at the thresholds this sweep considered** — its
confidence is uniformly high — but this is a small sample (3 distinct
names) and should not be read as a general guarantee for a more
linguistically diverse document population.

## Extraction/Validator Stability

This run's field accuracy (25,829/25,920 = 99.65%) and validator
baseline (17 erroneous, 15 routed, 2 unsafe accepted, 88.2% recall,
0.33% unsafe acceptance, 100% review precision) match the frozen Phase
8D.1B numbers exactly, confirming this instrumented rerun reproduces
current production behavior before its confidence analysis is trusted —
mirroring Phase 8C.4's own stability-guard discipline.

## Separation Result

### B — PARTIAL / EXPENSIVE SEPARATION

Native PaddleOCR recognition confidence **does** show real, measurable
separation for this failure class — unlike Phase 8C.4's `employer.name`
finding, the two residual confidences (0.9752, 0.9864) are not
indistinguishable from the correct population's central tendency, and a
threshold exists that catches both with zero remaining unsafe
acceptance. But the false-review cost to reach that threshold is
material, not negligible: 351 correct documents (59.9% of the correct
population) newly routed to review, autoaccept collapsing from 97.5% to
39.0%, review-queue precision falling to 4.6%, purely to catch 2 already
very-low-frequency (2/600) errors the validator otherwise leaves
unsafe-accepted at a 0.33% rate. Even the cheapest threshold that
catches only one of the two residuals (0.98) already costs 189 false
reviews (32.3%) for a 0.16-percentage-point unsafe-acceptance
improvement.

**Recommendation**: do not promote a global recognition-confidence
threshold. The false-review cost dominates any unsafe-acceptance gain by
roughly two orders of magnitude at every threshold tested. A narrower,
more targeted signal — e.g., a contextual check specific to the address
zone's character composition, or accepting this specific 0.33% residual
risk as a documented known limitation — is more promising than a global
score cutoff. Address-only field scoping helps modestly (351→294 new
false reviews at the threshold catching both) but does not change the
conclusion.

## Performance

Fresh PaddleOCR GPU inference was required (existing predictions
artifacts store only the final `W2Document`, not raw observations).
600-document run: 798.99s total (13.3 minutes), 1.33s/document average
(model warm-up amortized into the total, not isolated separately).
Confidence/threshold analysis itself is negligible (<1s, pure Python
over already-computed rows).

## Tests

31 new tests in
`tests/evaluation/test_recognition_confidence_residual_audit.py`:
`selected`-confidence strictness (single unambiguous observation only;
unmatched/ambiguous/no-confidence all explicitly `None` with a labeled
reason; never silently falls back to min/mean); threshold boundary
behavior (`==` does not flag, `<` does; missing confidence never
flags); per-aggregation behavior (`selected`/`min`/`mean` can
legitimately disagree, tested with a synthetic multi-observation case
even though the real dataset never exercises the disagreement);
document-level OR-composition; routing-metric arithmetic
(recall/false-review/unsafe-acceptance/precision); threshold-sweep
double-counting avoidance (a document the validator already routes is
never counted as a confidence "win"); triggering-field attribution;
non-ASCII detection; `box_13.retirement_plan` and `address_line_2`
exclusion from the phase's field scope. Full suite: 691 passing (660
baseline + 31 confidence-audit tests, no change to existing tests),
zero regressions.

## Known Limitations

- **The runner script's first draft under-built `ExtractionSignals`**,
  omitting the Phase 8D.1B address-evidence fields and silently
  reproducing the pre-8D.1B (23.5% recall) validator baseline instead of
  current production behavior (88.2% recall). Caught by this phase's own
  extraction/validator stability check before any confidence conclusion
  was drawn, fixed by switching to the shared
  `build_extraction_signals` helper, and the full 600-document run was
  redone. This is exactly the kind of error the stability-check
  discipline exists to catch — documented here rather than silently
  corrected, since it is a real finding about how easy this mistake is
  to make when a phase reimplements signal-threading instead of reusing
  the shared helper.
- Reverse-matching (`find_all_field_confidence_matches`) is the same
  approximate, exact/token-membership heuristic Phase 8C.4 built and
  documented its limitations for — unchanged here, and it happened to
  face no ambiguous/multi-observation cases in this particular 600-doc
  run (every match was a clean single observation), so those limitations
  were not exercised, not because they were resolved.
- The unicode audit's 3 distinct accented names is a small sample from
  one synthetic dataset; not a general claim about accented-name safety
  across a more linguistically diverse population.
- This measures PaddleOCR only, on this one dataset, where true
  recognition errors are extremely rare (2/25,920 fields). It says
  nothing about whether confidence would be more useful on a harder
  dataset with a larger genuine-error population.
- No combined/derived/calibrated confidence score was created or
  implied. Every value reported here is Paddle's own emitted recognition
  score ("Paddle emitted a native recognition score of X"), never
  reframed as a probability of correctness.

## What Was Deliberately Not Done

- No change to `validation/rules.py`, `validation/routing.py`, OCR
  configuration, parser zones, or canonical output.
- No new validation issue code or production routing behavior.
- No spellcheck, accent stripping, or regex normalization.
- No calibrated probability score.

## Artifacts

- `data/evaluation/results/phase8d8a_recognition_confidence_rows.jsonl`
- `data/evaluation/results/phase8d8a_recognition_confidence_audit.json`
- `data/evaluation/results/phase8d8a_recognition_confidence_thresholds.json`
- `src/w2_pipeline/evaluation/recognition_confidence_residual_audit.py`
- `src/w2_pipeline/evaluation/run_recognition_confidence_residual_audit.py`
- `tests/evaluation/test_recognition_confidence_residual_audit.py`

## Decision

**B — PARTIAL / EXPENSIVE SEPARATION.** Do not promote a global
recognition-confidence threshold. Production change: **NONE**.

## Next

Per Section 32's B/C branch: no promotion-phase brief follows from this
result. A future candidate experiment, if pursued, would be a narrower
contextual signal (address-zone-specific, not a global field-confidence
cutoff) rather than another global threshold sweep — or, given the
residual's rarity (0.33% unsafe acceptance, 2/600 documents), accepting
it as a documented known limitation may be the more proportionate
outcome. Not decided here; this phase's scope ends at the evaluation
result.
