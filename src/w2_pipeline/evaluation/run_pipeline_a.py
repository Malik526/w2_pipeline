"""Run Pipeline A against a Phase 3 evaluation manifest."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path

from w2_pipeline.evaluation.manifest import DatasetManifestEntry, load_manifest_jsonl
from w2_pipeline.evaluation.models import DocumentEvaluationStatus
from w2_pipeline.evaluation.runner import evaluate_manifest
from w2_pipeline.extraction.pipeline_a import PipelineAExtractor


def main() -> None:
    """Evaluate Pipeline A against a manifest and print aggregate metrics."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Path to manifest.jsonl.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum entries to evaluate.")
    parser.add_argument(
        "--variant-id",
        default=None,
        help="Optional variant ID filter, such as external_clean_render or clean_pdf.",
    )
    parser.add_argument("--output-json", type=Path, default=None, help="Optional summary JSON path.")
    args = parser.parse_args()

    manifest = load_manifest_jsonl(args.manifest)
    entries = _filter_entries(manifest.entries, variant_id=args.variant_id, limit=args.limit)
    result = evaluate_manifest(
        entries=entries,
        manifest_base_dir=args.manifest.parent,
        extractor=PipelineAExtractor(),
        pipeline_id="pipeline_a",
    )
    summary = _summarize(result.document_evaluations)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def _filter_entries(
    entries: list[DatasetManifestEntry],
    *,
    variant_id: str | None,
    limit: int | None,
) -> list[DatasetManifestEntry]:
    filtered = [entry for entry in entries if variant_id is None or entry.variant_id == variant_id]
    if limit is not None:
        return filtered[:limit]
    return filtered


def _summarize(evaluations):
    total = len(evaluations)
    failed = sum(evaluation.status != DocumentEvaluationStatus.SUCCESS for evaluation in evaluations)
    total_fields = sum(evaluation.total_fields for evaluation in evaluations)
    correct_fields = sum(evaluation.correct_fields for evaluation in evaluations)
    durations = [
        evaluation.duration_seconds
        for evaluation in evaluations
        if evaluation.duration_seconds is not None
    ]
    by_variant = defaultdict(lambda: {"documents": 0, "correct_fields": 0, "total_fields": 0})
    by_route = defaultdict(lambda: {"documents": 0, "correct_fields": 0, "total_fields": 0})
    by_field = defaultdict(lambda: {"correct": 0, "total": 0})

    for evaluation in evaluations:
        variant_bucket = by_variant[evaluation.variant_id]
        variant_bucket["documents"] += 1
        variant_bucket["correct_fields"] += evaluation.correct_fields
        variant_bucket["total_fields"] += evaluation.total_fields
        route_bucket = by_route[evaluation.extraction_route or "failed_or_unknown"]
        route_bucket["documents"] += 1
        route_bucket["correct_fields"] += evaluation.correct_fields
        route_bucket["total_fields"] += evaluation.total_fields
        for field_evaluation in evaluation.field_evaluations:
            field_bucket = by_field[field_evaluation.field_path]
            field_bucket["total"] += 1
            if field_evaluation.correct:
                field_bucket["correct"] += 1

    return {
        "pipeline_id": "pipeline_a",
        "documents": total,
        "failed_documents": failed,
        "failure_rate": failed / total if total else 0.0,
        "field_accuracy": correct_fields / total_fields if total_fields else 0.0,
        "correct_fields": correct_fields,
        "total_fields": total_fields,
        "average_duration_seconds": sum(durations) / len(durations) if durations else 0.0,
        "accuracy_by_variant": _accuracy_buckets(by_variant),
        "accuracy_by_route": _accuracy_buckets(by_route),
        "per_field_accuracy": _field_accuracy_buckets(by_field),
    }


def _accuracy_buckets(buckets):
    return {
        key: {
            **value,
            "field_accuracy": (
                value["correct_fields"] / value["total_fields"]
                if value["total_fields"]
                else 0.0
            ),
        }
        for key, value in sorted(buckets.items())
    }


def _field_accuracy_buckets(buckets):
    return {
        key: {
            **value,
            "incorrect": value["total"] - value["correct"],
            "field_accuracy": value["correct"] / value["total"] if value["total"] else 0.0,
        }
        for key, value in sorted(
            buckets.items(),
            key=lambda item: (item[1]["correct"] / item[1]["total"] if item[1]["total"] else 0.0, item[0]),
        )
    }


if __name__ == "__main__":
    main()
