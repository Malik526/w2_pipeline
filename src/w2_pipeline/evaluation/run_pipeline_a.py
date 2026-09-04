"""Run Pipeline A against a Phase 3 evaluation manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from w2_pipeline.evaluation.manifest import DatasetManifestEntry, load_manifest_jsonl
from w2_pipeline.evaluation.reporting import (
    summarize_document_evaluations,
    write_markdown_report_for_json,
)
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
    parser.add_argument(
        "--no-markdown-report",
        action="store_true",
        help="Do not write the matching .md report when --output-json is used.",
    )
    args = parser.parse_args()

    manifest = load_manifest_jsonl(args.manifest)
    entries = _filter_entries(manifest.entries, variant_id=args.variant_id, limit=args.limit)
    result = evaluate_manifest(
        entries=entries,
        manifest_base_dir=args.manifest.parent,
        extractor=PipelineAExtractor(),
        pipeline_id="pipeline_a",
    )
    summary = summarize_document_evaluations(
        result.document_evaluations,
        pipeline_id="pipeline_a",
        entries=entries,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        if not args.no_markdown_report:
            write_markdown_report_for_json(args.output_json)


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


if __name__ == "__main__":
    main()
