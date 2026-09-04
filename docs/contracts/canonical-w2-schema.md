# Canonical W-2 Schema Contract

This document summarizes the Phase 1 canonical W-2 Pydantic contract. The
implementation lives in:

```text
src/w2_pipeline/contracts/w2.py
```

Import the top-level model with:

```python
from w2_pipeline.contracts.w2 import W2Document
```

## Source Of Truth

The initial schema is derived from the official 2026 Form W-2 reference:

```text
docs/references/irs/2026_W2.pdf
```

The initial supported metadata values are:

```text
document_type: W-2
tax_year: 2026
schema_version: 2026
```

The schema is version-aware but does not implement historical years.

## Model Shape

The canonical model is:

```text
W2Document
-> metadata
-> employee
-> employer
-> federal_wages_and_taxes
-> box_12_entries[]
-> box_13
-> box_14_entries[]
-> tipped_occupation_codes[]
-> state_local_entries[]
-> field_observations[]
```

The supporting models are:

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
- `FieldObservation`

## Field Coverage

Employee fields cover SSN, first name, middle initial, last name, suffix, and
address. On the official 2026 Form W-2, Box e presents the employee name as
three visual subfields:

```text
Employee's first name and initial | Last name | Suff.
```

The canonical `Employee` model keeps those semantics as four fields:

- `first_name` stores only the first-name portion of the first visual subfield.
- `middle_initial` stores the single-letter initial from that same visual
  subfield when present.
- `last_name` stores the separate Box e last-name subfield.
- `suffix` stores the separate Box e suffix subfield.

This is a semantic mapping clarification, not a schema-version change; the
`middle_initial` and `suffix` fields already existed in schema version `2026`.

Employer fields cover EIN, name, address, and control number.

Federal fields cover Boxes 1 through 11. Monetary boxes use `Decimal`; Box 9 is
modeled as a string verification code rather than a money value.

Box 12 is modeled as repeated `Box12Entry` records with `code` and `amount`.

Box 13 is modeled as three strict booleans: statutory employee, retirement
plan, and third-party sick pay.

Box 14a is modeled as repeated flexible `Box14Entry` records with a label and
either an amount or text value. Box 14b is modeled separately as repeated
`TippedOccupationCode` records for Treasury tipped occupation code(s).

State/local Boxes 15 through 20 are modeled as repeated `StateLocalEntry`
records so multiple state/local lines can be represented.

## Nullability And Extraction State

The contract uses `None` for fields that are absent, not applicable, or not
supplied. Empty strings may be used when a valid blank field was observed and
preserved.

When a value alone is not enough to distinguish the reason for null or blank
state, `field_observations` records lightweight field-level status:

- `observed_blank`
- `not_applicable`
- `extraction_failed`

This preserves the Phase 1 distinction without adding confidence tracking,
provenance, or validation workflow behavior.

## Validation Boundary

Pydantic enforces structural and type validation only. It does not encode IRS
tax rules, business-rule validation, extraction confidence thresholds, review
routing, CSV export, persistence, API routes, frontend behavior, or RAG.
