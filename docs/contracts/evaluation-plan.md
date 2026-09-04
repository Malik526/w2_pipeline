# Evaluation Plan

This document is the authoritative Phase 0 evaluation contract.

## Evaluation Purpose

Future evaluation is offline technical benchmarking of competing
document-processing pipelines, not user-facing experimentation.

Experiments must hold constant:

- source dataset
- expected ground truth
- canonical schema
- evaluator

Only the extraction approach should change during the primary A/B comparison.

## Benchmarks

The primary benchmark is:

```text
2026-style W-2 documents
```

This benchmark answers how well the system performs against the current target
schema.

An optional secondary compatibility benchmark may later use historical forms,
such as 2025, 2024, or 2023 W-2s, if legitimate blank/reference forms and safe
synthetic test documents are obtained or generated.

Do not mix all years into one undifferentiated accuracy number. Future results
should remain segmentable by tax year:

```text
2026 field accuracy
2025 field accuracy
2024 field accuracy
2023 field accuracy
```

A combined aggregate may also be reported, but year-specific performance should
remain visible.

## Ground Truth

All pipelines must be evaluated against the same ground truth. Ground truth
should be expressed in the canonical W-2 representation once that representation
exists.

The official blank 2026 W-2 form is a reference artifact. It is not a completed
taxpayer fixture, benchmark data, model training data, or ground truth.

## Candidate Pipelines

Pipeline A is a deterministic baseline. It may later combine native PDF text
extraction, OCR where required, spatial/layout data, labels, regex, and
deterministic rules.

Pipeline B is a model-based challenger. It may later use a
document-understanding or vision model with schema-constrained structured
extraction.

Both approaches must produce the same canonical W-2 representation before
validation and scoring.

## Metrics

Field accuracy is the percentage of expected normalized W-2 fields whose
extracted value exactly or appropriately matches ground truth. It should support
overall, per-field, per-document, and per-tax-year reporting.

Review rate is the percentage of processed documents that cannot safely proceed
automatically and require human review:

```text
documents requiring review / total documents processed
```

Lower review rate is preferable only if accuracy remains acceptable.

Processing latency is the time required for a pipeline to produce its
structured extraction result. Future reports may include median, average, and
p95 latency.

Failure rate is the percentage of documents where the pipeline fails to produce
a valid processable extraction. Examples include exceptions, unusable OCR,
malformed structured output, or failure to construct the canonical
representation.

Cost per document should be measured when paid APIs or models are introduced.
This may be near zero for local approaches.

## Confidence Scores

Confidence scores are experimental. Do not treat model or extractor confidence
as equivalent to correctness.

Do not define automatic trust thresholds such as `confidence > 95%` without
empirical evidence. Future evaluation may compare reported confidence against
actual correctness to determine whether confidence is calibrated enough to help
with review routing.

Validation must function without relying exclusively on model confidence.

## Safe Evaluation Data

Future evaluation data should use synthetic W-2s, fake names, fake SSNs, fake
EINs, fake addresses, public blank IRS forms, or appropriately licensed open
datasets without sensitive taxpayer information.

Real taxpayer W-2 data must not be committed to the repository or casually used
as development fixtures.

## Phase 3 Harness

Phase 3 implements the first pipeline-independent ground-truth harness in:

```text
src/w2_pipeline/evaluation/
```

The harness compares an extractor's predicted `W2Document` with the expected
canonical `W2Document`. It does not inspect OCR output, PDF text, vision-model
responses, regex matches, or any pipeline-specific intermediate state.

The primary metric is:

```text
field accuracy = correct evaluated fields / total evaluated fields
```

The comparison flattens nested canonical models into deterministic field paths,
including list indexes for repeated fields:

```text
employee.first_name
federal_wages_and_taxes.box_1_wages_tips_other_compensation
box_12_entries[0].code
state_local_entries[0].box_15_state
```

Repeated fields are compared by index in Phase 3. This matches the current
canonical contract's order-preserving list representation and keeps the initial
evaluator deterministic. A later extractor phase may add semantic matching if
real extraction evidence shows order is not reliable enough.

Operational metadata fields that are not semantic W-2 content are excluded from
field accuracy:

```text
metadata.document_id
metadata.source_filename
metadata.source_file_type
field_observations
```

`metadata.document_type`, `metadata.tax_year`, and `metadata.schema_version`
remain evaluated so results stay tax-year and schema aware.

Failures are classified explicitly:

- `missing` when an expected field path is absent or an expected value is
  predicted as `null`
- `mismatch` when expected and predicted semantic values differ
- `unexpected` when a prediction contains a field path absent from ground truth
- `extraction_failed` when a pipeline raises instead of returning a prediction
- `invalid_canonical_result` when a pipeline returns data that cannot validate
  as `W2Document`

Strings are normalized only by trimming surrounding whitespace. Decimal values
remain `Decimal` values and are compared without float conversion.

## Phase 3B External Synthetic Benchmark

Phase 3B extends the Phase 3 harness without replacing the internal synthetic
benchmark. The architecture now supports two separate synthetic sources:

- internal synthetic W-2s generated by this repository for deterministic
  coverage control
- external synthetic W-2s adapted from Hugging Face for independent benchmark
  coverage

The external adapter targets:

```text
dataset = Symage/synthetic-us-forms-preview
form_id = irs_w2_single_page_2026
```

Inspected dataset-card properties are:

- license: `cc-by-4.0`
- splits: `train` and `test`
- row counts: 420 train rows, 105 test rows, 525 total rows
- 2026 W-2 subset: 150 single-page documents
- images: clean typed 300-DPI PNG page renders
- annotations: `tokens`, `bboxes`, `ner_tags`, `funsd_json`, `coco_json`,
  `yolo_txt`

The primary end-to-end benchmark mode is:

```text
external image
-> extractor
-> predicted W2Document
-> existing evaluator
-> external-annotation-derived ground truth
```

Benchmark isolation / annotation leakage prevention is mandatory. Extractors
receive an `ExtractionInput` containing the document path, document ID,
optional tax-year hint, and source metadata. They do not receive answer-bearing
dataset annotations.

External annotations remain evaluator-side. They may be preserved for a future
component-isolation diagnostic such as:

```text
oracle_layout tokens + bboxes
-> deterministic parser
-> canonical W2Document
```

That diagnostic deliberately bypasses OCR and must not be mixed with primary
end-to-end field accuracy. Manifest entries carry a `benchmark_mode` label,
defaulting to `end_to_end`, so these categories remain separable in future
reports.

The external mapping produces canonical `W2Document` ground truth and records
`evaluated_field_paths`. When external annotations do not authoritatively map a
canonical field, that field is excluded from scoring for that external item
rather than being treated as an extraction failure.

## Phase 4 Pipeline A Benchmark Integration

Phase 4 adds Pipeline A as the first evaluated extractor. Pipeline A plugs into
the existing benchmark runner through the same annotation-free `ExtractionInput`
contract used by all future extractors.

The benchmark runner now records `extraction_route` when a pipeline returns a
typed extraction result. Pipeline A route values are:

- `native_pdf`
- `ocr`
- `mixed`

The developer benchmark command is:

```bash
python -m w2_pipeline.evaluation.run_pipeline_a <manifest.jsonl>
```

The command reports field accuracy, document failure count/rate, average
duration, accuracy by variant, accuracy by route, per-field accuracy, and
structured incorrect field results. When `--output-json` is supplied, the JSON
file remains canonical and the runner also writes a matching Markdown report
with the same base filename.

## Phase 4B External Pipeline A Results

Phase 4B adds per-field summary output and structured field-failure inspection
to Pipeline A benchmark results. Completed external OCR benchmark artifacts are
recorded under:

```text
data/evaluation/results/
```

Human-readable companion reports use the same base filename as their canonical
JSON artifact. For example:

```text
data/evaluation/results/phase4b_external_clean_150.json
data/evaluation/results/phase4b_external_clean_150.md
```

The benchmark categories are intentionally separate:

- internal generated clean PDF benchmark: controlled native-PDF integration
  check, 5 documents, 100% field accuracy, route `native_pdf`
- external Symage clean benchmark: primary independent end-to-end Pipeline A
  realism benchmark, 150 independently generated 2026-style W-2 images,
  98.88% field accuracy, 0 document failures, route `ocr`
- external degradation benchmark: 600 total OCR variants, aggregate 89.27%
  field accuracy, 0 document failures, with clean 98.88%, compressed JPEG
  97.97%, rotated PNG 92.45%, and blurred PNG 67.76%

Result JSON includes:

- `field_accuracy`
- `failed_documents`
- `failure_rate`
- `average_duration_seconds`
- `accuracy_by_variant`
- `accuracy_by_route`
- `per_field_accuracy`
- `field_failures`

`field_failures` records the document ID, variant ID, canonical field path,
expected value, predicted value, route, and failure kind for fields that the
existing evaluator marked incorrect. These values are intended for synthetic
evaluation reports; future real-data reporting should redact sensitive values.

Review rate and cost per document remain future metrics. They are not
implemented by the current local deterministic benchmark artifacts.

## Long-Running Evaluation Execution

Any deterministic evaluation, benchmark, OCR run, model comparison, build, or
similar command expected to take more than approximately 2 minutes must be
launched in the background or detached mode rather than kept open
interactively. The run must persist stdout/stderr to a log file, persist the
PID, and identify the intended result artifact path before the agent stops
active polling.

Use `data/evaluation/results/` for benchmark logs, PID files, and result
artifacts. JSON/Markdown results are intentional benchmark artifacts. `.log`
and `.pid` files are local run-control artifacts and should not be committed
unless a future brief explicitly asks for them.

The project-local command pattern is documented in:

```text
data/evaluation/README.md
```
