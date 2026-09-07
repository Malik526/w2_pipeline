# Phase 8D.1B - Address Safety Closure + Box 12 Blank-Slot Semantics Audit

Two narrowly-scoped workstreams: (A) close the 13 unsafe-accepted address
failures the Phase 8D.1A expanded benchmark exposed, with an
evidence-based validator signal rather than a bare null-check; (B)
determine whether a printed blank-code "$0.00" Box 12 slot should be
represented in canonical output or intentionally omitted. Baseline:
commit `1f9c1f6`.

## Workstream A: Address Safety

### 1. Reproducing the 13 Unsafe Cases

Loaded directly from `phase8d1a_expanded_validator_rows.jsonl`: 13
documents, erroneous, `accepted` (not `needs_review`), failing only
address fields. 11 on `rotated_png`, 1 on `blurred_png`
(`symage_900027`), 1 on `compressed_jpeg` (`symage_900061`).

### 2-3. Address Evidence Audit (600 Documents)

New probe script (ad hoc, using the exact production zone/skip-filter
functions `_apply_ocr_employer_layout_fallbacks`/
`_apply_ocr_employee_layout_fallbacks` already use, not a
reimplementation) computed, for every document: `region_observation_count`
(raw OCR observations in the address zone) and `usable_row_count` (the
same observations after row-grouping -- the number of distinct printed
lines extraction could work with). Artifact:
`data/evaluation/results/phase8d1b_address_evidence_audit.json`.

**A clean, deterministic separator exists, measured not assumed:**

| | Employer (expects 3 rows: name, street, city/state/ZIP) | Employee (expects 2 rows: street, city/state/ZIP) |
|---|---|---|
| Correct extractions | 589/589 have `usable_row_count == 3` (0 exceptions) | 592/592 have `usable_row_count == 2` (0 exceptions) |
| Failed extractions | 9/11 have `usable_row_count == 2`; 2/11 have `usable_row_count == 3` (see below) | 8/8 have `usable_row_count == 1` (0 exceptions) |

`region_observation_count` alone does **not** separate success from
failure (both classes commonly show 3-4 raw observations) -- the
discriminator is specifically the *post-row-grouping* count, since
rotation can merge two printed lines into one row.

**The 2 employer exceptions** (`usable_row_count == 3`, i.e. "looks
complete," yet still wrong): `symage_900027` (`blurred_png`) and
`symage_900061` (`compressed_jpeg`) both have a value produced --
`"369 Pennsylvania Áve N"` vs. expected `"369 Pennsylvania Ave N"`,
`"9992 Š Jefferson St"` vs. expected `"9992 S Jefferson St"` -- a
character-level OCR misread (plain letter read as an accented one)
under blur/compression, not a structural extraction failure. This is a
different failure class (OCR recognition accuracy) that a
row-count/shape signal cannot see by design, consistent with this
project's Phase 8C.4 decision to never use OCR confidence scores as a
validation input.

### 4-5. Evidence-Based Architecture (Not Bare Null-Checking)

Considered and rejected the weakest rule (`if address is null:
needs_review`): for the 11 structurally-detectable cases,
`address_line_1 is None` is in fact perfectly correlated with
`usable_row_count` below the expected count (both are 100%-consistent
signals for this dataset) -- but a bare null-check throws away the
*reason* (no attempt vs. partial attempt vs. OCR-recognition mismatch),
which the brief's own evidence-architecture request (mirroring
`Box13CheckboxEvidence`) exists precisely to preserve for future
refinement. Implemented the full threaded-evidence path instead:

```
OCR observations
  -> compute_employer_address_evidence() / compute_employee_address_evidence()
     (parser_2026.py, read-only, reuses the exact production zone/skip-filter)
  -> ExtractionResult.employer_address_evidence / employee_address_evidence
     (AddressExtractionEvidence: region_observation_count, usable_row_count,
      parse_complete -- discrete fields, never one collapsed score)
  -> ExtractionSignals.employer_address_evidence_* / employee_address_evidence_*
     (primitives, not the extraction-side pydantic type -- validation still
      imports nothing from w2_pipeline.extraction)
  -> rules.py: _check_address_extraction_evidence
```

The validator never reopens the image, reruns OCR, or reruns parser
geometry -- it only reads `ExtractionSignals` fields already computed
during extraction, the same isolation `test_isolation.py`'s AST check
already enforces and continues to pass.

### 6. Calibrated Rule

`employer_address_extraction_incomplete` / `employee_address_extraction_incomplete`
fire when `not parse_complete and region_observation_count > 0` --
deliberately **not** `usable_row_count < 3` (which would hardcode this
one dataset's specific line-count convention into the validator itself)
and **not** `parse_complete is False` alone (which would also fire on a
route/document with genuinely zero address data, a different, exempt
case). `parse_complete` already fully captures the row-count threshold's
information for this codebase's current extraction logic
(`_address_from_two_line_block` requires `>= 2` remaining rows, so
`usable_row_count` below the expected count and `parse_complete is
False` are mathematically equivalent here) while remaining a general,
non-dataset-specific condition. `region_observation_count > 0` is the
guard against the exempt "genuinely no data" case.

### 7. Route Scoping

Scoped identically to the Phase 8C.12 checkbox-evidence-missing rule:
fires only for `signals.route in ("ocr", "mixed")`. `native_pdf` (no
image-based address extraction ever runs there) and Pipeline B's
`route="vlm"` (a different pipeline this evidence was never built for)
are exempt by the same positive allow-list, not a default-deny. This
benchmark is 100% plain-image OCR, so image-only/mixed-PDF parity was
not exercised here -- documented, not re-opened, per the brief.

### 8. Independent Issue Codes

`employer_address_extraction_incomplete` and
`employee_address_extraction_incomplete` are separate codes, both fire
independently when both parties' evidence is incomplete (tested
directly), and neither suppresses `employer_name_address_leak`/
`employer_name_layout_anomaly` or any checkbox/Box-12 issue (tested
directly). All `error` severity.

### 9. Synthetic Negative Tests

15 new tests in `tests/validation/test_rules.py`: strong employer/employee
evidence passes; missing-with-observations fires for each party
independently; zero-region-observations does not fire (the "genuinely no
data" exemption); no-evidence-supplied does not fire (missing
instrumentation is not treated as a failure); route scoping (`ocr`/
`mixed` fire, `None`/`vlm`/`native_pdf` don't); both parties' issues
coexist; the rule does not suppress employer-name issues; and,
explicitly per the brief's own distinction, a legitimately-null optional
`address_line_2` on an otherwise-complete address does **not** trigger
review (a different concept from a wholly-missing address).

### 10-12. Re-Run Expanded Validator Effectiveness

New script `run_address_evidence_validator_effectiveness.py` (extends
Phase 8D.1A's own script's signal-threading with the new evidence,
reusing its reporting helpers unchanged for direct comparability; the
8D.1A script itself is untouched). Artifacts:
`data/evaluation/results/phase8d1b_validator_effectiveness_600.json`,
`..._rows.jsonl`.

| | Before (8D.1A) | After (8D.1B) |
|---|---:|---:|
| Accepted | 596/600 | 585/600 |
| Needs review | 4/600 | 15/600 |
| Erroneous accepted (unsafe) | **13** | **2** |
| Erroneous routed to review | 4 | 15 |
| Error detection recall | 23.5% | **88.2%** |
| False review rate | 0.0% | **0.0%** (unchanged) |
| Unsafe acceptance rate | 2.17% | **0.33%** |
| Review-queue precision | 100% | 100% |

Per variant, `rotated_png` (the hardest, where all 11 structurally-
detectable cases live): unsafe acceptance **7.33% -> 0.0%**, error
detection recall 26.7% -> 100%. The remaining 2/600 unsafe documents
(`symage_900027`/`blurred_png`, `symage_900061`/`compressed_jpeg`) are
exactly the 2 OCR-character-misread cases identified in Section 3 --
**zero false-review cost** was paid to close the other 11 (`false_review_rate`
stayed 0.0% in both runs), confirming the evidence-based signal is
precise, not merely aggressive.

## Workstream B: Box 12 Blank-Code "$0.00" Semantics

### 11-13. Investigation

Per an explicit clarification during this phase (2026 IRS W-2
instructions): Box 12 represents *coded items* -- a code paired with an
amount -- not a fixed set of visually printed 12a-12d slots. Audited all
600 real slots (4 x 150 base documents) directly via FUNSD entity
linking (`_extract_box_12_entries`'s own pairing logic, without the
code-blank filter, so every slot -- not just real entries -- is
counted). Artifact:
`data/evaluation/results/phase8d1b_box12_slot_semantics_audit.json`.

| Slot state | Count |
|---|---:|
| Blank code, blank amount | 300 |
| Blank code, exactly `$0.00` | 135 |
| Blank code, nonzero amount | **0** |
| Populated code, `$0.00` | **0** |
| Populated code, nonzero amount | 165 |

**Airtight, symmetric, zero-exception evidence** in both directions
across all 600 real slots: a blank-code amount is always blank or
exactly `$0.00`, never nonzero; a populated-code amount is always
nonzero, never `$0.00`. 165 populated-code slots exactly matches the
independently-computed entry-count distribution (69 one-entry + 48
two-entry documents = 165), cross-confirming both measurements.

`Box12Entry.code`/`.amount` are both already required, non-nullable
schema fields (`code: str = Field(min_length=1, ...)`, `amount: Money`)
-- the canonical model structurally cannot represent a blank-code or
blank-amount slot at all, confirming `box_12_entries` was already
intended to mean "actual coded items," not "every printed slot."

### 14. Decision: A (Current Omission Is Correct)

No schema change. `box_12_entries` continues to represent only real,
complete, code-bearing entries. `Box12Entry`'s docstring
(`contracts/w2.py`) and `_extract_box_12_entries`'s docstring
(`external_symage.py`) were both updated to state this as a confirmed
contract (with the measured evidence cited), not an open question.

### 15. Anomalous Case: Nonzero Amount, No Code

Never observed in this dataset (0/600), but per the brief's explicit
contract, handled defensively rather than assumed impossible: a new
read-only production signal,
`compute_box_12_amount_without_code_found` (parser_2026.py), detects a
real (nonzero) Box 12 amount observation with no code observation in
the same row -- threaded through `ExtractionResult`/`ExtractionSignals`
the same way as the address evidence -- and a new validator rule,
`box_12_amount_without_code` (`error` severity, unconditional --
Box 12 amount placement is not route-dependent the way image-based
address extraction is), routes such a document to review rather than
silently dropping the entry (which `_apply_ocr_box_12_layout_fallback`
still correctly does -- a code must never be fabricated).

### 16-17. Benchmark Confirmation and Downstream

Box 12 benchmark accuracy (Phase 8D.1A's 100%) is confirmed to be based
on the 165 semantic, code-bearing entries only -- the 135 blank-code
`$0.00` placeholders were never counted as ground truth in the first
place, so there is no hidden inflation. Downstream JSON/CSV for the
known example remains exactly `box_12_entries: [{"code": "D", "amount":
"7142.00"}]`; the `$0.00` slot never appears.

### 18. Tests

- `tests/evaluation/test_external_symage.py` (+2): a populated code with
  a genuinely zero amount is still emitted (never dropped merely for
  being zero -- only a *blank* code is grounds for exclusion); a blank
  code with a nonzero amount (the anomalous, unobserved-in-practice
  shape) is dropped from ground truth, not fabricated.
- `tests/extraction/test_parser_2026.py` (+3): `compute_box_12_amount_without_code_found`
  returns `True` for an unmatched nonzero amount, `False` when the code
  matches, `False` for a `$0.00` placeholder (must never be flagged --
  it is the normal pattern, not an anomaly).
- `tests/validation/test_rules.py` (+2): the signal routes to review;
  its absence is not flagged.

## Final Verification

### 19. Downstream Happy Path (Unchanged)

Re-ran the real, fully-populated `symage_900001` example through
`validate_w2_document -> finalize_document -> export_json`/`export_csv`
with the new rules active: still `accepted`, zero issues, JSON/CSV
output unchanged. No downstream rewrite was needed (Box 12 contract did
not change).

### 20. Review Walkthrough (One Formerly-Unsafe Case)

`symage_900021-irs_w2_single_page_2026-p0` / `rotated_png` (one of the
11 now-closed unsafe cases), demonstrated end-to-end for real:

```
extraction         -> employer.address and employee.address both fully None
validation         -> needs_review
                       [employer_address_extraction_incomplete,
                        employee_address_extraction_incomplete]
start_review        -> ReviewRecord, status=pending
apply_correction x10 -> both parties' 5 address sub-fields corrected to the
                        real ground-truth values a reviewer would read off
                        the image ("288 E-470", "Grand Junction, CO 81501" /
                        "9099 Zerex St", "Colorado Springs, CO 80949")
                       -> status=in_review
revalidate          -> status=resolved, ValidationStatus.ACCEPTED
finalize_document   -> FinalizedW2, status=accepted
export_json/export_csv -> both contain the corrected addresses
```

Saved: `data/evaluation/results/phase8d1b_review_walkthrough_example.json`,
`..._example.csv`. This is the exact flow a Phase 8D.2 operator
walkthrough would exercise.

## Performance

Measured from the 600-document validator-effectiveness run: mean
1.209s/doc, median 1.192s/doc (max 7.14s, first-document PaddleOCR
warmup) -- indistinguishable from every prior Phase 8C/8D PaddleOCR-GPU
benchmark, confirming the new evidence computation (pure zone-filter/
row-grouping/regex over already-produced observations, no new OCR pass
or image operation) adds no measurable cost.

## Tests

22 new tests total (15 address-evidence rule tests, 7 address/Box-12
compute-function parser tests, 2 Box-12-semantics adapter tests, 2
Box-12-anomaly validator tests -- some counted above per-file). `ALL_RULE_NAMES`
bumped 14 -> 16 (`address_extraction_evidence`,
`box_12_amount_without_code`). Full suite: **597 tests passing**, up
from 573, zero regressions.

## Decision

**Address: A -- safety gap substantially closed.** 11 of 13 unsafe
failures now route to review with zero false-review cost, using a
measured, evidence-based signal (not a bare null-check, not a
fabricated confidence score). The remaining 2 are honestly reported as
a different, out-of-scope failure class (OCR character-recognition
accuracy under blur/compression) consistent with this project's
established boundary against OCR-confidence-based validation decisions.

**Box 12: A -- current omission is semantically correct.** Confirmed by
airtight, symmetric, zero-exception real-data evidence (600/600 slots)
and by the canonical schema's own pre-existing non-nullable field
design, now made explicit in both the schema docstring and the adapter
implementation. The one anomalous shape the brief's contract explicitly
calls out (nonzero amount, no code) is handled defensively with a new
evidence signal and validator rule, even though it does not occur in
this dataset.

## Artifacts

- `src/w2_pipeline/extraction/parser_2026.py` (`compute_employer_address_evidence`,
  `compute_employee_address_evidence`, `compute_box_12_amount_without_code_found`)
- `src/w2_pipeline/extraction/models.py` (`AddressExtractionEvidence`,
  `ExtractionResult.{employer,employee}_address_evidence`,
  `.box_12_amount_without_code_found`)
- `src/w2_pipeline/extraction/pipeline_a.py` (wiring)
- `src/w2_pipeline/contracts/w2.py` (`Box12Entry` docstring, confirmed contract)
- `src/w2_pipeline/evaluation/external_symage.py` (`_extract_box_12_entries` docstring)
- `src/w2_pipeline/validation/models.py` (`ExtractionSignals` primitives)
- `src/w2_pipeline/validation/rules.py` (`address_extraction_evidence`,
  `box_12_amount_without_code` rules)
- `src/w2_pipeline/evaluation/run_address_evidence_validator_effectiveness.py`
- `tests/extraction/test_parser_2026.py`, `tests/validation/test_rules.py`,
  `tests/evaluation/test_external_symage.py`, `tests/validation/test_integration_fixtures.py`
- `data/evaluation/results/phase8d1b_address_evidence_audit.json`
- `data/evaluation/results/phase8d1b_box12_slot_semantics_audit.json`
- `data/evaluation/results/phase8d1b_validator_effectiveness_600.json`
- `data/evaluation/results/phase8d1b_validator_rows.jsonl`
- `data/evaluation/results/phase8d1b_review_walkthrough_example.json`
- `data/evaluation/results/phase8d1b_review_walkthrough_example.csv`
