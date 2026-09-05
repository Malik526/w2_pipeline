# Validation And Routing Contract

Phase 6 implements the validation layer between extraction and downstream
output/human review. It answers a different question than either
extraction or benchmark evaluation:

```text
Extraction answers:
"What values did we read?"

Validation answers:
"Does this extracted document appear safe enough to continue automatically?"

Benchmark evaluation answers:
"Was extraction actually correct compared with known ground truth?"
```

These three must remain distinct. Validation never sees ground truth and
never re-extracts fields; the evaluator never runs in production and always
requires ground truth; extraction never decides whether its own output is
trustworthy.

```text
W2Document
+
optional extraction metadata / quality signals
        |
        v
   validate_w2_document()
        |
        v
   ValidationResult
        |
   +----+----+
   |         |
accepted  needs_review
```

## Scope

Implementation lives at:

```text
src/w2_pipeline/validation/
tests/validation/
```

- `models.py` -- `ValidationSeverity`, `ValidationStatus`, `ExtractionOutcome`,
  `ExtractionSignals`, `ValidationIssue`, `ValidationResult`.
- `redaction.py` -- PII masking for issue diagnostics.
- `rules.py` -- the ten deterministic rule functions and `run_all_rules`.
- `routing.py` -- `RoutingPolicy`/`decide_status`, kept separate from rule
  evaluation.
- `validator.py` -- `validate_w2_document`, the single entry point.
- `validate_w2.py` -- CLI (`python -m w2_pipeline.validation.validate_w2`).

Phase 6 does not implement an ML confidence model, a review UI, CSV export,
persistence, or a configuration UI for routing policy.

## Backend Neutrality

`validator.py` and every sibling module import only
`w2_pipeline.contracts.w2` (plus each other). None of them import
`w2_pipeline.extraction` (Pipeline A or Pipeline B) or
`w2_pipeline.evaluation` (which carries benchmark ground truth) --
`tests/validation/test_isolation.py` enforces this with AST-based import
inspection, the same technique Pipeline B's tests use to stay isolated from
Pipeline A.

```text
Pipeline A --+
             +--> W2Document --> validate_w2_document() --> ValidationResult
Pipeline B --+
```

The validator cannot special-case Pipeline A or PaddleOCR or the Qwen3-VL
Pipeline B challenger: it only ever sees a `W2Document` plus a
pipeline-agnostic `ExtractionSignals` value the caller constructs.
`tests/validation/test_validator.py::test_validate_w2_document_backend_neutral_for_pipeline_a_and_b_signals`
confirms identical documents produce identical issues/status regardless of
which `pipeline_id`/`route` is attached.

## Contracts

```python
class ValidationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

class ValidationStatus(str, Enum):
    ACCEPTED = "accepted"
    NEEDS_REVIEW = "needs_review"

class ExtractionOutcome(str, Enum):
    SUCCEEDED = "succeeded"
    EXTRACTION_FAILED = "extraction_failed"
    INVALID_CANONICAL_RESULT = "invalid_canonical_result"

class ExtractionSignals(BaseModel):
    pipeline_id: str | None = None
    outcome: ExtractionOutcome = ExtractionOutcome.SUCCEEDED
    route: str | None = None
    document_condition: str | None = None
    warnings: list[str] = []

class ValidationIssue(BaseModel):
    code: str
    field_path: str | None = None
    severity: ValidationSeverity
    message: str
    observed_value: Any = None
    metadata: dict[str, Any] = {}

class ValidationResult(BaseModel):
    status: ValidationStatus
    issues: list[ValidationIssue] = []
    checks_run: int
    pipeline_metadata: dict[str, Any] | None = None
```

`code` is machine-readable and stable; `message` is for humans. Issue codes
implemented in Phase 6:

```text
extraction_failure
extraction_warning
extraction_output_invalid
unsupported_document_type
tax_year_mismatch
unsupported_schema_version
required_field_missing
invalid_ssn_format
invalid_ein_format
invalid_money_value
invalid_box12_code_format
empty_entry
```

## No Unified Confidence Score

`ExtractionSignals` deliberately has no numeric confidence field. Pipeline
A (deterministic OCR/parsing) and Pipeline B (a generative VLM) have no
comparable per-field confidence semantics -- a Tesseract word-confidence
number and a VLM's implicit token-generation certainty are not the same
kind of quantity, and averaging or normalizing them into one score would
misrepresent both without empirical calibration (see
`docs/contracts/evaluation-plan.md`'s "Confidence Scores" section, which
already establishes this principle for the whole project). `warnings` is a
plain list of whatever free-text warnings the originating pipeline already
produced (e.g. `ExtractionWarning.message` values) -- reported as-is, not
scored or weighted.

## Required-Field Decisions (Evidence-Based)

Required-field rules are derived from two existing project sources rather
than invented:

1. `docs/contracts/canonical-w2-schema.md` -- which fields exist and what
   nullability represents.
2. `src/w2_pipeline/evaluation/synthetic.py` -- the project's own reference
   generator, which deliberately varies which fields are populated across
   its deterministic samples. It **always** populates
   `employee.ssn`/`first_name`/`last_name`, `employer.ein`/`name`, and
   federal Boxes 1/2/5/6; it **conditionally leaves null**
   `employee.middle_initial`, `employee.suffix`, `employer.control_number`,
   and federal Boxes 3/4/7/8/10/11 on various samples -- direct evidence
   those fields are legitimately optional for the supported workflow.

Required (an absent value is `required_field_missing`, severity `error`):

```text
employee.ssn
employee.first_name
employee.last_name
employer.ein
employer.name
federal_wages_and_taxes.box_1_wages_tips_other_compensation
federal_wages_and_taxes.box_2_federal_income_tax_withheld
federal_wages_and_taxes.box_5_medicare_wages_and_tips
federal_wages_and_taxes.box_6_medicare_tax_withheld
```

Explicitly NOT required (absence never raises an issue on its own):

```text
employee.middle_initial, employee.suffix, employee/employer address fields
employer.control_number
federal Boxes 3, 4, 7, 8, 9, 10, 11
box_12_entries, box_14_entries, tipped_occupation_codes, state_local_entries
  (each may legitimately be an empty list)
```

Boxes 3/4 (Social Security wages/tax) are treated as optional rather than
required despite being "core" federal boxes: the generator's own modeling
(`social_security_wages = wages if sample_number % 5 else None`) reflects a
real W-2 scenario (certain employees are exempt from Social Security
withholding but not Medicare), so requiring them would risk false review
routing on legitimate documents. This is a documented, adjustable
interpretation -- not an authoritative IRS rule -- and is called out here so
a future phase can revisit it with real user input if needed.

No employee/employer address subfield is required: the brief's guidance to
avoid inventing requirements, combined with there being no existing
project documentation calling out a specific address field as critical,
argues for leaving address entirely off the required list for Phase 6.

## Format Rules

- **SSN**: `^\d{3}-\d{2}-\d{4}$`. Only checked when a value is present (a
  missing SSN is already covered by the required-field rule, avoiding a
  duplicate issue for the same underlying problem).
- **EIN**: `^\d{2}-\d{7}$`, same present-only behavior.
- **Tax year / schema version / document type**: must equal the one
  currently supported production target (`2026`, `2026`, `"W-2"`) --
  `docs/contracts/system-contract.md`'s "Initial Production Target".
- **Money**: every populated monetary field (all ten `FederalWagesAndTaxes`
  money fields, every `Box12Entry.amount`, every `Box14Entry.amount`, and
  every `StateLocalEntry` money field) must be non-negative and have at
  most 2 decimal places. Both are well-established, universally true W-2
  money-field properties (dollars and cents, never negative) -- not
  invented tax-law limits. No cross-field numeric relationship (e.g. "Box 1
  should roughly equal Box 5") is implemented; the brief explicitly directs
  against inventing tax-law relationships that are not already documented.
- **Box 12 code**: `^[A-Z]{1,2}$`. Pydantic's `Box12Entry.code` already
  enforces length (1-2 characters) but not character class; real IRS Box
  12 codes are always uppercase letters, so a digit or lowercase code is
  almost certainly an extraction artifact. Severity `error` (not
  `warning`): the false-positive risk is very low, and a wrong code
  changes which box's meaning downstream systems attach to that amount.

## Domain/Structural Rule

- **Empty state/local entry** (`empty_entry`, severity `warning`): a
  `StateLocalEntry` with every field `None` carries no information and is
  likely a spurious extraction artifact (Box 12/14/tipped-code entries
  cannot be entirely empty under the canonical schema already --
  `Box14Entry` requires an amount or value, `Box12Entry`/
  `TippedOccupationCode` require a code -- so only `StateLocalEntry` needed
  this check). Kept as `warning`, not `error`: a spurious empty row is
  suspicious but not dangerous the way a malformed SSN/EIN/Box-12-code is,
  so the default routing policy leaves it as a recorded-but-not-blocking
  signal (see "Routing Policy").

No numeric cross-field consistency rule (e.g. Box 1 vs. Box 5, or state
wages vs. federal wages) is implemented -- per the brief, only rules
"strongly justified and not likely to create false positives" belong here,
and no such relationship is already documented in this project's contracts.

## Routing Policy

```python
@dataclass(frozen=True)
class RoutingPolicy:
    escalate_warnings: bool = False

def decide_status(issues, policy=None) -> ValidationStatus:
    if any error severity: return NEEDS_REVIEW
    if policy.escalate_warnings and any warning severity: return NEEDS_REVIEW
    return ACCEPTED
```

Default ("high-throughput") policy: any `error` issue routes to
`needs_review`; `warning`/`info`-only documents are `accepted`.
`RoutingPolicy(escalate_warnings=True)` ("conservative mode") additionally
routes warning-only documents to review. Routing is a pure function of the
issue list and is entirely separate from rule evaluation (`rules.py` never
imports `routing.py`), so a firm's throughput/conservativeness preference
can change without touching what counts as an issue. No configuration UI
is built in Phase 6 -- `RoutingPolicy` is a plain dataclass a caller
constructs directly.

## Null Document Handling

`validate_w2_document(None, ...)` is the path for "extraction did not
produce a valid canonical result at all" (a raised exception, or a payload
that never became a `W2Document`). It skips every field-level rule (there
is nothing to check) and returns `needs_review` with exactly one
`extraction_output_invalid` issue and `checks_run = 1`. A document that
*did* construct successfully but whose originating pipeline reported
`ExtractionOutcome.EXTRACTION_FAILED`/`INVALID_CANONICAL_RESULT` via
`ExtractionSignals.outcome` still runs every field rule (`checks_run = 10`)
in addition to the resulting `extraction_failure` issue -- both cases are
covered, but they are structurally different situations (no document to
check, vs. a document plus a signal saying something else went wrong).

## PII Redaction

`redaction.py` masks known PII-bearing canonical field paths before they
are attached to a `ValidationIssue.observed_value`:

- `employee.ssn`, `employer.ein`: masked to the last 4 characters,
  separators preserved (`"123-45-6789"` -> `"***-**-6789"`), so a reviewer
  can still spot-check which record an issue refers to.
- Employee/employer names, address lines/city/postal code, and employer
  control number: fully replaced with `"[REDACTED]"` -- a partial name or
  address mask has no standard form and little diagnostic value.
- Every other field (money amounts, Box 12 codes, state abbreviations,
  metadata) passes through unredacted -- none of it is PII on its own.

`rules.py` calls `redact_value()` for every issue that would otherwise
carry a raw SSN/EIN value (`invalid_ssn_format`/`invalid_ein_format`); no
rule currently attaches a raw name/address value to an issue at all (the
required-field-missing issue for those paths never includes
`observed_value`, since the value is `None` by definition).

## CLI

```bash
python -m w2_pipeline.validation.validate_w2 path/to/w2.json
python -m w2_pipeline.validation.validate_w2 path/to/w2.json --pipeline-id pipeline_a --route native_pdf
```

A source file that cannot be read, or that fails canonical `W2Document`
validation, is treated as a `None` document with an
`ExtractionOutcome.INVALID_CANONICAL_RESULT` signal rather than raising --
judging an already-broken artifact is exactly this command's job.

## Evaluation Isolation

`tests/validation/test_isolation.py` asserts, via AST import inspection,
that no file under `src/w2_pipeline/validation/` imports
`w2_pipeline.evaluation`, `w2_pipeline.extraction`, or
`w2_pipeline.ingestion`. Validation only ever receives a `W2Document` its
caller already produced; it never has the opportunity to see benchmark
ground truth, dataset annotations, or extraction-pipeline internals.

## Known Limitations (Phase 6)

- No ML/probabilistic confidence model, by design (see "No Unified
  Confidence Score").
- No configuration UI for `RoutingPolicy` -- a future phase would expose
  this as a firm-level setting.
- Box 3/4 (Social Security wages/tax) are treated as optional; this is a
  documented, adjustable interpretation (see "Required-Field Decisions"),
  not an authoritative rule.
- No cross-field numeric consistency checks (e.g. Box 1 vs. Box 5) --
  deliberately deferred pending a documented, justified rule.
- Address subfields are never validated for format or requiredness.
- A real integration check (see
  `docs/experiments/phase6-validation-feasibility.md`) surfaced that
  Pipeline A currently returns `employer.name = null` for every external
  Symage clean-render document checked, and that this field is not in any
  Symage record's `evaluated_field_paths` -- so no benchmark run has ever
  scored it. Phase 6 correctly flags this as `required_field_missing`;
  fixing Pipeline A's employer-name extraction is out of Phase 6's scope
  (extraction-behavior changes are explicitly excluded) and is reported as
  a discovered issue for a future task, not fixed here.
