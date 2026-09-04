# Phase 4B Pipeline A Benchmark Results

Phase 4B reconciles Pipeline A as a measured deterministic baseline against the
external Symage synthetic 2026 W-2 benchmark. The JSON files under
`data/evaluation/results/` remain the canonical machine-readable result
artifacts; this report is the concise human-readable summary.

## Benchmark Categories

| Category | Purpose | Documents | Route | Field Accuracy | Failure Rate |
| --- | --- | ---: | --- | ---: | ---: |
| Internal generated clean PDFs | Controlled integration smoke check | 5 | native_pdf | 100.00% | 0.00% |
| External Symage clean renders | Primary independent realism benchmark | 150 | ocr | 98.88% | 0.00% |
| External Symage degraded variants | Robustness benchmark | 600 | ocr | 89.27% | 0.00% |

The internal generated clean PDF run is a sanity check only. It should not be
combined with the external Symage image results as a single headline metric.

## Pipeline A External Benchmark

### Clean Benchmark

Result artifact:

```text
data/evaluation/results/phase4b_external_clean_150.json
```

| Metric | Value |
| --- | ---: |
| Documents | 150 |
| Correct fields | 3,263 |
| Total fields | 3,300 |
| Field accuracy | 98.8788% |
| Failed documents | 0 |
| Failure rate | 0.00% |
| Average duration | 2.143 seconds/document |
| Route | ocr |

### Robustness By Variant

Result artifact:

```text
data/evaluation/results/phase4b_external_all_variants_600.json
```

| Variant | Documents | Correct Fields | Total Fields | Field Accuracy |
| --- | ---: | ---: | ---: | ---: |
| external_clean_render | 150 | 3,263 | 3,300 | 98.8788% |
| compressed_jpeg | 150 | 3,233 | 3,300 | 97.9697% |
| rotated_png | 150 | 3,051 | 3,300 | 92.4545% |
| blurred_png | 150 | 2,236 | 3,300 | 67.7576% |
| all variants | 600 | 11,783 | 13,200 | 89.2652% |

The 600-document run had `failed_documents = 0`, `failure_rate = 0.0`, and
`average_duration_seconds = 2.1310415448267`.

## Primary Failure Modes

Clean external OCR remains strong overall. The weakest clean fields were:

| Field | Accuracy |
| --- | ---: |
| employee.first_name | 84.00% |
| box_13.retirement_plan | 96.67% |
| employee.last_name | 98.67% |
| employer.ein | 98.67% |
| federal_wages_and_taxes.box_6_medicare_tax_withheld | 98.67% |

Most major federal money boxes were at or near 100% on clean external renders.

Across all 600 variants, the weakest fields were:

| Field | Accuracy |
| --- | ---: |
| employee.first_name | 48.17% |
| box_13.retirement_plan | 66.83% |
| employee.last_name | 80.83% |
| employee.ssn | 83.00% |
| employer.ein | 83.00% |
| federal Boxes 1-6 | roughly 82.50%-84.17% |

## Interpretation

Pipeline A performs very strongly on clean and compressed external W-2 images,
degrades moderately under rotation, and degrades substantially under blur.

These results make Pipeline A a measured deterministic baseline. They do not
establish a final extraction architecture or production-readiness threshold.

## Runtime

The external clean run averaged approximately 2.14 seconds/document. The full
600-variant robustness run averaged approximately 2.13 seconds/document.

## Benchmark Integrity

The external benchmark uses the independent
`Symage/synthetic-us-forms-preview` dataset filtered to
`irs_w2_single_page_2026`.

Pipeline A received only the document path, document ID, optional tax-year hint,
and non-answer source metadata through `ExtractionInput`. Dataset annotations,
including `tokens`, `bboxes`, `ner_tags`, `funsd_json`, `coco_json`,
`yolo_txt`, and evaluator canonical ground truth, stayed evaluator-side.

## Reproduction

Prepare the external dataset locally:

```bash
python3 -m pip install '.[external]'
python -m w2_pipeline.evaluation.prepare_external_dataset
```

Run the clean external benchmark:

```bash
python -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl --variant-id external_clean_render --output-json data/evaluation/results/phase4b_external_clean_150.json
```

Run the full external robustness benchmark:

```bash
python -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl --output-json data/evaluation/results/phase4b_external_all_variants_600.json
```
