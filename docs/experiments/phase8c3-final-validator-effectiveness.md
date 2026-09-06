# Phase 8C.3 - Final Validator Effectiveness On Frozen Paddle Predictions

This is the authoritative validator-effectiveness analysis for the frozen
production-candidate extraction pipeline (Phase 8C.2). It measures how
the current Phase 6 production validator (`validate_w2_document`, no
changes made) behaves against the *actual* remaining errors in the final
600-document PaddleOCR run -- not a reconstruction, not an adjusted view.

## Method

Unlike the historical `validator_effectiveness.py` (which had to
*reconstruct* a predicted `W2Document` from ground truth plus a
benchmark's recorded field failures, because no historical run ever
persisted the complete prediction), this analysis consumes the real,
complete, ground-truth-free `PredictionRecord` entries Phase 8C.2 already
saved -- the actual `W2Document` PaddleOCR produced for all 600 documents.
New code:
`src/w2_pipeline/evaluation/validator_effectiveness_predictions.py`.

No OCR was rerun, no parser logic changed, no validation rule changed, no
routing behavior changed, and nothing was tuned against ground truth.
This run also does **not** apply the old `employer.name` ground-truth
adjustment (`KNOWN_GROUND_TRUTH_GAPS` in the historical module): Phase 8A
added an authoritative FUNSD-derived `employer.name` mapping to the
Symage ground truth, so that adjustment no longer applies and using it
here would hide the real finding.

## Leakage Boundary

For every one of the 600 saved `PredictionRecord` entries:

```text
record.document (the ACTUAL, complete prediction)
    -> validate_w2_document()      <- ground truth never passed in here
    -> accepted / needs_review
    -> THEN, and only then, ground truth (loaded from the manifest's own
       ground_truth_path, scored with the same evaluated_field_paths and
       compare_w2_documents the Phase 8C.2 benchmark itself used)
       is consulted to label whether the document was actually correct
       or erroneous
```

`ExtractionSignals` passed to the validator carries only
`pipeline_id`/`extraction_route`/an outcome derived from the record's own
`status` -- never `variant_id` or a document-condition label, which is
dataset metadata (e.g. "this is the rotated variant") that a real
incoming document would not carry. Enforced by a call-spy test
(`test_validator_receives_only_the_real_prediction_never_ground_truth`),
the same technique the historical module's own isolation test uses.
Validation package structural isolation (`tests/validation/test_isolation.py`)
is unaffected -- no file under `src/w2_pipeline/validation/` was touched.

Source artifacts:
```text
data/evaluation/results/phase8c2_final_paddleocr_gpu_all_variants_600_predictions.jsonl
data/evaluation/external/symage-synthetic-us-forms-preview-final/manifest.jsonl
```

Output artifacts:
```text
data/evaluation/results/phase8c3_final_validator_effectiveness_paddle_600.json
data/evaluation/results/phase8c3_final_validator_effectiveness_paddle_600_rows.jsonl
```

The `.json` file omits the verbose per-document `rows` (`--no-rows`); the
compact `_rows.jsonl` carries one line per document
(`document_id`, `variant_id`, `has_error`, `failing_field_paths`,
`validation_status`, `validation_issues`) -- not a duplicate of the full
prediction artifact, which still carries the complete `W2Document` per
document and is not repeated here.

## Overall Metrics

| Metric | Count | Percentage |
|---|---:|---:|
| Total documents | 600 | -- |
| Correct documents | 538 | 89.67% |
| Erroneous documents | 62 | 10.33% |
| Correct, accepted | 538 | 100.0% of correct |
| Correct, routed needs_review | 0 | 0.0% of correct |
| Erroneous, accepted | 62 | 100.0% of erroneous |
| Erroneous, routed needs_review | 0 | 0.0% of erroneous |
| **Error-detection recall** | 0 / 62 | **0.0%** |
| **False-review rate** | 0 / 538 | **0.0%** |
| **Automatic-acceptance rate** | 600 / 600 | **100.0%** |
| **Unsafe-acceptance rate** | 62 / 600 | **10.33%** |
| Review-queue precision | 0 / 0 | undefined (no document was ever routed to review) |

**The current production validator routed zero documents to review across
all 600.** Every one of the 62 erroneous documents was accepted
automatically, silently. This is not a partial miss -- it is a complete
miss on this run's entire remaining error surface.

## Per-Variant Metrics

| Variant | Documents | Correct | Erroneous | Erroneous caught | Erroneous accepted | Needs-review (any) |
|---|---:|---:|---:|---:|---:|---:|
| `external_clean_render` | 150 | 150 | 0 | -- | -- | 0 |
| `compressed_jpeg` | 150 | 150 | 0 | -- | -- | 0 |
| `blurred_png` | 150 | 150 | 0 | -- | -- | 0 |
| `rotated_png` | 150 | 88 | **62** | **0** | **62** | 0 |

Confirms the expectation from Phase 8C.2: clean/JPEG/blur are perfect, so
there is nothing for the validator to catch or falsely flag there (0%
false-review rate holds trivially). All 62 real remaining errors are
concentrated in `rotated_png`, and **all 62 pass through completely
unflagged.**

## Error-Class Analysis

### A. `box_13.retirement_plan` (checkbox visual-geometry error)

| | |
|---|---:|
| Affected documents | 60 |
| Routed needs_review | 0 |
| Accepted | 60 |
| **Catch rate** | **0.0%** |

**Why the validator cannot detect this without ground truth**: direct
inspection of `src/w2_pipeline/validation/rules.py` confirms there is no
rule that references `box_13` fields at all -- `retirement_plan` is a
plain `bool`, and `True` is exactly as structurally valid as `False`.
Every possible value passes Pydantic validation and every Phase 6 rule
trivially. There is no plausibility signal available from the document
alone (e.g. no cross-check against another box, no visual-confidence
score fed into `ExtractionSignals`) that could distinguish a correct
`False` from this rotation-induced `True`.

### B. `employer.name` (row-merge residual)

| | |
|---|---:|
| Affected documents | 4 |
| Routed needs_review | 0 |
| Accepted | 4 |
| **Catch rate** | **0.0%** |

**Why the validator cannot detect this without ground truth**: the only
rule touching `employer.name` is `_check_employer_identity_required_fields`,
which checks *only* whether the field is blank. The row-merge residual's
predicted value (e.g. `"Elan Consulting Corp 2861 Geneva Ponce De Leon Rd"`)
is a well-formed, non-blank string -- it passes the blank check trivially.
There is no length, word-count, or address-leakage heuristic in Phase 6
today that could flag "this looks like a name with an address appended."
A focused test
(`test_row_merge_style_wrong_but_nonblank_employer_name_is_not_caught`)
reproduces this exact shape directly against the real validator and
confirms it is accepted, not a hypothetical.

### Overlap Between The Two Classes

**2 documents exhibit both failures simultaneously**:
`symage_900033-irs_w2_single_page_2026-p0::rotated_png` and
`symage_900082-irs_w2_single_page_2026-p0::rotated_png`. This is not
surprising: both defects share the same underlying cause (rotation skew
large enough to disrupt PaddleOCR's spatial layout assumptions), so the
same especially-skewed documents are more likely to trip both. This
overlap is exactly why `60 + 4 - 2 = 62` unique erroneous documents,
not `64` (the raw field-failure count) -- see "Field Failures vs.
Erroneous Documents" below.

## Field Failures vs. Erroneous Documents

Do not conflate the two:

| | Count |
|---|---:|
| Total field failures (from Phase 8C.2) | 64 |
| Total unique erroneous documents (this analysis) | **62** |
| Overlap (documents with both failure classes) | 2 |

`64 - 62 = 2`, exactly matching the 2-document overlap above: each of
those 2 documents contributes 2 field failures but counts once as an
erroneous document. Computed directly by comparing each complete saved
prediction to ground truth over the same `evaluated_field_paths` Phase
8C.2 used -- not assumed from the field-failure count.

## Validator Issue Taxonomy

**Empty.** Zero documents were routed to `needs_review` anywhere in this
600-document run, so there is no issue-code breakdown to report -- the
validator raised zero `error`-severity issues (and no `warning`-only
issue that would matter, since the default routing policy does not
escalate warnings) on any of the 600 predictions, correct or erroneous
alike.

This is itself a finding, not an omission: it means every one of the 600
predicted documents is fully well-formed by every *structural* rule Phase
6 currently runs (supported metadata, required-field presence, SSN/EIN
format, money sign/precision, Box 12 code format, empty state/local
entries) -- including the 62 erroneous ones, whose specific defects
(a wrong boolean, a name with trailing address text) simply don't violate
any of those structural rules.

## False-Review And Unsafe-Acceptance Analysis

- **False-review rate: 0.0% (0/538).** The validator never wastes review
  effort on a document that was actually extracted correctly, on this
  run. There is no false-positive cost anywhere in this dataset today.
- **Unsafe-acceptance rate: 10.33% (62/600).** Just over one in ten
  documents in this run is silently accepted with wrong data un-caught --
  entirely concentrated in the `rotated_png` variant, where it is
  actually 62/150 = 41.33% of that variant's documents.
- **Review-queue precision: undefined.** With zero documents routed to
  review, there is no review queue to measure precision on.

## Interpretation

**Which remaining extraction errors the validator catches**: none, on
this run. Both known residual defect classes -- the checkbox
rotation-geometry boolean and the `employer.name` row-merge residual --
pass through 100% of the time.

**Which plausible errors pass silently**: exactly these two, and by
construction any other error that produces a structurally well-formed
value (a valid-shaped SSN/EIN, a non-blank name, a non-negative
2-decimal money amount, a legal boolean) rather than a missing or
malformed one. The Phase 6 rule set's entire detection surface is
*structural validity*, not *plausibility* or *cross-field consistency*
-- so any error a pipeline makes that still produces a well-formed value
is invisible to it today, independent of pipeline or backend.

**Whether review volume is reasonable**: there currently is none (0/600
routed to review) on this final production-candidate run. That is
"reasonable" only in the narrow sense that it imposes zero review labor
-- it provides zero safety net for the 10.33% unsafe-acceptance rate
found here. A firm relying on validator-driven review triage to catch
Phase 8C.2's two known residual defects would see neither caught, ever,
under the current rule set.

**Production implication for the final Paddle architecture**: this is
not a regression introduced by Phase 8C.1/8C.2 remediation -- it is a
pre-existing gap in the Phase 6 structural rule set that was invisible
until now, because there was never before a complete, ground-truth-free,
accurate prediction set to test it against at this fidelity. The frozen
Paddle extraction pipeline's own accuracy (99.56%) is materially higher
than the validator's demonstrated ability to catch what's left of it. Any
production deployment decision should treat the validator's current
0.0% catch rate on these two classes as a known, quantified residual
risk (10.33% unsafe acceptance, concentrated entirely in rotated
documents), not as a covered risk -- closing it would require new rules
with genuine plausibility signal (e.g. a length/shape sanity check on
`employer.name`, or routing every `rotated_png`-condition document to
review regardless of content, if that signal were ever passed in), which
is explicitly out of scope for this measurement-only phase.

## What Was Deliberately Not Done

- No OCR was rerun; no parser, checkbox, or validation-rule logic was
  changed; no routing policy was changed.
- No rule was added to catch either known error class, despite both
  being fully diagnosed here -- per the brief's explicit instruction.
- The old `employer.name` ground-truth-gap adjustment
  (`validator_effectiveness.py`'s `KNOWN_GROUND_TRUTH_GAPS`) was not
  applied; this analysis measures the real, unadjusted validator
  behavior against real, fully-covered ground truth.
- The frozen Phase 8B/8C.2 benchmark artifacts were not modified.

## Limitations

- This measures only the current Phase 6 structural rule set against one
  frozen 600-document PaddleOCR run. It says nothing about how a
  different rule set, a confidence-aware validator, or a different
  backend's error shapes would score.
- The 0% catch rate on both error classes is a direct, expected
  consequence of what rules.py already implements (verified by direct
  code reading, not inferred from the metric alone) -- it is not a
  surprising bug in this analysis code; it is an accurate measurement of
  an already-narrow rule set meeting two specific error shapes it was
  never designed to catch.
- No new validation rule was designed or evaluated as a candidate fix;
  that is future work, not this phase.

## Verification

7 new focused tests in
`tests/evaluation/test_validator_effectiveness_predictions.py`, covering:
end-to-end correct/detectable/undetectable-error counting and rate math;
the leakage-boundary call-spy; the exact row-merge-residual shape
reproduced directly against the real validator; document-vs-field-failure
counting; error-class overlap detection; per-variant aggregation
isolation; and extraction-failure-status signal handling. Full suite:
**379 tests passing (372 baseline + 7 new), zero regressions.** No file
under `src/w2_pipeline/validation/` was modified, so
`tests/validation/test_isolation.py` (no production/validation package
depends on evaluation code) continues to pass unchanged.
