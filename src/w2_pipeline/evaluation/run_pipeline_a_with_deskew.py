"""Phase 8C.9: full 600-document benchmark with conditional scan-deskew enabled.

Compares the frozen Phase 8C.2 pipeline (A) against the identical
pipeline plus conditional small-angle scan-deskew preprocessing (B). The
only intended variable is the deskew step -- same PaddleOCR
configuration, same parser, same checkbox logic, same canonical schema,
same 24 evaluated fields, same evaluator (`compare_w2_documents` with
each manifest entry's own `evaluated_field_paths`, exactly matching
Phase 8C.2's methodology).

Per-document diagnostics (`estimated_skew_angle_degrees`,
`correction_triggered`, ...) are gathered via one direct
`deskew_image_if_needed` call for reporting purposes; the actual
extraction is produced by the real, unmodified `PipelineAExtractor` with
`ObservationAcquirer(enable_conditional_deskew=True)` -- the same
production code path a real caller would use, not a reimplementation.
This means skew detection runs twice per document (once for the report,
once inside the real acquirer); both calls are deterministic and
side-effect-free except for writing the same corrected file to the same
deterministic path, so this redundancy costs a little compute but never
affects correctness.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.comparison import compare_w2_documents
from w2_pipeline.evaluation.manifest import DatasetManifestEntry, load_manifest_jsonl
from w2_pipeline.extraction.acquisition import ObservationAcquirer
from w2_pipeline.extraction.deskew import DEFAULT_TRIGGER_THRESHOLD_DEGREES, deskew_image_if_needed
from w2_pipeline.extraction.ocr_paddle import PaddleOcrAdapter, PaddleOcrConfig
from w2_pipeline.extraction.parser_2026 import compute_employer_name_observation_count
from w2_pipeline.ingestion import IngestionService


def run_benchmark(
    *,
    manifest_path: str | Path,
    threshold_degrees: float = DEFAULT_TRIGGER_THRESHOLD_DEGREES,
    variant_id: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    manifest = load_manifest_jsonl(manifest_path)
    base_dir = manifest_path.parent
    entries = manifest.entries
    if variant_id is not None:
        entries = [entry for entry in entries if entry.variant_id == variant_id]
    if limit is not None:
        entries = entries[:limit]

    ingestion_service = IngestionService()
    deskew_output_dir = base_dir / ".phase8c9_deskew_cache"
    extractor_observation_acquirer = ObservationAcquirer(
        ocr_adapter=PaddleOcrAdapter(config=PaddleOcrConfig(device="gpu")),
        enable_conditional_deskew=True,
        deskew_threshold_degrees=threshold_degrees,
        deskew_output_dir=deskew_output_dir,
    )
    from w2_pipeline.extraction.parser_2026 import parse_w2_2026_observations

    rows: list[dict[str, Any]] = []
    total_fields = 0
    correct_fields = 0

    for entry in entries:
        row, field_totals = _process_entry(
            entry,
            base_dir=base_dir,
            ingestion_service=ingestion_service,
            observation_acquirer=extractor_observation_acquirer,
            deskew_output_dir=deskew_output_dir,
            threshold_degrees=threshold_degrees,
            parse_fn=parse_w2_2026_observations,
        )
        rows.append(row)
        total_fields += field_totals[0]
        correct_fields += field_totals[1]

    return {
        "manifest_path": str(manifest_path),
        "threshold_degrees": threshold_degrees,
        "documents": len(rows),
        "total_fields": total_fields,
        "correct_fields": correct_fields,
        "field_accuracy": correct_fields / total_fields if total_fields else None,
        "rows": rows,
    }


def _process_entry(
    entry: DatasetManifestEntry,
    *,
    base_dir: Path,
    ingestion_service: IngestionService,
    observation_acquirer: ObservationAcquirer,
    deskew_output_dir: Path,
    threshold_degrees: float,
    parse_fn,
) -> tuple[dict[str, Any], tuple[int, int]]:
    document_path = base_dir / entry.document_path

    diagnostic_start = time.perf_counter()
    _resolved_path, angle, triggered = deskew_image_if_needed(
        document_path, output_dir=deskew_output_dir, threshold_degrees=threshold_degrees
    )
    detection_duration = time.perf_counter() - diagnostic_start

    started = time.perf_counter()
    ingested = ingestion_service.ingest(document_path, document_id=f"{entry.sample_id}:{entry.variant_id}")
    observations = observation_acquirer.acquire(ingested)
    document, _warnings = parse_fn(
        observations,
        document_id=entry.sample_id,
        source_filename=ingested.source_filename,
        source_type=ingested.source_type,
    )
    duration = time.perf_counter() - started

    ground_truth = W2Document.model_validate_json((base_dir / entry.ground_truth_path).read_text(encoding="utf-8"))
    evaluation = compare_w2_documents(
        expected=ground_truth,
        predicted=document,
        sample_id=entry.sample_id,
        variant_id=entry.variant_id,
        pipeline_id="pipeline_a",
        evaluated_field_paths=entry.evaluated_field_paths,
    )
    incorrect_field_paths = {failure.field_path for failure in evaluation.failures if failure.field_path}
    employer_name_observation_count = compute_employer_name_observation_count(document, observations.observations)

    row = {
        "document_id": entry.sample_id,
        "variant_id": entry.variant_id,
        "estimated_skew_angle_degrees": angle,
        "correction_triggered": triggered,
        "detection_duration_seconds": detection_duration,
        "employer_name_correct": "employer.name" not in incorrect_field_paths,
        "retirement_plan_correct": "box_13.retirement_plan" not in incorrect_field_paths,
        "employer_name_observation_count": employer_name_observation_count,
        "total_fields": evaluation.total_fields,
        "correct_fields": evaluation.correct_fields,
        "field_error_count": evaluation.total_fields - evaluation.correct_fields,
        "duration_seconds": duration,
    }
    return row, (evaluation.total_fields, evaluation.correct_fields)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_path", type=Path)
    parser.add_argument("--threshold-degrees", type=float, default=DEFAULT_TRIGGER_THRESHOLD_DEGREES)
    parser.add_argument("--variant-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-rows-jsonl", type=Path, default=None)
    parser.add_argument("--no-rows", action="store_true")
    args = parser.parse_args(argv)

    report = run_benchmark(
        manifest_path=args.manifest_path,
        threshold_degrees=args.threshold_degrees,
        variant_id=args.variant_id,
        limit=args.limit,
    )

    rows = report["rows"]
    if args.output_rows_jsonl is not None:
        args.output_rows_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with args.output_rows_jsonl.open("w", encoding="utf-8", newline="\n") as file_obj:
            for row in rows:
                file_obj.write(json.dumps(row))
                file_obj.write("\n")

    summary = {key: value for key, value in report.items() if key != "rows"}
    if not args.no_rows:
        summary["rows"] = rows

    text = json.dumps(summary, indent=2, sort_keys=True)
    print(text)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
