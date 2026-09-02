# System Contract

This document is the authoritative Phase 0 product and boundary contract for
W-2 Pipeline.

## Problem Statement

The long-term platform objective is:

```text
W-2 ingestion
-> extraction
-> canonicalization
-> validation
-> human review when required
-> downstream output
```

The project should convert received W-2 documents into validated canonical W-2
data that can be consumed by downstream tax-preparation workflows.

## Working User Assumption

The primary assumed user is an accounting or tax-preparation firm processing
W-2 documents supplied by individual tax clients for preparation of individual
tax returns.

Representative workflow:

```text
Individual taxpayer
-> provides one or more W-2s
-> accounting firm receives them
-> system ingests each W-2
-> fields are extracted
-> data is normalized
-> extracted data is validated
-> uncertain or problematic cases are reviewed
-> validated W-2 data becomes available
-> downstream tax-preparation workflow consumes the result
```

This is a working product assumption, not a claim about Rational's internal
architecture. Future product clarification may revise the user or workflow.

## Initial Production Target

The initial supported form version is:

```text
Form W-2
Tax Year: 2026
```

Conceptually, documents should be able to carry metadata such as:

```text
document_type: W-2
tax_year: 2026
schema_version: 2026
```

Phase 0 does not define the code representation for this metadata.

## Authoritative Reference

The official IRS 2026 Form W-2 PDF is the authoritative form-format reference
for the initial implementation. It is stored at:

```text
docs/references/irs/2026_W2.pdf
```

Phase 1 must derive the canonical W-2 schema field inventory from this PDF, not
from older generic W-2 examples.

## Tax-Year Awareness

The architecture must be tax-year aware from the beginning, while avoiding a
generalized multi-year tax platform in Phase 0.

The only required initial production schema is 2026. Historical forms such as
2025, 2024, and 2023 W-2s may later be used for robustness or compatibility
evaluation if legitimate blank/reference forms and safe synthetic test
documents are obtained or generated.

Do not force all years into one hard-coded form definition. Do not implement a
multi-year rules engine in Phase 0.

## System Begins

The system begins when a W-2 document enters the application.

Initial intended input types:

- PDF
- JPEG
- PNG

Document forms to recognize later:

- Digital PDF with embedded machine-readable text.
- Scanned PDF with one or more page images requiring OCR or document vision.
- Image or phone photo that may include rotation, blur, compression,
  perspective distortion, cropping, shadows, or inconsistent lighting.

Preprocessing, OCR, document vision, and file inspection are later-phase work.

## System Ends

The system ends when it has produced a validated canonical W-2 representation
suitable for downstream use.

Initial planned downstream forms:

- canonical JSON
- CSV

Future downstream integrations may include tax-preparation software, internal
Rational APIs, databases, or accounting systems. Those integrations are not
part of Phase 0.

## Explicit Non-Goals

The following are outside the MVP unless a later brief explicitly adds them:

- full Form 1040 preparation
- complete tax-return generation
- tax liability calculation
- IRS return filing
- SSA employer W-2 filing
- payroll processing
- W-2 generation for employers
- production tax-software integrations
- payment processing
- full client portal
- accounting CRM
- production authentication
- multi-tenant firm management
- production cloud architecture
- generalized multi-year tax-form platform
- comprehensive regulatory or compliance framework

## Phase 0 Non-Implementation Boundary

Phase 0 must not implement:

- canonical Pydantic W-2 schema
- year-specific schema adapters
- OCR
- PyMuPDF pipeline
- regex extraction
- model extraction
- Hugging Face inference
- tax-year detection
- synthetic W-2 generator
- benchmark datasets
- evaluator
- validation engine
- confidence thresholds
- review UI
- CSV exporter
- tax-software adapter
- PostgreSQL
- cloud object storage
- RAG or vector database
