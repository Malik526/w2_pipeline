# Final Evaluation Summary

Every number below is sourced from a committed, unmodified benchmark
artifact in `data/evaluation/results/`. This document deliberately does
**not** merge numbers across benchmark generations -- each section below
used a different scope/adapter/field-count, and averaging across them
would misrepresent all of them. All benchmarks use the **synthetic**
Symage dataset (`Symage/synthetic-us-forms-preview`); see
`docs/known-limitations.md` #1.

## Historical 24-field benchmark (Phase 8C.2)

The original, narrower field-coverage benchmark, frozen as the Phase
8C.2 production-candidate snapshot. **Historical scope only** -- superseded
in coverage (not correctness) by the expanded benchmark below.

| Metric | Tesseract | PaddleOCR GPU |
|---|---|---|
| Full-pipeline field accuracy (24 fields) | 98.54% (14,190/14,400) | **99.56% (14,336/14,400)** |
| Text/parser subsystem accuracy (23 fields, excl. `box_13.retirement_plan`) | 98.91% (13,650/13,800) | **99.97% (13,796/13,800)** |
| Average duration | -- | 1.229s/doc |

Source: `data/evaluation/results/phase8c2_final_paddleocr_gpu_all_variants_600.json`,
`docs/experiments/phase8c2-final-paddle-production-candidate.md`.

## Expanded evaluation contract (Phase 8D.1A)

The current field-coverage scope: employer/employee address, Box 12
semantic entries, and state/local rows added to scoring (previously
present in source annotations but never mapped by the ground-truth
adapter -- an evaluation-adapter gap, not a production-extraction gap).
PaddleOCR GPU, 600 documents, 4 conditions (`external_clean_render`,
`rotated_png`, `blurred_png`, `compressed_jpeg`).

| Metric | Value |
|---|---|
| Overall field accuracy | **99.649%** (25,829 / 25,920 fields) |
| `external_clean_render` | **100.0%** (6,480 / 6,480) |
| `rotated_png` | **98.627%** (6,391 / 6,480) |
| `blurred_png` | 99.985% (6,479 / 6,480) |
| `compressed_jpeg` | 99.985% (6,479 / 6,480) |
| Failed documents (extraction crash) | 0 / 600 |
| Average duration | 1.350s/doc (this run's average, all 4 conditions) |

Source: `data/evaluation/results/phase8d1a_expanded_pipeline_a_600.json`.

## Validation effectiveness after Phase 8D.1B

Same 600-document expanded run, now scored against the production
validator (16 rules; `ALL_RULE_NAMES` in `src/w2_pipeline/validation/rules.py`)
including the Phase 8D.1B address-evidence rule.

| Metric | Overall | `rotated_png` only |
|---|---|---|
| Erroneous documents (ground truth mismatch) | 17 | 15 |
| Erroneous documents routed to `needs_review` | 15 | 15 |
| Erroneous documents unsafely accepted | **2** | **0** |
| Unsafe acceptance rate | **0.33%** | **0.0%** |
| Error detection recall | 88.2% | **100%** |
| False review rate (correct doc sent to review) | **0.0%** | 0.0% |
| Review queue precision | 100% | 100% |

The 2 unsafely-accepted documents (`symage_900027`/`blurred_png`,
`symage_900061`/`compressed_jpeg`) are OCR character-recognition
substitutions in an address field (a plausible-looking wrong value, not
a missing one) -- a different failure class than the evidence rule
targets, honestly reported rather than absorbed into the headline number.
See `docs/known-limitations.md` #2.

Source: `data/evaluation/results/phase8d1b_validator_effectiveness_600.json`.

## Performance

| Measurement | Value | Source |
|---|---|---|
| Phase 8C.2 average (600 docs, all conditions) | 1.229s/doc | `phase8c2_final_paddleocr_gpu_all_variants_600.json` |
| Phase 8C.11 steady-state (excl. 1st doc) | 1.267s/doc | `docs/experiments/phase8c11-anchor-checkbox-promotion.md` |
| Phase 8C.11 all-600 average | 1.280s/doc | same |
| Phase 8D.1A average (600 docs, expanded scope) | 1.350s/doc | `phase8d1a_expanded_pipeline_a_600.json` |
| First-document PaddleOCR model-load/warmup cost | ~8.9s (one-time per process) | `docs/experiments/phase8c11-anchor-checkbox-promotion.md` |

Steady-state PaddleOCR GPU latency is consistently **~1.2-1.35s/document**
across every benchmark generation in this project; the warmup cost is a
one-time per-process cost, not a per-document one, and is reported
separately rather than averaged in or hidden.

Validator/review/export overhead is negligible relative to OCR: all
`review/cli.py` commands used in the Phase 8D.2 walkthrough (validate,
review-create, review-correct, review-revalidate, export-document,
export-review) complete in well under 100ms each, since none of them
invoke OCR -- they operate on an already-extracted canonical
`W2Document` plus its `ExtractionSignals`.

## Tests

**600 tests passing** as of commit `0b34d76` (Phase 8D.2), zero known
regressions. See each phase's `docs/experiments/*.md` for the
test-count history (477 -> 489 -> 514 -> ... -> 597 -> 600).

## Field coverage

Canonical `W2Document` fields, classified by what the external Symage
600-document benchmark can actually verify. Full machine-readable
version: `data/evaluation/results/phase8d1a_canonical_field_coverage_matrix.json`.

**Implemented + benchmarked** (real extraction logic, real measured
accuracy -- the numbers above): employee/employer identity (SSN, EIN,
name, first/middle/last), employee/employer address (line 1, city,
state, postal code, country), federal Boxes 1-6, Box 12 semantic entries
(code + amount), `box_13.retirement_plan`, state/local Boxes 15-17, all
`metadata.*` fields.

**Implemented but weakly benchmarked** (real detector exists; benchmark
has zero positive/true examples to verify against): `box_13.statutory_employee`,
`box_13.third_party_sick_pay` -- a zone-calibrated OCR checkbox detector
already exists for both (same mechanism as `retirement_plan`), but 0/150
base documents have either flag checked in ground truth, so detector
correctness on a true positive is unverified here.

**Schema-supported, annotation unavailable** (schema field + extraction
code both exist; the Symage dataset's annotations never populate a
value to check against): `employee.suffix`, `address_line_2` (both
parties), federal Boxes 7-11, `box_14_entries`, `tipped_occupation_codes`,
state/local Boxes 18-20, `employer.control_number`.

**Internal bookkeeping, not scored**: `field_observations[]` (extraction
provenance metadata, not W-2 business content -- excluded from
evaluation and CSV output by design).

No field in the "schema-supported, annotation unavailable" or "weakly
benchmarked" categories is claimed as production-verified anywhere in
this project's numbers above.

## Scope statement

**These numbers are benchmark-specific and synthetic, not universal
production claims.** They describe measured behavior on the Symage
synthetic dataset under the 4 conditions tested, on the specific
hardware/OCR configuration recorded in each artifact's
`benchmark_metadata`. They do not predict accuracy on real taxpayer
documents, other scan qualities, other tax years, or other form types.
See `docs/known-limitations.md` for the full, explicit list of what is
and is not covered.
