# Phase 8C.8 - Promote Employer-Name Signals Into The Production Validator

Promotes the two winning `employer.name` signals -- Phase 8C.5's
address-leak heuristic and Phase 8C.6's layout-span signal, combined per
Phase 8C.7's tiered-OR recommendation -- from evaluation-only evidence
into `w2_pipeline.validation.rules`, then reruns the full frozen
600-document Paddle prediction set through the real, promoted validator
to establish the new development baseline. Neither signal was tuned
further; both are promoted exactly as their own phases defined them. No
OCR, parser extraction decision, or checkbox logic was changed. No W-2
field other than `employer.name` was touched. This is a development
baseline, not a final project freeze.

## Implementation

### Where each signal now lives

`src/w2_pipeline/validation/rules.py`:

- `_check_employer_name_address_leak(document)` -- pure text inspection,
  no extraction dependency. Promotes Phase 8C.5's winning candidate
  (`contains_street_number AND contains_road_suffix`, expanded USPS-style
  suffix list) verbatim: same regex, same suffix set, same whole-word
  matching, no tuning, no company-name dictionary, no document-specific
  logic.
- `_check_employer_name_layout_anomaly(document, signals)` -- purely
  geometric, reading `signals.employer_name_observation_count` (see
  below); never inspects `employer.name`'s text.

Both are `error` severity and both appended to `run_all_rules`
(`ALL_RULE_NAMES` grew from 10 to 12); the default routing policy already
sends any `error` issue to `needs_review`, so either signal alone routes
for review -- the OR policy Phase 8C.7 recommended, achieved for free by
the existing routing mechanism (no new policy code needed).

### How layout provenance reaches validation

Maintains the dependency direction the brief specified --
**extraction/parser -> quality/provenance signal -> validator**, never
validator -> parser internals:

1. `src/w2_pipeline/extraction/parser_2026.py` gained
   `compute_employer_name_observation_count(document, observations)`, a
   read-only production function. It reuses `_observations_in_zone` and
   `_group_observation_rows` with a newly-named module constant,
   `EMPLOYER_NAME_ZONE` (previously an inline literal tuple in
   `_apply_ocr_employer_layout_fallbacks` -- now named so this function
   and the fallback can never drift out of sync). It never influences
   `employer.name`'s value; it only reports, after the value is already
   decided, how many observations the matching row-group contained. This
   moves Phase 8C.6's evaluation-only measurement into the smallest
   production surface the validator needs -- not a parser redesign.
2. `ExtractionResult` (`extraction/models.py`) gained one new optional
   field, `employer_name_observation_count: int | None`, populated by
   `PipelineAExtractor.extract_ingested` right after parsing.
3. `ExtractionSignals` (`validation/models.py`) gained the matching field,
   `employer_name_observation_count: int | None`. This is the existing
   "field-quality metadata a caller may attach" channel, extended rather
   than creating a new one.
4. Whoever calls `validate_w2_document` is responsible for copying
   `ExtractionResult.employer_name_observation_count` into
   `ExtractionSignals` -- exactly like `pipeline_id`/`route` already work.
   The validator itself never reaches into extraction/parser internals;
   `tests/validation/test_isolation.py` (no file under
   `src/w2_pipeline/validation/` imports `w2_pipeline.extraction`,
   `w2_pipeline.evaluation`, or `w2_pipeline.ingestion`) continues to
   pass unmodified.

### Issue codes and routing policy

| Issue code | Severity | Fires when |
|---|---|---|
| `employer_name_address_leak` | `error` | `employer.name` contains a street-number-shaped digit AND a road-suffix word |
| `employer_name_layout_anomaly` | `error` | `employer.name` came from more than one OCR observation |

Both issues are preserved independently in `ValidationResult.issues` --
never collapsed into one boolean -- so a document where both fire is
distinguishable from one where only one did, preserving the
both/one/neither agreement information Phase 8C.7 identified as valuable
free evidence.

### Native OCR confidence: untouched

Phase 8C.4's `ocr_confidence` field and its evaluation-side aggregation
code are unmodified. It remains available metadata, not used as a
routing threshold here.

## Regression Tests (Before The Benchmark Rerun)

15 new/updated tests, all passing before any 600-document run:

- `tests/validation/test_rules.py` (14 new): address-leak shape flagged;
  normal name not flagged; `3M Corporation` (legitimate number, no
  suffix) not flagged; `Infinite Loop Technologies` (suffix word, no
  number) not flagged; whole-word boundary preserved (`123 Wayfair Inc`
  not flagged); single-observation layout not flagged; multi-observation
  layout flagged with the count preserved in `metadata`; missing
  provenance (`None`) handled safely; and full routing coverage for all
  four combined-routing cases (neither/address-only/layout-only/both,
  each asserting the resulting `ValidationStatus`).
- `tests/extraction/test_parser_2026.py` (3 new):
  `compute_employer_name_observation_count` returns 1 for a normal
  single-line name, 2 for a merged row (using the same real diagnosed
  geometry as Phase 8C.1/8C.6's tests), and `None` when `employer.name`
  itself is `None`.
- `tests/extraction/test_pipeline_a.py` (updated): asserts
  `ExtractionResult.employer_name_observation_count` exists without
  changing the already-passing `field_accuracy == 1.0` assertion --
  confirms the new signal never affects the extraction result.
- `tests/evaluation/test_validator_effectiveness_predictions.py`
  (1 renamed + 2 new): the Phase 8C.3 test that documented the original
  "no rule inspects employer.name content" gap is renamed and its
  assertion flipped to confirm that exact shape **is now caught** --
  updating outdated evidence, not silencing a real regression (the
  scenario it constructs, a name plus `"123 Fake Rd"`, is precisely what
  Phase 8C.8 was built to catch). Two new tests confirm
  `employer_name_observation_count` threads correctly from
  `PredictionRecord.pipeline_metadata` and is absent (not fabricated) for
  records that predate this phase.

Full suite after all rule/model/test changes: **477 tests passing (460
baseline + 17 new/updated), zero regressions.**

## Full 600-Document Validator Rerun

### Stability check (required before scoring)

The frozen Phase 8C.2 `PredictionRecord` artifact never carried
`employer_name_observation_count`, so a fresh extraction pass was
required. New script:
`src/w2_pipeline/evaluation/run_pipeline_a_with_employer_name_signals.py`
uses the real, unmodified `PipelineAExtractor` (same PaddleOCR GPU
configuration as every prior Phase 8C run) and verifies **every one of
the 600 extracted documents against Phase 8C.2's frozen prediction by
full object equality** before anything is scored -- a stronger check
than Phase 8C.4/8C.6's independent accuracy recomputation.

```json
{
  "documents_checked": 600,
  "documents_matching_frozen_phase8c2": 600,
  "mismatches": []
}
```

**All 600 match exactly.** (One incidental bug was caught and fixed
during this check, not silently worked around: the new script initially
passed a different `document_id` convention to `IngestionService.ingest`
than Phase 8C.2's benchmark runner used, which showed up immediately as
a `metadata.document_id`-only mismatch on the very first document
checked -- fixed to match `w2_pipeline.evaluation.runner`'s own
`f"{sample_id}:{variant_id}"` convention exactly, then all 600
re-verified.)

Result artifacts:
```text
data/evaluation/results/phase8c8_paddle_with_layout_signals_600_predictions.jsonl
data/evaluation/results/phase8c8_extraction_stability_check.json
data/evaluation/results/phase8c8_validator_effectiveness_paddle_600.json
data/evaluation/results/phase8c8_validator_effectiveness_paddle_600_rows.jsonl
```

### Overall Validator Metrics

| Metric | Phase 8C.3 (pre-promotion) | Phase 8C.8 (post-promotion) |
|---|---:|---:|
| Total documents | 600 | 600 |
| Correct documents | 538 | 538 |
| Erroneous documents | 62 | 62 |
| Correct, accepted | 538 | 538 |
| Correct, routed needs_review | 0 | 0 |
| Erroneous, accepted | 62 | **58** |
| Erroneous, routed needs_review | 0 | **4** |
| Error-detection recall (all 62) | 0.0% | **6.45%** |
| False-review rate | 0.0% | **0.0%** (unchanged) |
| Automatic-acceptance rate | 100.0% | **99.33%** |
| Unsafe-acceptance rate | 10.33% | **9.67%** |
| Review-queue precision | undefined (0 routed) | **100.0%** |

**Do not read "6.45% overall recall" as a disappointing result** -- it is
exactly what the brief predicted and required separating out:
`box_13.retirement_plan`'s 60 checkbox failures are intentionally
untouched by this phase (see "Employer-Name Error Detection" below for
the number that matters here).

### Per-Variant Metrics

| Variant | Documents | Correct | Erroneous | Erroneous caught | False-review rate |
|---|---:|---:|---:|---:|---:|
| `external_clean_render` | 150 | 150 | 0 | -- | 0.0% |
| `compressed_jpeg` | 150 | 150 | 0 | -- | 0.0% |
| `blurred_png` | 150 | 150 | 0 | -- | 0.0% |
| `rotated_png` | 150 | 88 | 62 | 4 | 0.0% |

**Clean/JPEG/blur remain completely quiet** -- identical to Phase 8C.3,
zero documents flagged for any reason, confirming the two new rules
introduce zero false-review cost anywhere the known defects don't occur.
All 4 catches and 100% of the remaining unsafe-acceptance are, as
expected, confined to `rotated_png`.

### Employer-Name Error Detection (The Number This Phase Targeted)

| | |
|---|---:|
| Affected documents | 4 |
| Routed needs_review | **4** |
| Accepted | 0 |
| **Catch rate** | **100.0%** |

**4/4 known `employer.name` row-merge defects are now caught.** Zero
false positives among the 596 correct employer names (unchanged from
Phase 8C.5/8C.6/8C.7's own measurements -- confirmed again here in the
real, promoted validator, not just the evaluation-side simulation).

### Checkbox Errors: Explicitly Separate, Intentionally Unchanged

| | |
|---|---:|
| Affected documents | 60 |
| Routed needs_review | 2 |
| Accepted | 58 |
| Catch rate | 3.33% |

**The 2/60 "caught" here are incidental, not a checkbox detection.**
Phase 8C.7 already established that exactly 2 documents
(`symage_900033`, `symage_900082`) have *both* an `employer.name` failure
and a `box_13.retirement_plan` failure simultaneously (the
`overlap_between_classes` count). Those 2 are routed to `needs_review`
because of their `employer.name` issue -- `box_13.retirement_plan` itself
still has zero dedicated validation logic anywhere in this project. The
remaining 58 checkbox failures are accepted exactly as before. This
number should not be read as "checkbox detection improved 3.33%"; it is
a side effect of document-level (not field-level) routing, reported
transparently rather than left to look like unintended progress.

## Issue Agreement (Compared Against Phase 8C.7)

| State | Phase 8C.7 (evaluation-side simulation) | Phase 8C.8 (real validator) |
|---|---:|---:|
| Both fire | 4 | **4** |
| Address only | 0 | **0** |
| Layout only | 0 | **0** |
| Neither fires | 596 | **596** |

**Exact match.** The real production validator reproduces Phase 8C.7's
evaluation-side simulation precisely -- both issue codes appear on
exactly the same 4 documents (`symage_900033`, `symage_900045`,
`symage_900082`, `symage_900146`), confirmed directly via the validator
issue taxonomy:

```json
{"issue_code": "employer_name_address_leak", "document_count": 4, "correct_document_count": 0, "erroneous_document_count": 4},
{"issue_code": "employer_name_layout_anomaly", "document_count": 4, "correct_document_count": 0, "erroneous_document_count": 4}
```

No document anywhere in the 600 fires only one of the two issues, and no
correct document fires either. The known limitation both prior phases
already stated stands unchanged: this is 4 positive examples from one
dataset and one defect shape, not proof the two signals will always
agree this completely on a different corpus.

## Performance

Measured directly (in-process `time.perf_counter`, cross-checked with
`timeit` over repeated runs), on the same 600-document prediction set,
**validator time only** -- never conflated with the ~1.2-1.4s/document
OCR/extraction latency measured in Phase 8B/8C.2/8C.4:

| | Full validator (12 rules, post-promotion) |
|---|---:|
| Total, 600 documents | 17.4 ms |
| Mean | 0.029 ms |
| Median | 0.028 ms |
| p95 | 0.039 ms |
| Max | 0.124 ms |

**Incremental cost of just the two new rules**, measured in isolation
(calling only `_check_employer_name_address_leak` and
`_check_employer_name_layout_anomaly` per document, same 600-document
set):

| | Two new rules only |
|---|---:|
| Total, 600 documents | 1.67 ms |
| Mean | 2.79 us |
| Median | 2.65 us |
| p95 | 3.26 us |

The two new checks account for roughly **10% of total validator time**
(≈2.8us of ≈29us per document) -- a plain regex search plus a small
frozenset membership check, exactly as expected for pure string/int
comparisons with no I/O. This is negligible in absolute terms (600
documents' worth of validation, with the new rules, still completes in
under 20 milliseconds total) and was measured directly rather than
assumed, per the brief's explicit instruction.

## Success Criteria (Restated Against Measured Results)

| Criterion | Result |
|---|---|
| 4/4 known employer-name defects routed to review | **Met** |
| Correct clean/JPEG/blur documents remain effectively quiet | **Met** (0 flagged, 0.0% false-review rate) |
| False-review rate remains acceptably low | **Met** (0.0%, unchanged from pre-promotion) |
| No extraction behavior changes | **Met** (600/600 bit-identical to frozen Phase 8C.2) |
| Checkbox failures remain explicitly separate / unchanged | **Met** (58/60 still accepted; the 2 "caught" are a documented, transparent side effect of shared-document routing, not new checkbox logic) |
| Validator overhead negligible or clearly quantified | **Met** (quantified: ~2.8us/document incremental, ~29us/document total) |
| Full test suite passes | **Met** (477 passing, zero regressions) |

**100% overall validator recall was not chased, and was not expected** --
the `box_13.retirement_plan` class remains intentionally unresolved,
per the brief.

## What Was Deliberately Not Done

- No OCR configuration, parser extraction decision, or checkbox logic was
  changed.
- The two signals were not tuned further, and no new employer-name
  heuristic was added beyond exactly what Phase 8C.5/8C.6 already
  validated.
- Layout-provenance validation was not expanded to any field other than
  `employer.name`.
- No weighted/combined confidence score was introduced -- both issues
  remain separately visible `error` issues, exactly per Phase 8C.7's
  tiered-preservation recommendation.
- The frozen Phase 8B/8C.2/8C.3/8C.4/8C.5/8C.6/8C.7 artifacts were not
  modified; this phase's artifacts are new, separately-named files.
- Checkbox remediation was not started.
- A final project freeze was not declared -- this is a development
  baseline update.

## Verification

17 new/updated tests (see "Regression Tests" above); full suite: **477
tests passing (460 baseline + 17), zero regressions.** Extraction
stability verified by full object equality across all 600 documents
against the frozen Phase 8C.2 prediction before any validator scoring
occurred. `tests/validation/test_isolation.py` (validation depends on
neither `w2_pipeline.evaluation`, `w2_pipeline.extraction`, nor
`w2_pipeline.ingestion`) continues to pass unmodified, confirming the
promoted rules introduced no dependency-direction violation.
