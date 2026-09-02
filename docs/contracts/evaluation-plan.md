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
