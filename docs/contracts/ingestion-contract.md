# Ingestion Contract

This document summarizes the Phase 2 document intake boundary. The
implementation lives in:

```text
src/w2_pipeline/ingestion/
```

Use the service with:

```python
from w2_pipeline.ingestion import ingest_document
```

## Scope

Phase 2 accepts local PDF, JPEG, and PNG source files and returns a normalized
`IngestedDocument` result for future extraction pipelines.

Ingestion answers what was received and how later processing should treat it.
It does not answer which W-2 fields are present and does not populate
`W2Document`.

## Result Shape

`IngestedDocument` records:

- generated or caller-provided document ID
- source path and filename
- source document type
- MIME type
- file size
- SHA-256 content fingerprint
- PDF page count and text routing metadata, when applicable
- image dimensions, when applicable
- ingestion status

The document ID is application identity. The SHA-256 hash is a deterministic
content fingerprint and is not used as the document ID or as an authentication
mechanism.

## Type Detection

The ingestion service reconciles supported file extensions with detectable file
signatures. It accepts:

- `application/pdf`
- `image/jpeg`
- `image/png`

Clearly unsupported extensions, corrupt content, or extension/content
mismatches fail with explicit ingestion errors.

## PDF Inspection Heuristic

PyMuPDF is used only for lightweight PDF inspection and routing metadata.

A PDF page is considered to have usable embedded text when PyMuPDF extracts at
least 40 alphanumeric characters from that page. Aggregate classification is:

- `embedded_text` when every page has usable embedded text
- `image_only` when no page has usable embedded text
- `mixed` when some pages have usable embedded text and others do not
- `unknown` when no page-level signal exists

This heuristic is deterministic and intentionally limited. It is not OCR, W-2
classification, tax-year detection, field extraction, or a guarantee that text
is semantically useful.

## Image Inspection

Pillow is used for lightweight JPEG/PNG readability checks and dimensions.
Phase 2 does not deskew, enhance, denoise, crop, normalize, or OCR images.

## Error Boundary

Ingestion failures raise explicit exceptions from
`w2_pipeline.ingestion.errors`, including:

- `DocumentNotFoundError`
- `UnreadableDocumentError`
- `UnsupportedDocumentTypeError`
- `DocumentTypeMismatchError`
- `CorruptPdfError`
- `CorruptImageError`

Error messages identify the failing file name, but do not expose source
contents.

## Non-Goals

Phase 2 does not implement OCR, W-2 field parsing, regex extraction, model or
vision inference, tax-year inference, validation engines, confidence scoring,
human review, FastAPI upload routes, persistence, CSV export, frontend work, or
RAG.
