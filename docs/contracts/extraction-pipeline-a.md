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

Phase 4 selects Tesseract as the initial OCR baseline. The Python package
calls the local `tesseract` system binary and parses TSV output into
observations. Phase 4B sets full-page segmentation mode `--psm 3` as the
default and uses a supplemental `--psm 6` pass only to retain recognized
SSN-like text in the top identifier region. Phase 4D keeps PSM 3 as the
incumbent default while allowing controlled full-page PSM 11 and PSM 12
experiments through configuration.

If Tesseract is unavailable, Pipeline A raises `MissingOcrDependencyError` with
an actionable installation message. Unit tests do not require the system OCR
binary.

### OCR Backend Boundary

Pipeline A's observation acquisition layer (`ObservationAcquirer`) depends on
a structural `OcrAdapter` contract (`src/w2_pipeline/extraction/ocr_backend.py`)
rather than on Tesseract directly:

```python
class OcrAdapter(Protocol):
    def extract_image(self, image_path, *, page_number: int = 1) -> list[TextObservation]: ...
    def extract_pdf_pages(self, pdf_path, *, page_numbers=None) -> list[TextObservation]: ...
```

Any backend implementing this contract is interchangeable behind
`ObservationAcquirer` without the deterministic parser knowing which engine
produced an observation. Both OCR backends share PDF-page-to-image rendering
through `src/w2_pipeline/extraction/pdf_rendering.py` rather than duplicating
PyMuPDF rendering logic.

Phase 4 through Phase 4D used Tesseract exclusively. Phase 4E adds PaddleOCR
as a second backend behind the same contract, selectable with
`--ocr-backend {tesseract, paddleocr}` on the benchmark CLI. Tesseract remains
the default; adding PaddleOCR support does not change the incumbent.

### PaddleOCR Backend (Phase 4E)

`PaddleOcrAdapter` (`src/w2_pipeline/extraction/ocr_paddle.py`) calls the
`paddleocr` Python package's `PaddleOCR(...).predict(image_path)` pipeline and
converts each result's `res.json["res"]` payload into `TextObservation`
values: `rec_texts` becomes observation text, `rec_boxes` (already
`[x_min, y_min, x_max, y_max]` per detection) becomes the bounding box
directly, and `rec_scores` is not currently used for filtering. Unlike
Tesseract's word-level TSV output, PaddleOCR returns already-reconstructed
text lines, so the parser receives line-level observations similar in shape
to native PDF text extraction rather than requiring OCR word-row
reconstruction.

`PaddleOcrConfig` defaults:

```text
lang: "en"
device: "cpu"
use_doc_orientation_classify: False
use_doc_unwarping: False
use_textline_orientation: False
enable_mkldnn: False
```

`enable_mkldnn` defaults to `False` because PaddlePaddle's oneDNN CPU
execution path raised a PIR attribute-conversion error
(`ConvertPirAttribute2RuntimeAttribute not support
[pir::ArrayAttribute<pir::DoubleAttribute>]`) for the default PP-OCRv6 models
on the reference development machine; plain CPU inference without MKL-DNN is
stable. This is an environment-specific correctness fix, not a tuning choice.

If the `paddleocr` package is not installed, Pipeline A raises the same
`MissingOcrDependencyError` used by the Tesseract backend, pointing at the
`paddle` optional dependency group. Install it with:

```bash
pip install '.[paddle]'
```

Unit tests do not require PaddleOCR or its models installed; they override
the adapter's raw-prediction seam with canned payloads, mirroring the
existing Tesseract test pattern.

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

External Symage clean-render PaddleOCR smoke benchmark:

```bash
python -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl --variant-id external_clean_render --ocr-backend paddleocr --limit 5
```

The `--tesseract-psm` option selects only the main full-page Tesseract page
segmentation mode for Pipeline A. Supported experiment values are `3`, `11`,
and `12`. The targeted supplemental PSM 6 SSN recovery pass remains enabled so
PSM 11 and PSM 12 experiments isolate the main segmentation mode.
`--tesseract-psm` is ignored when `--ocr-backend paddleocr` is selected.

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

## Phase 4E PaddleOCR Backend Smoke Result

Phase 4E's implementation was validated with a 5-document PaddleOCR smoke
benchmark against the same external Symage clean-render set used by the
Tesseract baselines, before any full-scale PaddleOCR benchmark was run:

```text
documents: 5
field_accuracy: 0.9826086956521739
failed_documents: 0
correct_fields: 113
total_fields: 115
average_duration_seconds: 74.29913957080062
artifact: data/evaluation/results/phase4e_paddleocr_smoke_5.json
```

The only incorrect field across the 5 documents was `box_13.retirement_plan`
(3/5 correct), already a known weak field under the Tesseract incumbent.
Employee identity fields (first/last name, SSN), employer EIN, and all
federal money boxes were exact on this small sample.

This smoke result is directional evidence that the implementation is
functionally correct, not a statistically meaningful comparison against the
150-document Tesseract baseline. The dominant finding from the smoke run is
throughput, not accuracy: PaddleOCR averaged approximately 74.3
seconds/document versus Tesseract's approximately 2.05-2.22
seconds/document, roughly a 35-37x slowdown, driven by deep-learning model
inference versus Tesseract's classical OCR pipeline. A full 150-document
PaddleOCR benchmark would take on the order of 3 hours of wall-clock time at
this rate (longer for the 600-document robustness set), versus roughly 5
minutes for the equivalent Tesseract run. The full 150-document PaddleOCR
comparison has not been run as part of Phase 4E's implementation task and
remains the next step before PaddleOCR could be considered as an incumbent
replacement.
