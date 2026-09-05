# Review And Downstream Output Contract

Phase 7 implements the workflow that consumes Phase 6's `ValidationResult`
and completes the product's end-to-end story:

```text
PDF / image
    |
    v
ingestion
    |
    v
extraction (Pipeline A or Pipeline B)
    |
    v
W2Document
    |
    v
validation (Phase 6)
   / \
  /   \
accepted   needs_review
  |            |
  v            v
output      ReviewRecord (Phase 7)
               |
               v
          human correction
               |
               v
          revalidate (Phase 6, again)
               |
               v
           accepted
               |
               v
             output
```

This document covers the two new packages that implement the right-hand
(review) and terminal (output) parts of that diagram.

## Scope

```text
src/w2_pipeline/review/       tests/review/
src/w2_pipeline/downstream/   tests/downstream/
```

Phase 7 does not implement a frontend, authentication, a database, a new
AI reviewer, or an LLM-based correction mechanism. No extraction or
validation logic changed. `data/review/` is the default (gitignored)
location for review records; see `data/review/README.md`.

## Three Distinct Questions, Restated

```text
Extraction answers:
"What values did we read?"

Validation answers:
"Does this extracted document appear safe enough to continue automatically?"

Review answers:
"What does a human say the correct value actually is, and does the
corrected document now pass validation?"

Benchmark evaluation answers:
"Was extraction actually correct compared with known ground truth?"
```

Review depends on validation (it calls `validate_w2_document` directly,
never reimplementing any rule) but, like validation, never depends on
`w2_pipeline.evaluation` or `w2_pipeline.extraction` --
`tests/review/test_dependency_isolation.py` and the equivalent downstream
test enforce this via the same AST-import-inspection technique
`tests/validation/test_isolation.py` uses. Corrections are always
explicit, human-supplied values; nothing in this phase infers or predicts
a corrected value.

## Review Contracts (`src/w2_pipeline/review/`)

```python
class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"

class Correction(BaseModel):
    field_path: str
    old_value: Any
    new_value: Any
    reason: str | None = None
    reviewer_id: str | None = None
    corrected_at: datetime

class ReviewRecord(BaseModel):
    review_id: str
    document_id: str
    status: ReviewStatus = PENDING
    original_document: W2Document          # never mutated
    validation_result: ValidationResult    # pre-review (Phase 6's first call)
    corrections: list[Correction] = []     # append-only
    corrected_document: W2Document | None = None
    revalidation_result: ValidationResult | None = None
    pipeline_metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
```

`original_document` is immutable for the life of the record; a correction
never edits it in place. `corrected_document` is `None` until the first
correction, then always reflects every correction applied so far (not
just the latest one) -- `apply_correction` always starts from
`record.corrected_document or record.original_document`. Both the
pre-review (`validation_result`) and post-correction
(`revalidation_result`) `ValidationResult` values are preserved side by
side, per the brief's explicit requirement.

### State Machine (`transitions.py`)

```text
pending -> in_review -> resolved
              |  ^
              +--+   (idempotent: stays in_review while still invalid)
```

`resolved` is terminal for this phase -- there is no reopen workflow.
Every other transition (e.g. `pending` straight to `resolved`, or out of
`resolved`) raises `IllegalReviewTransitionError`. `transition_review` is
a small, explicit function rather than free-form status assignment, kept
in its own module so `workflow.py` and any future caller share one
source of truth for what is legal.

### Field-Path Corrections (`field_paths.py`)

Corrections address a field using the same dotted, index-bracketed
convention the evaluator already uses for scoring
(`w2_pipeline.evaluation.comparison.flatten_w2_document`), e.g.
`employee.ssn` or `box_12_entries[0].code`. `get_field`/`set_field_value`
navigate a `model_dump(mode="python")` copy of the document rather than
chaining `model_copy(update=...)` calls, so arbitrary depth/list-index
paths work uniformly. `W2Document`'s `extra="forbid"` config means an
unknown key can never appear in that dump, so navigating one naturally
raises `InvalidFieldPathError` -- there is no separate allow-list to
maintain. `set_field_value` always ends by calling
`W2Document.model_validate(data)`, so a syntactically valid path with a
type-invalid new value (e.g. a non-boolean into `box_13.retirement_plan`,
or a 7-character Box 12 code) raises `CorrectionValidationError` instead
of silently producing a broken document.

### Workflow Orchestration (`workflow.py`)

```python
start_review(document, validation_result, *, document_id, pipeline_metadata=None) -> ReviewRecord
apply_correction(record, *, field_path, new_value, reason=None, reviewer_id=None) -> ReviewRecord
revalidate(record, *, policy=None) -> ReviewRecord
```

- `start_review` raises `ReviewError` if given an `accepted`
  `validation_result` -- an accepted document never needs a review record
  (brief: "accepted result does not require review").
- `apply_correction` transitions `pending` -> `in_review` on the first
  correction; raises `IllegalReviewTransitionError` if the record is
  already `resolved`.
- `revalidate` calls `validate_w2_document` with a **fresh**
  `ExtractionSignals()` (default `succeeded` outcome, no warnings) rather
  than whatever signals produced the original `needs_review` result: once
  a human has reviewed and corrected the document, the *corrected content*
  is what is being judged, not the original extraction attempt. It moves
  the record to `resolved` only when the result is `accepted`; otherwise
  the record stays `in_review` (brief: "remains in_review / pending
  resolution").

None of these functions duplicate a single Phase 6 rule -- `revalidate`
is a thin wrapper around the existing `validate_w2_document`.

### Persistence (`repository.py`)

```python
class ReviewRepository(Protocol):
    def save(self, record: ReviewRecord) -> None: ...
    def get(self, review_id: str) -> ReviewRecord: ...
    def list(self) -> list[ReviewRecord]: ...
```

`FileReviewRepository` is the one implementation this phase ships: one
JSON file per record under a base directory, named `<review_id>.json` --
never a document ID, employee name, SSN, or EIN, per this project's
PII-in-filenames policy (`tests/review/test_repository.py::test_filenames_are_review_id_only_not_document_metadata`
enforces this). No production database is introduced; a future
Postgres/S3-backed implementation only needs to satisfy the same three
methods, and nothing in `workflow.py` would need to change.

## Downstream Output Contracts (`src/w2_pipeline/downstream/`)

```python
class FinalizedW2(BaseModel):
    document_id: str
    status: str = "accepted"
    schema_version: int
    tax_year: int
    document: W2Document

def finalize_document(document: W2Document, validation_result: ValidationResult) -> FinalizedW2:
    """Raises NotAcceptedError unless validation_result.status == accepted."""
```

`finalize_document` is the **only** place a `FinalizedW2` is constructed,
and the only enforcement point for "a non-accepted document never reaches
downstream output" -- every output adapter takes a `FinalizedW2`, never a
raw `W2Document` + `ValidationResult` pair, so an adapter has no path
around the gate. A `needs_review` document must complete the review
workflow above and reach an `accepted` `revalidation_result` before it can
be finalized.

### JSON Output (`json_output.py`)

`export_json(finalized, path=None) -> str` serializes `FinalizedW2` as-is
via `model_dump_json` -- Unicode preserved (no `\uXXXX` escaping), field
names/schema semantics unchanged, schema/tax-year metadata already present
via the wrapper.

### CSV Output (`csv_output.py`)

One row per document (brief's simplest-stable option). Every scalar field
(metadata, employee, employer, federal boxes, Box 13 flags, including
nested address fields) flattens into its own dotted-path column, matching
the evaluator's own flattening convention. The four repeated structures
(`box_12_entries`, `box_14_entries`, `tipped_occupation_codes`,
`state_local_entries`) do not flatten into a fixed column set -- a
document can have zero, one, or several of each -- so each is
JSON-string-encoded into a single cell (brief's option A) rather than
emitted as separate related files (option B): simpler, and the one-row-
per-document invariant survives regardless of how many repeated entries a
document has. `field_observations` is excluded (internal extraction
bookkeeping, not W-2 content).

### Adapter Boundary (`adapter.py`)

```text
FinalizedW2
    |
    +--> export_json()
    +--> export_csv()
    +--> (future) internal database / tax software / REST API / webhook /
         QuickBooks or other accounting-platform adapter
```

`OutputAdapter` is a `Protocol` (`Callable[[FinalizedW2, Path | None],
str]`) documenting and type-checking this boundary structurally --
`export_json`/`export_csv` satisfy it as plain functions, no class
hierarchy required. No vendor-specific integration (QuickBooks or
otherwise) is implemented; a future adapter only needs to accept a
`FinalizedW2` (already guaranteed `accepted`) and never touches
extraction, validation, or review code.

## Demonstration CLI (`src/w2_pipeline/review/cli.py`)

One orchestrating CLI, matching this project's existing single-purpose-
script convention (`validate_w2.py`, `run_pipeline_a.py`,
`run_pipeline_b.py`) but with subcommands, since this phase's workflow has
more than one step:

```bash
python -m w2_pipeline.review.cli validate <w2.json>
python -m w2_pipeline.review.cli review-create <w2.json> --repo-dir data/review
python -m w2_pipeline.review.cli review-correct <review_id> --repo-dir data/review --field-path employee.ssn --new-value '"123-45-6789"'
python -m w2_pipeline.review.cli review-revalidate <review_id> --repo-dir data/review
python -m w2_pipeline.review.cli export-document <w2.json> --format json|csv [--output PATH]
python -m w2_pipeline.review.cli export-review <review_id> --repo-dir data/review --format json|csv [--output PATH]
```

`--new-value` is parsed as JSON when possible (so `true`/`false`/numbers/
`null` behave correctly for boolean/numeric fields), falling back to the
raw string otherwise -- pass an explicitly quoted JSON string
(`--new-value '"1234.56"'`) to force an exact-precision money string
rather than a JSON float. A source file that fails to parse as a
canonical `W2Document` is treated as a `None` document with an
`invalid_canonical_result` signal (same convention as `validate_w2.py`);
`review-create` on such a file prints the resulting validation issues and
exits with an error, since there is no valid document to attach a review
record to.

## End-To-End Flows (Both Committed As Tests)

**Flow A (accepted)**: `tests/downstream/test_finalize.py::test_finalize_accepted_document` --
a known-good document validates as `accepted` and finalizes directly.

**Flow B (review)**: `tests/review/test_workflow.py::test_full_flow_b_end_to_end`
and, driven entirely through the CLI,
`tests/review/test_cli.py::test_cli_full_review_flow` -- a document
missing a required field validates `needs_review`, a review record is
created (`pending`), a correction is applied (`in_review`), revalidation
succeeds (`resolved`), and the corrected document exports cleanly. Both
tests additionally confirm only the corrected field differs between the
original and corrected document.

## Security / PII

- Review record filenames are the review ID only (`FileReviewRepository`);
  never a document ID, name, SSN, or EIN.
- `data/review/` is gitignored (`data/review/README.md`) -- review
  records may carry real taxpayer PII in production use and must stay
  local, same policy as `data/documents/`.
- Neither package introduces console/log statements that print raw field
  values outside of the CLI's own intentional output (the explicit
  `ValidationResult`/`ReviewRecord`/finalized-artifact JSON a user asked
  for) -- there is no separate "debug log" path to redact.
- `CorrectionValidationError` messages may echo back the invalid value a
  human just submitted via `--new-value`; this is the same actor who
  already possesses that value, not an unintended-audience leak, so no
  additional redaction was added there (unlike Phase 6's `redaction.py`,
  which guards values pulled *out of* a document into a diagnostic
  message for a different audience).

## Known Limitations

- No persistence backend beyond the filesystem (`FileReviewRepository`);
  a production deployment would implement `ReviewRepository` against
  Postgres/S3/etc.
- No reopen workflow for a `resolved` review record.
- CSV output only supports a single flat row per document; very large
  numbers of Box 12/14/state-local entries remain readable (JSON-encoded
  in one cell) but are not spreadsheet-native.
- No authentication/authorization on any CLI command or repository
  operation -- reviewer identity (`reviewer_id`) is a free-text audit
  field, not a verified identity.
