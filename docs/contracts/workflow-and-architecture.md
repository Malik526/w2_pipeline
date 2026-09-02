# Workflow And Architecture Contract

This document is the authoritative Phase 0 lifecycle, terminology, and
architecture contract.

## Core Workflow

The long-term workflow is:

```text
ingestion
-> extraction
-> canonicalization
-> validation
-> review
-> downstream output
```

Phase 0 documents these concepts only. Later phases may implement them.

## Core Terminology

Ingestion means receiving a document and preparing or routing it for processing.
Later responsibilities may include upload handling, document IDs, file-type
detection, original-file storage, PDF inspection, embedded-text detection, page
rendering, and image preprocessing. Ingestion does not determine what individual
W-2 fields mean.

Extraction means identifying W-2 values from a document, such as SSN, EIN,
employee name, employer name, Box 1, Box 2, Box 12 entries, Box 13 checkboxes,
and state or local fields. Extraction answers: what does this document appear
to contain?

Canonicalization means mapping extracted information into the application's
standardized W-2 representation. All extraction strategies must ultimately
converge on the same canonical model.

Validation means determining whether extracted structured data can be trusted
and used. Future validation categories may include schema validation, format
validation, deterministic domain validation, consistency checks, and
extraction-quality checks. Tax-domain validation must be grounded in
authoritative documentation. Do not invent tax rules.

Human review means routing cases that cannot safely pass automated validation
for manual review. Conceptual outcomes are `validated`, `needs_review`, and
`failed`. Phase 0 does not implement a review UI.

Downstream output means the structured result passed to the next system or
process. Initial planned output forms are canonical JSON and CSV. The canonical
model should remain independent from any downstream vendor.

## Document Lifecycle

Initial lifecycle/status terminology:

```text
uploaded
-> processing
-> extracted
-> validating
-> validated
```

Possible branch or terminal states:

```text
needs_review
failed
```

These terms are shared language for future backend, persistence, frontend, and
evaluation work. Phase 0 does not implement a workflow engine.

## Conceptual Architecture

The target architecture is:

```text
Next.js / React UI
-> FastAPI
-> Ingestion
-> Tax-year detection/configuration
-> Replaceable extraction pipeline
-> Canonical W-2
-> Tax-year-aware validation
-> validated / needs_review / failed
-> JSON / CSV
```

## Year-Specific Adapter Principle

Prefer this conceptual flow:

```text
Raw W-2
-> identify tax year
-> select appropriate year-specific form definition/extraction configuration
-> extract
-> map to canonical W-2 representation
-> apply validation appropriate to that tax year
```

Examples:

```text
2024 W-2 -> 2024 adapter/config -> canonical W-2
2025 W-2 -> 2025 adapter/config -> canonical W-2
2026 W-2 -> 2026 adapter/config -> canonical W-2
```

Do not implement historical adapters in Phase 0.

## Tax-Year Form Definition Vs Canonical Model

A tax-year form definition represents how a specific year's W-2 expresses
information, including layout, available boxes, Box 12 codes, and fields that
may be specific to that tax year.

The canonical W-2 model represents the application's standardized internal
representation of W-2 information.

The desired flow is:

```text
year-specific W-2
-> year-specific interpretation
-> canonical internal W-2
```

Phase 1 will define the first canonical model using the official 2026 Form W-2.

## Replaceable Extraction Pipeline Contract

Later phases will compare competing extraction implementations. The
architecture should support replaceable extraction pipelines:

```text
                         -> Pipeline A -
Normalized document ----|              |-> Canonical W-2 -> Validation
                         -> Pipeline B -
```

Pipeline A is the future deterministic baseline:

```text
native PDF extraction where available
OR
OCR where required
-> text + spatial/layout data
-> regex / labels / deterministic rules
-> canonical W-2
```

Pipeline B is the future model-based challenger:

```text
normalized document/image
-> document-understanding or vision model
-> schema-constrained structured extraction
-> canonical W-2
```

Both pipelines must converge on the same canonical representation and must be
evaluated against the same ground truth.

## Implemented Ingestion Boundary

Phase 2 implements the document intake layer before extraction:

```text
raw file
-> validate intake
-> inspect document
-> classify routing characteristics
-> IngestedDocument
-> ready for future extraction
```

The ingestion service accepts local PDF, JPEG, and PNG files, validates
extension and detectable content type, records source filename, MIME type, file
size, generated or caller-provided document ID, and SHA-256 fingerprint.

For PDFs, PyMuPDF records page count and classifies embedded-text routing as
`embedded_text`, `image_only`, `mixed`, or `unknown` using the documented
heuristic in `docs/contracts/ingestion-contract.md`.

For JPEG/PNG files, Pillow verifies readability and records dimensions.

This boundary is reusable by future deterministic and model-based extraction
pipelines. It does not implement OCR, W-2 field extraction, W-2 classification,
tax-year inference, validation engines, persistence, or export.

## RAG Boundary

This is primarily a document-processing and structured-extraction system, not a
Retrieval-Augmented Generation system.

The core problem is:

```text
known W-2
-> extract known fields
```

not:

```text
question
-> retrieve relevant knowledge
-> augment LLM context
-> generate answer
```

RAG may later support validation explanations, IRS instruction retrieval, firm
SOP retrieval, or tax-rule assistance. Do not add embeddings, vector databases,
document chunking, or RAG frameworks during Phase 0.

## Initial Technical Direction

Do not install dependencies unnecessarily in Phase 0.

Planned future stack:

- Python as the primary processing language.
- FastAPI for the API layer.
- Pydantic for canonical W-2 representation, data typing, and structural
  validation.
- PyMuPDF for PDF inspection, text extraction, coordinates, rendering, and
  digital/scanned PDF handling.
- pandas for offline evaluation analysis.
- Local filesystem storage for prototype source/test documents.
- SQLite for lightweight local metadata or state if needed.
- Next.js, React, and TypeScript for a future frontend.

The prototype should avoid premature production infrastructure. A future
migration path may be filesystem to object storage and SQLite to PostgreSQL.
