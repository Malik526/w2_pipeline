"""Run Pipeline B (Qwen3-VL) against a Phase 3 evaluation manifest.

Phase 5A feasibility spike: intended for small `--limit` smoke runs against
1-5 documents, not full-scale benchmarking. See
`docs/contracts/extraction-pipeline-b.md`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from w2_pipeline.evaluation.manifest import DatasetManifestEntry, load_manifest_jsonl
from w2_pipeline.evaluation.reporting import (
    summarize_document_evaluations,
    write_markdown_report_for_json,
)
from w2_pipeline.evaluation.runner import evaluate_manifest
from w2_pipeline.extraction.pipeline_b import PipelineBConfig, PipelineBExtractor


def main(argv: list[str] | None = None) -> None:
    """Evaluate Pipeline B against a manifest and print aggregate metrics."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    manifest = load_manifest_jsonl(args.manifest)
    entries = _filter_entries(manifest.entries, variant_id=args.variant_id, limit=args.limit)
    extractor = PipelineBExtractor(
        config=PipelineBConfig(model_id=args.model_id, device=args.device, dtype=args.dtype)
    )
    result = evaluate_manifest(
        entries=entries,
        manifest_base_dir=args.manifest.parent,
        extractor=extractor,
        pipeline_id="pipeline_b",
    )
    summary = summarize_document_evaluations(
        result.document_evaluations,
        pipeline_id="pipeline_b",
        entries=entries,
        benchmark_metadata=_pipeline_b_metadata(extractor, variant_id=args.variant_id),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        if not args.no_markdown_report:
            write_markdown_report_for_json(args.output_json)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Path to manifest.jsonl.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum entries to evaluate. Phase 5A is scoped to 1-5 documents.",
    )
    parser.add_argument(
        "--variant-id",
        default=None,
        help="Optional variant ID filter, such as external_clean_render or rotated_png.",
    )
    parser.add_argument(
        "--model-id",
        default="Qwen/Qwen3-VL-4B-Instruct",
        help="Hugging Face model ID for Pipeline B's vision-language model.",
    )
    parser.add_argument(
        "--device",
        default="auto",
        help="Transformers device_map value, e.g. auto, cuda, cpu. Default auto.",
    )
    parser.add_argument(
        "--dtype",
        default="auto",
        help="Transformers dtype value, e.g. auto, bfloat16, float32. Default auto.",
    )
    parser.add_argument("--output-json", type=Path, default=None, help="Optional summary JSON path.")
    parser.add_argument(
        "--no-markdown-report",
        action="store_true",
        help="Do not write the matching .md report when --output-json is used.",
    )
    return parser


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


def _pipeline_b_metadata(extractor: PipelineBExtractor, *, variant_id: str | None) -> dict:
    config = extractor.runtime.config
    return {
        "git_commit": _git_commit(),
        "model_id": config.model_id,
        "device": config.device,
        "dtype": config.dtype,
        "variant_filter": variant_id,
    }


def _git_commit() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


if __name__ == "__main__":
    main()
