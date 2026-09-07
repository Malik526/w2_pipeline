# Phase 8D.1A - Annotation Coverage Audit, Ground-Truth Adapter Repair, and Full-Field Downstream Verification

Phase 8D.1 surfaced a real evaluation blind spot while picking a
representative document to verify downstream JSON/CSV output: the
rendered `symage_900001` W-2 visibly has a populated employer address,
employee address, a Box 12 entry, and state/local values, but the
canonical ground truth for that same document had all of them null.
This phase traces that gap through every layer -- annotation source,
benchmark adapter, production extraction, validation, downstream
serialization -- fixes what evidence supports fixing, and reports what
remains a residual, honestly measured, gap.

**Root cause, stated up front**: this was almost entirely an
**evaluation-adapter gap, not a production-extraction gap** -- the exact
same pattern Phase 8A already found once for `employer.name`. The FUNSD
source annotations always had employer/employee address, Box 12, and
state/local values; the ground-truth adapter (`external_symage.py`)
simply never mapped them, so no benchmark ever scored them, so nobody
had visibility into whether production extraction handled them. It
mostly already did (federal boxes 1-11's zone-based OCR fallback pattern
already existed and worked); address/Box 12/state-local needed new,
analogous fallback functions, which this phase built, calibrated against
real OCR output, and found two further real production bugs while doing
so (Sections 8-9).

## 1. Reproducing the Known Example

`symage_900001-irs_w2_single_page_2026-p0` (`external_clean_render`),
the exact document Phase 8D.1 used. All values below were confirmed
directly from the real Symage FUNSD annotation bundle and the real
PaddleOCR output on the actual page image -- not assumed.

## 2. Annotation Format Audit

Symage records carry six parallel annotation representations
(`ExternalAnnotationBundle`): `tokens`/`bboxes`/`ner_tags` (flat,
LayoutLM-NER-shaped, no semantic field identity), `funsd_json`
(question/answer entities with explicit `linking`, i.e. semantic
field identity + geometry via each entity's own `box`), `coco_json`
(object-detection-shaped, per-field category IDs like
`label/tax.retirement_plan`), and `yolo_txt` (normalized bounding boxes,
category index only, no text). `funsd_json` is the richest semantically
linked structure and is what the adapter already used and this phase
continued to use -- it alone carries both the text value and which
canonical concept it answers, via `linking` pairs between a `question`
entity and its `answer` entity/entities.

Two annotation-format subtleties this phase's implementation depends on,
confirmed by direct inspection, not assumed:

- Box 12's "Code" question repeats **once per slot** (12a-12d, 4 times
  per document, same question text each time) with its own answer
  entity (possibly blank); the "See instructions for box 12" question
  links to **all four amount answers in slot order** in one `linking`
  list. A flat question-text-keyed dict (`_extract_funsd_values`)
  collapses 4 identical "Code" keys to the last one -- Box 12 extraction
  reads the raw entity list directly instead (Section 5).
- State/local questions (`State`, `Employer's state ID number`, `State
  wages, tips, etc.`, `State income tax`, `Local wages, tips, etc.`,
  `Local income tax`, `Locality name`) appear exactly once per document
  (confirmed across all 150 base documents) -- no repeated-row
  reconstruction needed, unlike Box 12.

## 3. Benchmark Adapter Audit

`external_symage.py`'s `_map_scalar_field` mapped identity fields, all
11 federal money boxes, and Box 13 -- but **never** mapped `employer`'s
combined-answer address lines (2nd/3rd lines of Box c's answer;
explicitly called out as future work in a Phase 6B-era code comment),
**never** mapped `employee`'s address question at all, and had **no
mapping path whatsoever** for Box 12 or any of the seven state/local
questions. The mapping table below reflects the pre-8D.1A state:

| Source annotation (FUNSD question) | Pre-8D.1A adapter mapping | Canonical field | Pre-8D.1A covered? |
|---|---|---|---|
| Employee's SSN / first name / last name / Suff. | Mapped | `employee.ssn`/`first_name`/`middle_initial`/`last_name`/`suffix` | Yes |
| Employer identification number (EIN) | Mapped | `employer.ein` | Yes |
| Employer's name, address, and ZIP code (line 1 only) | Mapped | `employer.name` | Yes |
| Employer's name, address, and ZIP code (lines 2-3) | **Not mapped** | `employer.address.*` | **No** |
| Employee's address and ZIP code | **Not mapped at all** | `employee.address.*` | **No** |
| Control number | Mapped | `employer.control_number` | Yes |
| Wages/tax boxes 1-11 | Mapped | `federal_wages_and_taxes.*` | Yes |
| Code (x4) / See instructions for box 12 | **Not mapped** | `box_12_entries` | **No** |
| Statutory employee / Retirement plan / Third-party sick pay | Mapped | `box_13.*` | Yes |
| State / Employer's state ID number / State wages / State income tax / Local wages / Local income tax / Locality name | **Not mapped** | `state_local_entries` | **No** |

## 4. Annotation-Coverage Audit Report

New script: `src/w2_pipeline/evaluation/run_annotation_coverage_audit.py`.
Artifact: `data/evaluation/results/phase8d1a_annotation_coverage_audit.json`.

Across all 150 base documents (source-annotation, not benchmark,
coverage -- "does the FUNSD data have this at all"):

| Field | Documents with a real source value |
|---|---:|
| `employee.address` (Box f block) | 150/150 |
| `employer.address` (Box c block, lines 2-3) | 150/150 |
| Box 12 (at least one non-blank code) | 117/150 |
| `box_15_state` / `box_16_state_wages` / `box_17_state_income_tax` | 150/150 each |
| `box_15_employer_state_id_number` | 114/150 |
| `box_18_local_wages` / `box_19_local_income_tax` / `box_20_locality_name` | 0/150 each |
| `employee.suffix` | 0/150 |

**12 canonical field paths gained ground-truth coverage** this phase
adds that the pre-8D.1A adapter discarded (the audit's own
`fields_newly_covered_by_phase_8d1a` list): `employer.address.{address_line_1,city,state,postal_code,country}`,
`employee.address.{address_line_1,city,state,postal_code,country}`, and
`box_12_entries`/`state_local_entries` (as families -- see Section 5 for
why these two are scored per-index, not as one bare path).

Box 12 entry-count distribution: 33/150 documents have zero real
entries, 69/150 have one, 48/150 have two.

## 5. Ground-Truth Adapter Repair

`build_ground_truth` was refactored into a pure function,
`build_ground_truth_from_funsd(funsd_json, *, document_id)`, so it can
run directly against an already-committed `annotations/*.json` bundle
with no Hugging Face network dependency -- both the live,
record-driven `SymageW2Adapter.build_ground_truth` and the offline
`regenerate_external_ground_truth.py` script call the same one
implementation (no duplicated mapping logic).

- **Employer address**: Box c's combined answer's 2nd line (street) and
  3rd line ("City, ST ZIP", comma-separated) are now mapped, deterministic,
  never fabricated (a missing line leaves that piece unset).
- **Employee address**: a new question mapping
  (`"employee s address" -> "employee.address.address_line_1"`) plus the
  same 2-line "street" / "City, ST ZIP" parse Box c's address lines use.
- **Box 12**: `_extract_box_12_entries` reads the raw FUNSD entity list
  directly (not the flattened question-text dict), pairing each "Code"
  question (sorted by its own geometric row position) with the
  correspondingly-ordered amount answer from the shared "box 12"
  question's `linking` list. A slot is only emitted as a `Box12Entry`
  when its code is non-blank -- a `$0.00` amount with no code (a real
  pattern in this dataset, e.g. a synthetic-generator placeholder in an
  unused slot) is correctly excluded, per the schema's own requirement
  that every entry have a code.
- **State/local**: `_extract_state_local_entry` builds the one
  `StateLocalEntry` this dataset ever has directly from the flat
  question-text dict (safe here since every state/local question text is
  unique, unlike Box 12's repeated "Code").
- **A real bug found and fixed during this work, before it reached a
  committed result**: `evaluated_field_paths` initially recorded bare
  collection names (`"box_12_entries"`, `"state_local_entries"`).
  `compare_w2_documents` treats `evaluated_field_paths` as a literal list
  of `flatten_w2_document` leaf keys -- `flatten_w2_document` only ever
  produces index-qualified keys (`box_12_entries[0].code`), so the bare
  name matched neither the expected nor predicted flattened dict and was
  scored as an automatic `UNEXPECTED` failure on *every* document. Caught
  by this phase's own first expanded-benchmark smoke test (a suspicious
  `0/4` on both new collection fields), fixed by adding the real
  index-qualified paths instead: `box_12_entries[i].{code,amount}` for
  each real ground-truth entry index, and
  `state_local_entries[0].{field}` for each of the 7 sub-fields
  (unconditionally, since the state/local question is present on every
  document even when its answer is blank -- the same "question present,
  value may be null" convention the scalar per-question loop above
  already applies).

`EXTERNAL_ADAPTER_VERSION` bumped `symage-w2.phase8a.v2 ->
symage-w2.phase8d1a.v3`, the same versioning discipline Phase 8A already
established for the `employer.name` addition.

New script: `src/w2_pipeline/evaluation/regenerate_external_ground_truth.py`
-- rewrites all 150 `ground_truth/*.json` files and the manifest's
`evaluated_field_paths`/`generator_version` in place, entirely from the
already-committed `annotations/*.json` bundles (no network access).
`data/evaluation/external/` is gitignored (developer-local, regenerable
data, confirmed via `.gitignore`), so this regeneration has no git-visible
diff -- only the code/scripts and the `data/evaluation/results/*`
benchmark artifacts this phase produces are committed.

## 6. Adapter Tests

18 new tests in `tests/evaluation/test_external_symage.py`: employer
address mapping (replacing the now-outdated Phase 8A-scope test that
asserted address lines were *not* mapped), employee address mapping
(happy path, missing second line), Box 12 (second-slot-only via a blank
first code, multiple real entries, all-slots-blank yields no entries),
state/local (full row, missing optional employer-state-ID, no
state/local questions at all yields no entries).

## 7. Expanded Evaluation Contract

The scored field set is no longer the historical "24 fields" -- it is
now derived dynamically per document from `evaluated_field_paths`
(unchanged mechanism; only the adapter's own coverage expanded). Old
historical metrics are **not** rewritten: Phase 8C.2/8C.10/8C.11/8C.12's
frozen result artifacts remain valid for the narrower field set they
measured at the time. This phase's own artifacts are new files
(`phase8d1a_*`), none of them overwriting an earlier phase's.

Repeated structures score per-index (`box_12_entries[0].code`, not a
bare `box_12_entries`), matching `flatten_w2_document`'s own convention;
a document-level entry-count mismatch (predicted more or fewer entries
than ground truth) surfaces as `missing`/`unexpected` at the
out-of-range index automatically, with no special-casing needed.

## 8. Production OCR/Parser Trace

Traced each newly-covered field family from real PaddleOCR observations
on the known document (`symage_900001`) through to canonical output,
before writing any new parser code:

- **Employer/employee address**: OCR already sees the text cleanly (Box
  c: `"Timberline Trading Co."` / `"105 Penland St"` /
  `"Murphy, NC 28906"` as three separate observations; Box f similarly)
  -- classified as **B: OCR fine, parser mapping missing**. The existing
  label-based primary parser (`_value_after_label(lines, "Address 1")`)
  is built for the *internal* synthetic PDF generator's literal
  `"Label: Value"` line convention, which the external Symage renders
  (a realistic W-2 layout, no such labels) never produce -- the same
  root cause `employer.name`'s Phase 6B OCR fallback was built to solve,
  just never extended to the address lines that sit right below it.
- **Box 12**: OCR sees `"Code"`, the code letter, and each `"$X.XX"`
  amount as separate observations in two distinct columns -- classified
  as **C: parser mapping missing** (no Box-12-specific OCR fallback
  existed at all; `_parse_box_12`'s literal-label regex never matches
  Symage's format).
- **State/local**: OCR sees each box's own printed label
  (`"15 State"`, `"16 State wages, tips, etc."`, ...) as one observation
  and its value nearby -- classified as **C: parser mapping missing**,
  the same root cause as Box 12.

No OCR recognition failures (class A) or grouping issues (class B, once
address is separated from the rest) were found for any of these
families on this document; extraction gaps were consistently class C
(missing parser logic), which is why Section 9's fix is entirely new
zone-based OCR fallback functions, mirroring the existing
`_apply_ocr_federal_layout_fallbacks`/`_apply_ocr_employer_layout_fallbacks`
pattern -- not a change to OCR configuration, checkbox detection, or
employer-name logic.

## 9. Production Extraction Implemented

All new fallbacks are ratio-of-`_layout_extent` zones (this file's
existing convention, not raw image pixels), calibrated from real OCR
output and cross-checked against `rotated_png`/`compressed_jpeg`/
`blurred_png` variants of the same document, not just the clean render.

- **`_apply_ocr_employer_layout_fallbacks`** extended: the same
  `EMPLOYER_NAME_ZONE` row list used for `employer.name` now also
  supplies address lines 2-3 via a new, taller `EMPLOYER_ADDRESS_ZONE`
  (name-zone bounds are left untouched -- they are already benchmarked
  and this phase does not need to change them).
- **`_apply_ocr_employee_layout_fallbacks`** extended: a new
  `EMPLOYEE_ADDRESS_ZONE`, with `_make_employee_name_row_filter` guarding
  against a **real bug found under this dataset's rotated variant**
  (Section 10) -- the employee's own name row can shift into the address
  zone under rotation.
- **`_apply_ocr_box_12_layout_fallback`** (new): locates code-shaped
  tokens (`^[A-Z]{1,2}$`) in a code column and money-shaped tokens in an
  amount column, pairs each code with its nearest-row amount (not by
  list position -- a blank code slot prints no observation at all, so
  index-based pairing would misalign once any slot is empty), and only
  emits an entry for a non-blank code.
- **`_apply_ocr_state_local_layout_fallback`** (new): boxes 15-20 each
  get their own fixed value zone (mirroring
  `_apply_ocr_federal_layout_fallbacks`'s boxes 1-11 pattern), with a
  second **real bug found and fixed** for boxes 15's own two fields
  (Section 10).
- **`_parse_city_state_zip`** fixed: the internal generator's
  `"City ST ZIP"` line has no comma; the real form's `"City, ST ZIP"`
  does, and the un-fixed function left a trailing comma in `city`.

## 10. Two Real Bugs Found Under Rotation (Fixed, Not Papered Over)

Both were caught by testing the *rotated* variant directly, not assumed
from the clean render -- consistent with this project's established
lesson (Phase 8C.9/8C.10) that fixed-ratio zones are canvas-geometry-
sensitive.

1. **Employee name bleeding into the address zone.** Under this
   dataset's 2deg rotation, `"Steven D"` (Box e's name) sits at ratio y
   0.527-0.552 -- just inside `EMPLOYEE_ADDRESS_ZONE`'s `y0=0.53`
   boundary -- and was recovered as `employee.address.address_line_1`
   before the fix. Fixed by filtering rows that match the
   already-resolved name value (`_make_employee_name_row_filter`),
   rather than by further tightening an already-razor-thin zone
   boundary (which would just move the same collision to a different
   rotation angle).
2. **Box 15's own printed label leaking into its value.** Under
   rotation, `"15 State"` sits close enough above its value that
   `_zone_text` (which joins every observation found anywhere in a zone)
   produced `"15 State NC"` instead of `"NC"`. Fixed with a positive
   shape match (`_STATE_CODE_RE`, a bare 2-letter code) instead of
   fighting the zone boundary -- the same fix pattern as (1).

Both are direct regression tests
(`test_parser_employee_address_fallback_excludes_employee_name_row`,
`test_parser_state_local_value_does_not_leak_printed_label`), built from
real measured rotated-variant OCR coordinates, not synthetic guesses
(an earlier hand-crafted attempt at these tests produced a
razor-thin-margin false failure of its own -- documented in the test's
own comments as a cautionary note about this exact pitfall).

## 11. A Third Real Bug: State Employer ID Format Diversity

A first implementation assumed a state employer ID is EIN-shaped
(`\d{2}-\d{7}`), spot-checked against a handful of samples that happened
to match. This phase's own first full expanded-600-benchmark run caught
it as a **180/600 "missing" failure, uniform at exactly 45/150 across
all four variants** (not concentrated in `rotated_png` like the other
two bugs -- a strong signal it was a format-coverage bug, not an OCR-
quality one). The annotation-coverage audit's full sweep of all 114
non-blank state-ID values across the 150 base documents found real
formats `_EIN_RE` misses entirely: `\d{3}-\d{6}`, `\d{3}-\d{4}-\d{1}`,
even `\d{3}/\d{3}-\d{3}-\d{3}`. Replaced with `_STATE_ID_RE =
r"^\d+(?:[/-]\d+)+$"`, verified to match all 114 real values with no
false-positive risk (neither the printed label nor nearby dollar
amounts are digits-and-separators-only). A parametrized regression test
covers four of the real formats directly.

## 12. Expanded 600-Document Benchmark

Real, unmodified `run_pipeline_a.py` CLI (`--ocr-backend paddleocr
--paddle-device gpu`) against the repaired manifest -- no new benchmark
script needed for extraction itself, since the manifest's own
`evaluated_field_paths` now drives scoring automatically.

Artifacts: `data/evaluation/results/phase8d1a_expanded_pipeline_a_600.json`,
`..._predictions.jsonl`.

| | Value |
|---|---:|
| Total fields | 25,920 |
| Correct fields | 25,829 |
| **Overall field accuracy** | **99.649%** |

| Variant | Field accuracy |
|---|---:|
| `external_clean_render` | 100.0% (6480/6480) |
| `compressed_jpeg` | 99.985% (6479/6480) |
| `blurred_png` | 99.985% (6479/6480) |
| `rotated_png` | 98.627% (6391/6480) |

### New-field accuracy (populated-only vs. null-only, per Section 12's brief)

| Field | Overall | Populated in GT | Null in GT |
|---|---:|---:|---:|
| `employer.address.*` (5 sub-fields) | 589-591/600 (98.2-98.5%) | 589-591/600 (150/150 docs populated) | n/a (never null in GT) |
| `employee.address.*` (5 sub-fields) | 592/600 (98.7%) | 592/600 (150/150 docs populated) | n/a (never null in GT) |
| `box_12_entries[i].code`/`.amount` | 100% (all real entries) | 100% across 117/150 populated docs | 100% across 33/150 zero-entry docs (no spurious entries predicted) |
| `state_local_entries[0].box_15_state`/`box_16_*`/`box_17_*` | 100% | 100% (150/150 populated) | n/a |
| `state_local_entries[0].box_15_employer_state_id_number` | 100% (after Section 11's fix) | 100% across 114/150 populated docs | 100% across 36/150 blank docs |
| `state_local_entries[0].box_18/19/20` | 100% | n/a (never populated in this dataset) | 100% (600/600 correctly null) |

### Failure Taxonomy (Residual, After All Three Bug Fixes)

17 distinct (document, variant) pairs still fail an address sub-field,
concentrated in `rotated_png` (14/17): 4 are the **already-known**,
**pre-existing** `employer.name`/rotation row-merge residual
(`symage_900033/900045/900082/900146`, unchanged from Phase 8C.2 --
when that block's row grouping fails, the whole Box c block, name
included, fails together, so the address failing alongside it is the
same root cause, not a new one). The other 13 are new,
address-specific misses: `symage_900021/900026/900039/900049/900058/
900077/900081/900087/900125/900137` (`rotated_png`), plus one each on
`900027` (`blurred_png`) and `900061` (`compressed_jpeg`). Spot-checked
`900021`: `employer.name` extracts correctly but the address zone finds
fewer than 2 rows for this specific document's rotated geometry -- a
per-document zone-margin residual, not a systematic failure of the
mechanism (the same 150-document benchmark shows 98.2-98.7% accuracy on
these fields).

**Not chased further**: per this project's own established lesson
(Phase 8C.9), fixed-ratio-zone rotation robustness has diminishing
returns and real regression risk past a certain point; the two rotation
bugs that had a clean, general, non-`rotated_png`-specific fix
(Sections 10, 11) were fixed, and the remaining ~13-document residual is
reported honestly as a Category B-style gap for this specific field
family under this specific variant, not force-closed.

## 13. Validator Effectiveness Under the Expanded Contract

New script: `src/w2_pipeline/evaluation/run_expanded_validator_effectiveness.py`
(models `employer_name_observation_count`/`box_13_checkbox_evidence`
signal-threading on Phase 8C.12's own established pattern, but does not
assert byte-identical-to-frozen-Phase-8C.2 extraction the way that
phase's script did -- divergence on address/Box-12/state-local fields
is this phase's intended, expected outcome, not a regression to guard
against).

Artifacts: `data/evaluation/results/phase8d1a_expanded_validator_effectiveness_600.json`,
`..._rows.jsonl`.

| | Overall | `rotated_png` |
|---|---:|---:|
| Accepted | 596/600 (99.3%) | 146/150 (97.3%) |
| Needs review | 4/600 | 4/150 |
| Correct accepted | 583 | 135 |
| Erroneous documents | 17 | 15 |
| Erroneous routed to review | 4 | 4 |
| **Erroneous accepted (unsafe)** | **13** | **11** |
| Error detection recall | 23.5% | 26.7% |
| False review rate | 0.0% | 0.0% |
| **Unsafe acceptance rate** | **2.17%** | **7.33%** |
| Review-queue precision | 100% | 100% |

**Measured, not assumed: unsafe acceptance is no longer 0% under the
expanded contract.** The 4 needs_review documents are exactly the 4
pre-existing `employer.name` residuals
(`symage_900033/900082/900146/900045`) -- caught because `employer.name`
itself mismatches and trips the existing `employer_name_address_leak`/
`employer_name_layout_anomaly` rules, address failing alongside them on
the same documents. The other **13 erroneous documents fail *only* on
address fields** (`unsafe_acceptance_by_field_family: {"address": 13}`)
-- every one of them a fully-missing address (all five sub-fields
`None`), not a malformed-but-present one, so this phase's new
`address_format` rule (which only fires when a state/postal_code value
*exists* and is malformed) never sees anything to flag. **No validator
rule currently treats "no address extracted at all" as suspicious for a
pipeline that, when working, always populates it** -- a real, honestly-
measured safety gap this phase surfaces but does not close. Closing it
properly (an evidence-based "address extraction confidence" signal,
calibrated the way Phase 8C.12 calibrated the checkbox validator rather
than a hasty bolt-on) is recommended as follow-up work, not attempted
here at the tail of an already-large phase -- see the Decision section.

## 14. Downstream Re-Verification With a Fully-Populated Real Example

`data/evaluation/results/phase8d1a_example_full_w2.json` /
`.csv` -- the same real `symage_900001` document (**synthetic data**,
no real taxpayer information), now with employer/employee address, the
Box 12 `D`/`7142.00` entry, and the NC state/local row all present, run
through the real `validate_w2_document -> finalize_document ->
export_json`/`export_csv` path unchanged from Phase 8D.1. Confirmed
directly: JSON preserves the full nested `Address`/`Box12Entry`/
`StateLocalEntry` structures; CSV flattens address sub-fields to their
own dotted columns and JSON-encodes `box_12_entries`/
`state_local_entries` into single cells, exactly as Phase 8D.1 already
documented for the (then-always-empty) repeated structures -- no new
downstream code was needed, since `csv_output.py`'s flattening was
already generic over whatever the canonical document contains.

## 15. JSON/CSV Repeated-Structure Consistency

`box_12_entries`/`state_local_entries` CSV cells decode
(`json.loads`) back to the exact same list-of-dicts the JSON payload's
own `document.box_12_entries`/`document.state_local_entries` values are
-- verified on the fully-populated example above, the same check Phase
8D.1 already ran on synthetic fixtures now confirmed on real,
newly-populated data.

## 16. Downstream Gating (Unchanged, Reconfirmed)

Unaffected by this phase's changes -- `finalize_document`'s gate logic
never inspected which fields were populated, only `ValidationResult.status`.
Reconfirmed: the fully-populated accepted example above exports cleanly;
`symage_900033` (the known `employer.name` residual, needs_review) is
still correctly blocked.

## 17. Review-Workflow Coverage Audit

`w2_pipeline.review.field_paths`'s `get_field`/`set_field_value` are
**fully generic path-based traversal** over `W2Document.model_dump()` --
there is no fixed field allowlist. Verified directly, not assumed:
`set_field_value(doc, "employer.address.city", "Springfield")`,
`set_field_value(doc, "box_12_entries[0].code", "DD")`, and
`set_field_value(doc, "state_local_entries[0].box_15_state", "CA")` all
work today with zero code changes. **No review-workflow gap exists** for
any of the four newly-covered field families -- a reviewer can already
correct them through the existing `review-correct` CLI command exactly
as they would `employee.ssn`.

## 18. Canonical Field Coverage Matrix

`data/evaluation/results/phase8d1a_canonical_field_coverage_matrix.json`.
Every canonical `W2Document` field classified as `implemented_and_benchmarked`,
`implemented_but_weakly_benchmarked` (`box_13.statutory_employee`/
`third_party_sick_pay` -- a real, zone-calibrated OCR checkbox detector
exists, but 0/150 base documents have a ground-truth-positive example
for either flag, so correctness is unverified by this benchmark, a
limitation that predates this phase and is unchanged by it),
`schema_supported_extraction_ready_annotation_unavailable` (`employee.suffix`,
both parties' `address_line_2`, federal boxes 7/8/9/10/11,
`box_14_entries`/`tipped_occupation_codes`, state/local boxes 18-20 --
real parser logic exists for some of these, real OCR-zone fallback logic
exists for others, but this dataset's annotations never populate any of
them, confirmed directly rather than assumed), or
`internal_bookkeeping_not_scored` (`field_observations`).

## 19. Historical Metrics Preserved

Phase 8C.2/8C.10/8C.11/8C.12/8D.1's committed result artifacts are
byte-for-byte untouched. This phase's artifacts are new files under the
`phase8d1a_*` prefix. The expanded adapter revealed additional
annotation coverage not represented in the earlier canonical GT adapter,
so Phase 8D.1A introduces a broader evaluation contract; prior metrics
remain valid for their original scored field set.

## 20. Performance

Measured from the expanded 600-document benchmark runs (PaddleOCR GPU,
same hardware/config as every other Phase 8C/8D benchmark):

| | Mean/doc |
|---|---:|
| Extraction (`run_pipeline_a.py`, includes PaddleOCR) | 1.35s |
| Extraction + validation (`run_expanded_validator_effectiveness.py`) | 1.23s (median 1.21s) |

Both numbers land in the same ~1.2-1.35s/doc range every prior Phase
8C/8D PaddleOCR-GPU benchmark has measured (dominated by PaddleOCR
itself) -- confirming the new address/Box-12/state-local OCR fallbacks
add no measurable incremental cost, as expected: they are pure-Python
zone-filter/regex operations over already-produced text observations,
the same complexity class as the pre-existing federal-box fallback they
mirror, not a new OCR pass or image operation.

## 21. Tests

- `tests/evaluation/test_external_symage.py`: +18 (adapter mapping for
  all four new field families, edge cases, the outdated Phase 8A-scope
  test updated to its new, intended behavior).
- `tests/extraction/test_parser_2026.py`: +10 (address/Box-12/state-local
  OCR fallback happy paths, both rotation-bug regression tests built
  from real measured coordinates, the state-ID-format parametrized
  regression test).
- `tests/validation/test_rules.py`: +5 (new `address_format` rule: valid
  address passes, valid ZIP+4 passes, invalid state code detected,
  invalid postal code detected, a wholly-null address is never flagged).
- `ALL_RULE_NAMES` count bumped 13 -> 14 (`test_rules.py`,
  `test_integration_fixtures.py`).

Full suite: **573 tests passing** (up from 564 before this phase's test
additions), zero regressions.

## 22. New Validation Rule: Address Format

`_check_address_format` (Phase 8D.1A): a two-letter USPS state/territory
code and a 5-digit-or-ZIP+4 postal code for both `employer.address` and
`employee.address` -- the same "format, not content" scope SSN/EIN
format checks already have. Deliberately does **not** add city-emptiness
or address/label-leak checks: this benchmark's real addresses come from
a single unlabeled OCR block with no annotated failure examples of
either kind to calibrate against, so adding them now would be exactly
the unevidenced-threshold pattern the rest of this validator module
avoids (see `rules.py`'s own module docstring). Box 12/state-local money
and code-format validity needed **no new rule at all** -- the pre-existing,
schema-generic `_check_monetary_fields_valid`/`_check_box_12_code_format`/
`_check_no_empty_state_local_entries` rules already iterate
`document.box_12_entries`/`state_local_entries`, so they started
covering the newly-populated real values automatically.

## Decision

**B/A hybrid, reported honestly rather than forced.** Ground-truth
coverage is now substantially repaired (12 field paths, ~150-190 sub-
field observations per document depending on Box 12 slot count),
production extraction was built and verified for every newly-covered
family (99.6% overall field accuracy, 98.6% on the hardest variant),
downstream JSON/CSV already preserved them with zero new code, and the
review workflow already supports correcting them with zero new code.

Two residual gaps remain, honestly measured rather than hidden or
force-closed:

1. **Extraction**: address recovery under `rotated_png` has a
   ~13-document (of 150) zone-margin residual beyond the 4 pre-existing
   `employer.name` cases (Section 12).
2. **Validation** (the more consequential one): expanding ground-truth
   coverage revealed unsafe acceptance is no longer 0% -- **2.17%
   overall, 7.33% on `rotated_png`** -- because no current rule treats a
   fully-missing address as suspicious for a pipeline that, when
   working, always populates one (Section 13). This is exactly the kind
   of blind spot expanding evaluation coverage is supposed to surface;
   surfacing it, not silently re-declaring "0% unsafe acceptance" from
   the pre-expansion baseline, is this phase's job. Closing it with a
   properly evidence-calibrated signal (not a hasty bolt-on) is
   recommended as immediate follow-up work before this pipeline's
   address fields are treated as production-trustworthy without human
   review.

## Artifacts

- `src/w2_pipeline/evaluation/external_symage.py` (adapter repair)
- `src/w2_pipeline/evaluation/regenerate_external_ground_truth.py`
- `src/w2_pipeline/evaluation/run_annotation_coverage_audit.py`
- `src/w2_pipeline/evaluation/run_expanded_validator_effectiveness.py`
- `src/w2_pipeline/extraction/parser_2026.py` (address/Box-12/state-local
  OCR fallbacks, `_parse_city_state_zip` comma fix)
- `src/w2_pipeline/validation/rules.py` (`address_format` rule)
- `tests/evaluation/test_external_symage.py`,
  `tests/extraction/test_parser_2026.py`, `tests/validation/test_rules.py`,
  `tests/validation/test_integration_fixtures.py`
- `data/evaluation/results/phase8d1a_annotation_coverage_audit.json`
- `data/evaluation/results/phase8d1a_canonical_field_coverage_matrix.json`
- `data/evaluation/results/phase8d1a_expanded_pipeline_a_600.json`
- `data/evaluation/results/phase8d1a_expanded_pipeline_a_600_predictions.jsonl`
- `data/evaluation/results/phase8d1a_expanded_validator_effectiveness_600.json`
- `data/evaluation/results/phase8d1a_expanded_validator_rows.jsonl`
- `data/evaluation/results/phase8d1a_example_full_w2.json`
- `data/evaluation/results/phase8d1a_example_full_w2.csv`
