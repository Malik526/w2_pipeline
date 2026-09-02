# Codex Implementation Brief - Phase 1

## Canonical W-2 Data Contract / Pydantic Schema

## Objective

Implement the canonical W-2 data contract for the W-2 Pipeline project.

Phase 1 turns the official 2026 Form W-2 into the single typed internal
structure every future extractor must produce:

```text
OCR pipeline ----|
                 |-> Canonical W-2 model
Vision model ----|
```

The output of Phase 1 is the contract layer only: Pydantic models, package
structure, structural tests, and documentation updates. Do not implement
extraction, OCR, vision, validation engines, persistence, export, or UI.

## Required Context

Before making changes, read:

- `AGENTS.md`
- `README.md`
- `docs/contracts/system-contract.md`
- `docs/contracts/workflow-and-architecture.md`
- `docs/contracts/evaluation-plan.md`
- `docs/references/irs/README.md`
- `docs/project-state.md`

Use the official 2026 W-2 reference PDF as the source of truth for the field
inventory:

```text
docs/references/irs/2026_W2.pdf
```

Do not derive the schema from older W-2 examples.

## Phase Boundary

Phase 1 must implement only the canonical schema contract.

Do not implement:

- OCR
- PyMuPDF extraction
- regex parsing
- vision models
- Hugging Face inference
- tax-year detection logic
- year-specific historical adapters
- synthetic W-2 generation
- benchmark datasets
- evaluation runners
- business-rule or tax-rule validation engines
- confidence thresholds
- CSV export
- database persistence
- FastAPI routes
- frontend UI
- RAG, embeddings, vector databases, or document chunking

## Package Structure

Create a small Python package for the contract layer. Prefer this structure
unless existing project conventions have changed:

```text
pyproject.toml
src/
  w2_pipeline/
    __init__.py
    contracts/
      __init__.py
      w2.py
tests/
  contracts/
    test_w2_contract.py
```

Use Pydantic v2 and Python typing throughout. Configure tests with pytest.

The contract should be importable as:

```python
from w2_pipeline.contracts.w2 import W2Document
```

## Model Shape

Implement the canonical document around this conceptual shape:

```text
W2Document
|-- metadata
|-- employee
|-- employer
|-- federal_wages_and_taxes
|-- box_12_entries[]
|-- box_13
|-- box_14_entries[]
|-- tipped_occupation_codes[]
|-- state_local_entries[]
```

Define these supporting models:

- `W2Metadata`
- `Address`
- `Employee`
- `Employer`
- `FederalWagesAndTaxes`
- `Box12Entry`
- `Box13Flags`
- `Box14Entry`
- `TippedOccupationCode`
- `StateLocalEntry`
- `W2Document`

## Metadata Requirements

`W2Metadata` must include:

- `document_type`
- `tax_year`
- `schema_version`
- `document_id`
- `source_filename`
- `source_file_type`

Use constrained literal or enum values where useful for structure, but do not
implement tax-year detection. The only required initial values are:

```text
document_type: W-2
tax_year: 2026
schema_version: 2026
```

The schema should be version-aware without implementing support for historical
years.

## Employee Model

`Employee` must account for the employee fields on the official 2026 W-2:

- SSN
- first name
- middle initial
- last name
- suffix
- address

The employee address should use the shared `Address` model.

## Employer Model

`Employer` must account for:

- EIN
- name
- address
- control number, where applicable

The employer address should use the shared `Address` model.

## Address Model

`Address` should be reusable for employee and employer addresses. Model enough
structure to represent the W-2 address blocks without encoding extraction
layout:

- address line 1
- address line 2
- city
- state
- postal code
- country, optional

Do not add address normalization or geocoding.

## Federal Wages And Taxes

`FederalWagesAndTaxes` must model W-2 Boxes 1 through 11:

- Box 1: wages, tips, other compensation
- Box 2: federal income tax withheld
- Box 3: social security wages
- Box 4: social security tax withheld
- Box 5: Medicare wages and tips
- Box 6: Medicare tax withheld
- Box 7: social security tips
- Box 8: allocated tips
- Box 9: verification code
- Box 10: dependent care benefits
- Box 11: nonqualified plans

Use `Decimal`, not `float`, for monetary values. Box 9 may be blank or contain
a non-money code/value depending on IRS form usage, so do not force it into a
money type if the 2026 reference indicates otherwise.

Example monetary style:

```python
box_1_wages: Decimal | None
```

## Box 12

Model Box 12 as repeated code/value entries:

```text
box_12_entries: list[Box12Entry]
```

`Box12Entry` should include:

- code
- amount

Use `Decimal` for the amount. Do not model Box 12 as four unrelated hard-coded
fields in the canonical representation.

Do not encode the full IRS Box 12 business-rule table in Pydantic. Structural
typing is enough for Phase 1. If a constrained code type is used, keep it
grounded in the official 2026 W-2 instructions and avoid turning it into a
business-rule validator.

## Box 13

`Box13Flags` must include exactly these boolean fields:

- statutory employee
- retirement plan
- third-party sick pay

Use booleans for checked/unchecked structural representation. Do not infer
tax consequences from them.

## Box 14

Box 14 must handle both flexible other entries and the 2026 tipped occupation
field.

Model Box 14a as repeated flexible entries:

```text
box_14_entries: list[Box14Entry]
```

`Box14Entry` should include:

- label
- amount or value

Use a representation that supports both money-like and text-like values without
forcing extraction pipelines to invent incompatible output shapes.

Model Box 14b separately as:

```text
tipped_occupation_codes: list[TippedOccupationCode]
```

`TippedOccupationCode` should represent Treasury Tipped Occupation Code(s) from
the official 2026 form.

## State And Local Fields

Model Boxes 15 through 20 as repeated entries:

```text
state_local_entries: list[StateLocalEntry]
```

`StateLocalEntry` must account for:

- Box 15: state
- Box 15: employer state ID number
- Box 16: state wages, tips, etc.
- Box 17: state income tax
- Box 18: local wages, tips, etc.
- Box 19: local income tax
- Box 20: locality name

Use `Decimal` for state/local monetary values.

## Nullability And Extraction State

Nullability must be intentional. The model should distinguish these concepts:

- blank valid field
- field absent or not applicable
- extraction failed

Do not treat all three as the same thing.

Recommended approach:

- Use `None` only for fields that are absent, not applicable, or not supplied.
- Use empty strings only when the source form explicitly has a blank value that
  was observed and preserved as blank.
- Add a small reusable structural wrapper or status enum only if it stays light
  and improves the distinction between blank, absent, and extraction failure.

Avoid overbuilding field-level provenance or confidence tracking in Phase 1.
Confidence remains exploratory and belongs to later evaluation/review work.

## Validation Boundary

Pydantic should enforce structural and type validation only.

Allowed Phase 1 validation examples:

- money fields parse to `Decimal`
- list fields are lists
- booleans are booleans
- required nested objects are present
- metadata identifies 2026 W-2 schema version

Do not encode IRS tax/business logic in the Pydantic model. Later validation
work must stay separate and grounded in authoritative IRS documentation.

Avoid automatic trust thresholds or confidence-based approval rules.

## Serialization Requirement

The canonical model must serialize to canonical JSON using Pydantic v2.

Tests should prove:

- a valid W-2 payload validates
- `Decimal` values serialize predictably for JSON
- repeated fields preserve list structure
- `W2Document.model_dump()` and `W2Document.model_dump_json()` work

## Test Requirements

Add focused pytest coverage for:

- a complete valid 2026 W-2 payload
- minimal optional/nullable valid payload behavior
- malformed money fields fail structural validation
- malformed repeated fields fail structural validation
- malformed boolean Box 13 fields fail structural validation
- unsupported metadata tax year or schema version fails, if the model constrains
  Phase 1 to 2026
- canonical JSON serialization

Tests must not use real taxpayer PII. Use clearly fake values such as:

- SSN: `000-00-0000`
- EIN: `00-0000000`
- fake names
- fake addresses

Do not add real W-2 fixtures.

## Documentation Requirements

Update:

- `README.md` with the Phase 1 contract location and package entrypoint.
- `docs/project-state.md` with Phase 1 completion status and next phase.
- `CHANGELOG.md` with the meaningful change.

Create a short schema contract document only if needed, for example:

```text
docs/contracts/canonical-w2-schema.md
```

Keep documentation focused. Do not duplicate the entire implementation brief.

## Verification

Run the relevant checks after implementation:

```text
pytest
```

If the project adds formatting, linting, or type-checking commands in
`pyproject.toml`, run those too.

Also verify:

- the official 2026 W-2 reference PDF remains under `docs/references/irs/`
- no evaluation dataset was added
- no real taxpayer data was added
- no extraction/OCR/vision/validation/export/frontend code was added
- changelog and project-state updates are present

## Definition Of Done

Phase 1 is complete when:

- the 2026 W-2 has a complete typed Pydantic representation
- every relevant 2026 form field is accounted for
- repeated fields are modeled correctly
- optional and nullable behavior is intentional
- monetary values use `Decimal`
- the model can serialize to canonical JSON
- tests prove valid payloads pass and malformed structural payloads fail
- the schema is version-aware without implementing historical years
- future extraction pipelines can target the model without knowing each other
- required documentation and changelog updates are complete
- no later-phase functionality has been implemented

## Expected Next Phase

After Phase 1, the expected next phase is likely:

```text
Phase 2 - Ingestion Boundary And Document Intake Contract
```

Do not begin Phase 2 during Phase 1.
