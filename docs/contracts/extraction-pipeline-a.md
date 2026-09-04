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
Phase 4B sets full-page segmentation mode `--psm 3` as the default and uses a
supplemental `--psm 6` pass only to retain recognized SSN-like text in the top
identifier region. Phase 4D keeps PSM 3 as the incumbent default while allowing
controlled full-page PSM 11 and PSM 12 experiments through configuration.

If Tesseract is unavailable, Pipeline A raises `MissingOcrDependencyError` with
an actionable installation message. Unit tests do not require the system OCR
binary.

## Parser Strategy

The initial 2026 W-2 parser uses explicit deterministic rules:

- layout-aware employee and employer identity regions
- label/value parsing for federal Boxes 1-8, 10, and 11
- exact `Decimal` money parsing without float conversion
- OCR word-row reconstruction for Tesseract word observations
- OCR full-page geometry/zone fallbacks for employee name/SSN, employer EIN,
  federal money boxes, and Box 13 checkbox markers
- Box e employee-name parsing that reads the first-name-and-initial region
  left-to-right, splits a trailing uppercase single-letter token into
  `employee.middle_initial`, and keeps `employee.last_name` and
  `employee.suffix` as independent visual subfields
- conservative tiny OCR artifact filtering in the Box e name zones when a
  much smaller one- to three-character fragment appears alongside normal-size
  name text
- repeated Box 12 code/value rows
- Box 13 checkbox text markers
- Box 14a amount or text values
- Box 14b tipped occupation codes
- repeated state/local rows for Boxes 15-20

Box 9 is not populated by the internal 2026 fixture generator. The canonical
schema still contains the Phase 1 field, but the Phase 4 fixture correction
prevents the renderer from inventing unsupported Box 9 content.

Pipeline A does not transliterate or normalize employee-name accents. Strings
are preserved as recognized and compared exactly by the evaluator; for
example, `Jesús` and `Jesus` remain different semantic values.

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

External Symage clean-render PSM experiment smoke benchmark:

```bash
python -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl --variant-id external_clean_render --tesseract-psm 11 --limit 5
```

Full external prepared benchmark:

```bash
python -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl
```

The `--tesseract-psm` option selects only the main full-page Tesseract page
segmentation mode for Pipeline A. Supported experiment values are `3`, `11`,
and `12`. The targeted supplemental PSM 6 SSN recovery pass remains enabled so
PSM 11 and PSM 12 experiments isolate the main segmentation mode.

## Baseline Results

The initial Phase 4 native-PDF smoke check used internal generated clean PDFs:

```text
documents: 5
field_accuracy: 1.0
failure_rate: 0.0
route: native_pdf
```

Phase 4B installed and exercised Tesseract end to end for external Symage image
benchmarks. The external clean-render benchmark result is:

```text
documents: 150
field_accuracy: 0.9887878787878788
failure_rate: 0.0
average_duration_seconds: 2.2230018675666874
route: ocr
```

The full prepared external-variant benchmark result is:

```text
documents: 600
field_accuracy: 0.8926515151515152
failure_rate: 0.0
average_duration_seconds: 2.1310415448267
route: ocr
```

Variant accuracy:

```text
external_clean_render: 0.9887878787878788
compressed_jpeg: 0.9796969696969697
rotated_png: 0.9245454545454546
blurred_png: 0.6775757575757576
```

Pipeline A performs strongly on clean and compressed external W-2 images,
degrades moderately under rotation, and degrades substantially under blur.
Known weaknesses include employee first-name extraction, Box 13 retirement-plan
checkbox detection, employee SSN/employer EIN under degraded variants, and
blurred federal Boxes 1-6. These results establish a deterministic measured
baseline, not a final production extraction architecture.

After Phase 4B, Box e employee-name semantics were corrected so
`employee.first_name` no longer absorbs the middle initial. Historical Phase
4B results remain useful as OCR baselines, but any benchmark intended to
evaluate employee-name field accuracy must be rerun against regenerated
external ground truth with `employee.middle_initial` included in
`evaluated_field_paths`.
