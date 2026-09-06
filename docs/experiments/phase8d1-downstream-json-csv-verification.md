# Phase 8D.1 - Downstream JSON/CSV Verification

Verifies that a validated, finalized `W2Document` produces correct,
stable, usable downstream JSON and CSV output, and that a document
requiring review cannot be silently exported. This is a
downstream-contract verification phase: no OCR, parser, checkbox,
validator, employer-name, or canonical-schema change. All findings below
were checked against real code and, where the brief asked for it, real
Phase 8C.11/8C.12 predictions -- not assumed from reading the source.

## 1. Current Downstream Architecture

`src/w2_pipeline/downstream/` (Phase 7, already substantially built
before this phase):

```text
W2Document + ValidationResult
    -> finalize_document()          (finalize.py -- the only gate)
    -> FinalizedW2                  (models.py)
        -> export_json()            (json_output.py)
        -> export_csv()             (csv_output.py)
        -> OutputAdapter protocol   (adapter.py, structural typing only)
```

- Input contract: `export_json`/`export_csv` both take exactly one
  `FinalizedW2`, never a raw `W2Document`. `FinalizedW2` can only be
  produced by `finalize_document(document, validation_result)`, which
  raises `NotAcceptedError` unless `validation_result.status ==
  ValidationStatus.ACCEPTED` -- confirmed as the only real call site of
  `FinalizedW2(...)` anywhere in this codebase (`review/cli.py`'s
  `_handle_export_document`/`_handle_export_review` both call
  `finalize_document` first).
- Export is already gated by validation status, before this phase.
- JSON shape: `FinalizedW2` dumped as-is (`document_id`, `status`,
  `schema_version`, `tax_year`, full nested `document`).
- CSV shape: one row, every scalar field flattened to a dotted-path
  column (`employee.first_name`, not `employee_first_name`), four
  repeated structures JSON-encoded into one cell each.
- Existing tests (`tests/downstream/`) already covered: basic JSON/CSV
  shape, unicode preservation, repeated-structure JSON-encoding, null ->
  empty-cell, `field_observations` exclusion, `NotAcceptedError` on a
  `needs_review` document, `OutputAdapter` protocol conformance. Not
  previously covered (added this phase): boolean type/representation,
  money exact-precision format, SSN/EIN leading-zero preservation, CSV
  escaping, export determinism, a real Phase 8C.12 residual document
  through the gate, and the `FinalizedW2` direct-construction bypass
  (Section 4).

No working code needed a rewrite; verification surfaced one real,
narrow gap (Section 4), fixed with the smallest change that closes it.

## 2. JSON Verification

Real document used: `symage_900001-irs_w2_single_page_2026-p0` /
`external_clean_render` from
`data/evaluation/results/phase8c12_checkbox_signals_600_predictions.jsonl`
(a real Phase 8C.11 extraction, `retirement_plan=true`, validated
`accepted` using its real `pipeline_metadata`-carried checkbox/employer-
name evidence -- not a synthetic fixture). Saved as
`data/evaluation/results/phase8d1_example_w2.json` (**synthetic W-2
data**: the entire Symage benchmark dataset is synthetic; no real
taxpayer information appears anywhere in this artifact).

```json
{
  "document_id": "symage_900001-irs_w2_single_page_2026-p0:external_clean_render",
  "status": "accepted",
  "schema_version": 2026,
  "tax_year": 2026,
  "document": {
    "metadata": { "document_type": "W-2", "tax_year": 2026, "...": "..." },
    "employee": { "ssn": "242-48-4959", "first_name": "Steven", "...": "..." },
    "employer": { "ein": "75-5696876", "name": "Timberline Trading Co.", "...": "..." },
    "federal_wages_and_taxes": { "box_1_wages_tips_other_compensation": "114858.00", "...": "..." },
    "box_13": { "statutory_employee": false, "retirement_plan": true, "third_party_sick_pay": false },
    "box_12_entries": [], "box_14_entries": [], "tipped_occupation_codes": [], "state_local_entries": [],
    "field_observations": []
  }
}
```

- **Structure**: canonical nesting preserved exactly; no duplicate
  fields; `field_observations` (internal bookkeeping) present here but
  intentionally excluded from CSV (Section 5).
- **Types, verified directly**: booleans are real JSON `true`/`false`
  (`payload["document"]["box_13"]["retirement_plan"] is True`, not the
  string `"true"`). Money (`Decimal`) serializes as an exact-precision
  **string** (`"114858.00"`), confirmed with a constructed
  `Decimal("114857.99")` value -- no float artifact is possible because
  the value never passes through a binary float at all. `null` stays
  JSON `null`, never coerced to `""`. SSN (`"012-34-5678"`, constructed)
  round-trips with its leading zero intact -- both are `str` fields, not
  `int`, end to end.
- **Determinism**: `export_json(finalized) == export_json(finalized)` on
  a second call -- **byte-identical**, not merely semantically equal
  (Pydantic's `model_dump_json` is deterministic for a fixed model
  instance and schema).

## 3. CSV Verification

Same document, same finalized wrapper, exported via `export_csv`. Actual
header + row saved to `data/evaluation/results/phase8d1_example_w2.csv`:

```text
box_12_entries,box_13.retirement_plan,box_13.statutory_employee,box_13.third_party_sick_pay,box_14_entries,employee.address.address_line_1,...,employee.first_name,employee.last_name,employee.middle_initial,employee.ssn,employee.suffix,...,employer.ein,employer.name,federal_wages_and_taxes.box_1_wages_tips_other_compensation,...,metadata.document_id,...,state_local_entries,tipped_occupation_codes
[],True,False,False,[],,...,Steven,Armstrong,D,242-48-4959,,...,75-5696876,Timberline Trading Co.,114858.00,...,symage_900001-...,...,[],[]
```

- **One row per document**: confirmed, and consistent across repeated
  single-document calls (Section 6, batch composition check).
- **Column order**: `sorted(row)` -- alphabetical by dotted path,
  verified deterministic (`header.split(",") == sorted(header.split(","))`).
- **Flattening**: dotted paths (`employee.first_name`,
  `federal_wages_and_taxes.box_1_wages_tips_other_compensation`,
  `box_13.retirement_plan`) -- this project's actual, pre-existing
  convention (matching `w2_pipeline.evaluation.comparison.flatten_w2_document`),
  not the underscore convention the brief's own examples used
  illustratively; documented as the real convention, not reinvented.
- **CSV types, verified directly, not assumed**:
  - Booleans: Python's `str(bool)` -- **`"True"`/`"False"`**, capitalized,
    *not* JSON-style `true`/`false` and *not* `1`/`0`. This is the one
    genuine JSON/CSV representation difference found (Section 5);
    deterministic, but previously undocumented -- now documented in
    `docs/contracts/review-and-downstream-output.md`.
  - Null/missing optional: empty cell (`""`).
  - Money: identical exact-precision string to JSON (`"114858.00"` in
    both).
  - `False` vs. `null`: confirmed distinguishable -- a `False` checkbox
    cell reads `"False"` (never empty); a `null` suffix cell reads `""`
    (never `"False"` or `"None"`).
- **Escaping**: constructed `Smith, "Jones" & O'Brien Corp` as
  `employer.name` (the real dataset has no naturally comma/quote-bearing
  values). `csv.DictWriter` (already in use, not hand-built
  concatenation) quotes it correctly; `csv.DictReader` round-trips the
  exact original string.
- **Determinism**: byte-identical on repeated export, same as JSON.

## 4. Real Finding: `FinalizedW2` Construction Bypass (Fixed)

`finalize.py`'s docstring claimed "there is no public constructor path
that skips validation" -- true in the sense that no code in this
repository actually does it, but not true as a type-level guarantee.
Verified directly:

```python
sneaky = FinalizedW2(document_id="x", status="accepted", schema_version=2026,
                      tax_year=2026, document=a_needs_review_document)
export_json(sneaky)  # succeeded -- no error, no gate
```

Because `status: str = "accepted"` accepted *any* string, a caller
constructing `FinalizedW2` directly (bypassing `finalize_document`
entirely) could set any status -- including fabricating `"accepted"` for
a document that was never validated, or even leaving `status="needs_review"`
and having both adapters serialize it anyway, since neither adapter
re-checks anything beyond "is this object a `FinalizedW2` instance."

**Fix** (smallest change that closes the literal-status hole):
`status: Literal["accepted"] = "accepted"`. `finalize_document`'s only
real call sites already always pass `"accepted"` at that point (it
already raised before reaching the constructor otherwise), so this is
behavior-neutral for every legitimate caller and verified
zero-regression against the full suite. A dedicated regression test
(`test_finalized_w2_cannot_be_constructed_with_a_non_accepted_status`)
confirms `FinalizedW2(status="needs_review", ...)` now raises
`pydantic.ValidationError`.

**Residual, explicitly not fixed**: `FinalizedW2` still cannot verify
that the `document` field it holds was the one actually checked -- it
does not retain a `ValidationResult` reference. Closing that would mean
re-validating inside the model itself, duplicating `finalize_document`'s
responsibility rather than trusting it once, in one place. Left as a
caller-discipline invariant (documented, not silently accepted as
"already solved") -- consistent with "verify and tighten," not "rebuild
the gate mechanism."

## 5. JSON/CSV Consistency Check

Built a field-by-field comparison (`run_downstream_verification.py`):
flatten the JSON `document` payload to the same dotted-path keys CSV
uses, normalize (`None -> ""`, `bool -> str(bool)`), and compare against
the corresponding CSV cell for every scalar field.

**Result on the real example document: 40/40 scalar fields match, 0
mismatches.** The four repeated structures (`box_12_entries`,
`box_14_entries`, `tipped_occupation_codes`, `state_local_entries`)
decode identically from their JSON-string CSV cells back to the same
Python structure as the JSON payload's own value for that field
(cross-checked on a second, denser synthetic document with all four
populated plus a suffix -- see `run_downstream_verification.py`'s
manual verification during this phase).

**One intentional, documented format difference**: `field_observations`
is present in JSON (full internal bookkeeping list) and absent from CSV
(`_EXCLUDED_FIELDS`) -- pre-existing, intentional (internal extraction
bookkeeping, not W-2 business content), reconfirmed still true.

No omitted fields, wrong flattening, field swaps, stale mappings,
boolean inversion, or renamed columns were found.

## 6. Export-Gating Verification

**A. Accepted document**: the real Phase 8C.11 example above -- JSON and
CSV export both succeed.

**B. Needs-review document, real data**: loaded the actual Phase 8C.12
residual `symage_900033-irs_w2_single_page_2026-p0` / `rotated_png`
(one of the four known `employer.name` failures) with its real
`pipeline_metadata` signals.

```text
validation_status: needs_review
validation_issue_codes: [employer_name_address_leak, employer_name_layout_anomaly]
finalize_document(...) -> NotAcceptedError:
  "Cannot finalize a document with validation status 'needs_review';
   only 'accepted' documents may become downstream output."
```

Export is blocked before any file is written -- `csv_output.py` builds
its entire row into an in-memory string before ever touching a path, and
`finalize_document` raises before either adapter is even called, so
there is no partial-output risk in the normal call path.

**C. Resolved/revalidated document**: not re-exercised end-to-end in
this phase -- `tests/review/test_workflow.py::test_full_flow_b_end_to_end`
and `tests/review/test_cli.py::test_cli_full_review_flow` (Phase 7,
pre-existing, still passing) already cover
`needs_review -> correction -> revalidation -> accepted -> export`
completely; duplicating that here would re-implement, not verify, the
review workflow, which is out of this phase's scope.

## 7. Representative Values Tested

Real Phase 8C.12 document (checked `retirement_plan`, populated money,
names, SSN/EIN, tax year) plus targeted synthetic constructions for
values the real Symage dataset never produces (address is always null in
this dataset; suffix is never generated by
`w2_pipeline.evaluation.synthetic`, box_12/14/state_local/tipped-codes
populate on ~20-70% of synthetic samples depending on seed): unchecked
`retirement_plan`, a document with address + Box 12/14 + state/local +
tipped-occupation-code entries + suffix all populated simultaneously (for
Section 5's denser JSON/CSV consistency pass), a leading-zero SSN, and a
comma/quote/apostrophe-bearing employer name.

## 8. Sensitive Identifier Handling

SSN/EIN are `str | None` in the canonical schema (not `int`), confirmed
by direct construction and export: `"012-34-5678"` -> `"012-34-5678"` in
both JSON and CSV, no leading-zero loss, no scientific notation (CSV
never coerces the cell to a number type -- it is written as a quoted/
plain string by `csv.DictWriter`, and a spreadsheet application opening
the raw file may reformat on *display*, but the file's own bytes are
never altered), no truncation.

## 9. Null/Empty/Missing/False/Zero Behavior

| Canonical value | JSON | CSV |
|---|---|---|
| `None` (optional field) | `null` | `""` (empty cell) |
| `False` | `false` | `"False"` |
| `Decimal("0.00")` | `"0.00"` | `"0.00"` |
| Missing/empty repeated structure | `[]` | `"[]"` (JSON-encoded empty array in the cell) |

`False` and `null` are never conflated in either format -- confirmed
with a dedicated test (`test_export_csv_false_is_distinguishable_from_null`)
setting `retirement_plan=False` alongside a `null` `employee.suffix` on
the same document and asserting the two cells differ (`"False"` vs.
`""`).

## 10. Round-Trip Sanity Check

No importer exists (correctly out of scope -- not built). Lightweight
semantic round-trip only: `export_json` -> `json.loads` -> compare
business values to the source `W2Document` (done throughout Sections
2-5); `export_csv` -> `csv.DictReader` -> compare normalized row values
to canonical source (done throughout Sections 3, 5, 6). Both round-trip
cleanly for every field checked.

## 11. Batch Behavior

**No batch export function exists**, confirmed by inspection
(`export_json`/`export_csv` each take exactly one `FinalizedW2`; the CLI's
`export-document`/`export-review` are both single-document) and not
added -- out of scope per the brief ("do not create unnecessary batch
architecture"). Verified instead that calling the single-document
primitive repeatedly composes correctly: 3 real, distinct, accepted Phase
8C.12 documents each exported individually produce **identical CSV
headers** (same column set/order every time) and **distinct
`metadata.document_id`** values (no cross-contamination between calls).
JSON has no documented list/envelope behavior either -- one `FinalizedW2`
per call, as designed.

## 12. Error Behavior

`finalize_document` raises `NotAcceptedError` (an explicit, typed
exception, not a silent partial artifact) before either adapter is ever
invoked for a non-accepted document -- verified in Section 6 with real
data. `export_csv`/`export_json` build their complete output in memory
(`io.StringIO()` / `model_dump_json()`) before writing to `path`, so a
mid-serialization failure cannot leave a truncated file; writing to an
unwritable/nonexistent-parent path raises a standard `OSError` from
`Path.write_text`, an explicit failure rather than a misleading
"successful" empty/partial file. No format-choice validation gap exists:
the CLI's `_export` helper only recognizes `"csv"` vs. everything-else-as-
JSON (unchanged, out of this phase's scope to alter).

## 13. Performance

Measured directly against all 596 real, accepted Phase 8C.12 predictions
(separately from PaddleOCR extraction, which is not part of this
measurement):

| | Total (596 docs) | Mean/doc |
|---|---:|---:|
| JSON serialization | 7.4 ms | 12.4 microseconds |
| CSV serialization | 38.8 ms | 65.1 microseconds |

Both negligible next to PaddleOCR's ~1.2 seconds/document (roughly
5 and 4 orders of magnitude smaller, respectively). CSV is slower than
JSON (sorting + per-field flattening + the `csv` module's own quoting
logic vs. Pydantic's single `model_dump_json` call) but still
microsecond-level.

## 14. Tests

13 new tests, zero unintended regressions:

- `tests/downstream/test_json_output.py` (+5): booleans are real JSON
  booleans, money is an exact string (constructed with `Decimal(...)`,
  not a raw string via `model_copy` -- see note below), null stays
  `null`, SSN leading zero preserved, byte-identical repeated export.
- `tests/downstream/test_csv_output.py` (+8): boolean representation
  pinned to `"True"`/`"False"`, `False` vs. `null` distinguishability,
  money matches JSON's exact string, SSN leading zero preserved, comma/
  quote/apostrophe escaping round-trips, column order is deterministically
  sorted, byte-identical repeated export.
- `tests/downstream/test_finalize.py` (+1): the `FinalizedW2` bypass
  regression test (Section 4).

**Construction note surfaced during test-writing**: `model_copy(update=
{...})` does not re-run Pydantic validation/coercion, so passing a raw
Python `str` for a `Decimal` (`Money`) field via `model_copy` silently
leaves the field as a `str` rather than coercing it -- `_check_monetary_fields_valid`
then raises a `TypeError` (`'<' not supported between 'str' and 'int'`)
instead of a clean `ValidationIssue`, when validation is run against
such a document. This is a test-construction pitfall (existing tests
already avoid it, e.g. `Box12Entry(code="D", amount="500.00")` uses the
real constructor), not a reachable production defect -- `parser_2026.py`
always constructs canonical models through validated constructors, never
`model_copy` with a mismatched raw type for a `Decimal` field. Noted here
rather than "fixed," since altering validator internals to defend
against a construction pattern extraction code never uses is out of this
phase's scope (`Do NOT: change validator logic`).

Full suite: **547 tests passing**, up from 534, zero unintended
regressions.

## 15. Artifacts

- `data/evaluation/results/phase8d1_example_w2.json` -- real,
  accepted, checked-retirement-plan example (**synthetic W-2 data**, no
  real taxpayer information).
- `data/evaluation/results/phase8d1_example_w2.csv` -- the same
  document's CSV export.
- `data/evaluation/results/phase8d1_downstream_verification.json` --
  the full machine-readable verification report (determinism, JSON/CSV
  consistency, money/boolean/SSN checks, gating, batch composition,
  performance) this document summarizes, reproducible via
  `python -m w2_pipeline.evaluation.run_downstream_verification`.

## 16. Actual Final Contracts

See Sections 2 and 3 above for the actual emitted JSON structure and CSV
header/row -- both taken directly from the saved example artifacts, not
written aspirationally.

## 17. Decision

**A. Production-ready downstream contract**, with one gap found and
closed during this verification pass (Section 4), not before it. JSON
and CSV are both correct, deterministic, and consistent with each other
(40/40 fields, 0 mismatches on the real example); SSN/EIN integrity,
money precision, and null/false distinguishability all verified directly
against real and constructed data; review gating was already correctly
enforced by `finalize_document` and is now additionally enforced at the
type level (`Literal["accepted"]`) against a bypass path that existed
only in principle (no code in this repository ever exercised it); no
internal/debug data leaks into CSV, and the one JSON/CSV field
difference (`field_observations`) is intentional and documented; all
tests pass.

## Artifacts

- `src/w2_pipeline/downstream/models.py` (`FinalizedW2.status: Literal["accepted"]`)
- `src/w2_pipeline/evaluation/run_downstream_verification.py`
- `tests/downstream/test_json_output.py`, `test_csv_output.py`, `test_finalize.py`
- `data/evaluation/results/phase8d1_example_w2.json`
- `data/evaluation/results/phase8d1_example_w2.csv`
- `data/evaluation/results/phase8d1_downstream_verification.json`
- `docs/contracts/review-and-downstream-output.md` (updated contract details)
