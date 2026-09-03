# Pipeline A Extraction Contract

Phase 4 implements Pipeline A, the deterministic native-text/OCR baseline.

## Scope

Pipeline A starts after Phase 2 ingestion:

```text
IngestedDocument / ExtractionInput
-> route document
-> acquire text + layout
-> parse deterministic W-2 fields
-> canonical W2Document
```

It does not implement Pipeline B, model inference, confidence thresholds,
validation, review routing, persistence, export, frontend work, or RAG.

## Observation Model

Native PDF extraction and OCR converge on:

```text
TextObservation
```

Each observation records:

- text
- 1-indexed page number
- top-left-origin bounding box using `x0`, `y0`, `x1`, `y1`
- source: `native_pdf` or `ocr`

The deterministic parser consumes this common representation rather than
PyMuPDF or Tesseract-specific objects.

## Routing

PDFs with usable embedded text use PyMuPDF native line extraction. Image files
and image-only PDFs use OCR. Mixed PDFs are processed page by page, combining
native observations for text pages and OCR observations for image-only pages.

## OCR Engine

Phase 4 selects Tesseract as the single OCR baseline. The Python package calls
the local `tesseract` system binary and parses TSV output into observations.

If Tesseract is unavailable, Pipeline A raises `MissingOcrDependencyError` with
an actionable installation message. Unit tests do not require the system OCR
binary.

## Parser Strategy

The initial 2026 W-2 parser uses explicit deterministic rules:

- layout-aware employee and employer identity regions
- label/value parsing for federal Boxes 1-8, 10, and 11
- exact `Decimal` money parsing without float conversion
- repeated Box 12 code/value rows
- Box 13 checkbox text markers
- Box 14a amount or text values
- Box 14b tipped occupation codes
- repeated state/local rows for Boxes 15-20

Box 9 is not populated by the internal 2026 fixture generator. The canonical
schema still contains the Phase 1 field, but the Phase 4 fixture correction
prevents the renderer from inventing unsupported Box 9 content.

## Benchmark Isolation

Pipeline A integrates with the Phase 3/3B evaluator through `ExtractionInput`.
For external Symage records, the extractor receives only document path, document
ID, source metadata, and optional tax-year hint. It never receives tokens,
bounding boxes, NER tags, FUNSD, COCO, YOLO, or canonical ground truth.

## Benchmark Commands

Internal clean PDF smoke benchmark:

```bash
python -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/generated/manifest.jsonl --variant-id clean_pdf --limit 5
```

External Symage clean-render smoke benchmark:

```bash
python -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl --variant-id external_clean_render --limit 5
```

Full external prepared benchmark:

```bash
python -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl
```

## Baseline Results On 2026-09-03

This environment does not have the `tesseract` system binary installed.

Internal generated clean PDFs use the native PDF route:

```text
documents: 5
field_accuracy: 1.0
failure_rate: 0.0
route: native_pdf
```

External Symage clean renders require OCR:

```text
documents: 150
field_accuracy: 0.0
failure_rate: 1.0
route: ocr
reason: missing Tesseract runtime
```

All prepared external variants:

```text
documents: 600
field_accuracy: 0.0
failure_rate: 1.0
route: ocr
reason: missing Tesseract runtime
```

These numbers confirm benchmark execution and failure isolation. They are not
evidence of OCR quality until Tesseract is installed and the OCR route can run.
