"""Phase 8C.4: instrumented PaddleOCR run capturing native OCR confidence.

This is NOT a replacement extraction benchmark and does not produce a new
`PredictionRecord` artifact comparable to Phase 8C.2's frozen files. Its
only purpose is confidence analysis: for each of the 600 manifest
documents, it runs the exact same acquisition + parsing path
`PipelineAExtractor` uses (`ObservationAcquirer.acquire` then
`parse_w2_2026_observations`, called directly rather than through
`PipelineAExtractor.extract_ingested` only so the intermediate
`ObservationSet` -- now confidence-bearing -- can be kept for
`w2_pipeline.evaluation.field_confidence` to match against), scores it
against ground truth the same way `evaluate_manifest` does
(`compare_w2_documents` with the manifest's own `evaluated_field_paths`),
and additionally derives per-field OCR-confidence provenance.

Because this reruns OCR (PaddleOCR gives bit-identical results for a
bit-identical input, but a second run is still a second inference pass,
not a re-read of the frozen Phase 8C.2 artifact), this script's own
accuracy summary is checked against the frozen Phase 8C.2 numbers as a
stability guard -- see `verify_against_phase8c2` and
`docs/experiments/phase8c4-paddle-native-confidence-analysis.md`.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.comparison import compare_w2_documents
from w2_pipeline.evaluation.field_confidence import (
    CONFIDENCE_ANALYSIS_FIELD_PATHS,
    find_all_field_confidence_matches,
)
from w2_pipeline.evaluation.manifest import DatasetManifestEntry, load_manifest_jsonl
from w2_pipeline.extraction.acquisition import ObservationAcquirer
from w2_pipeline.extraction.ocr_paddle import PaddleOcrAdapter, PaddleOcrConfig
from w2_pipeline.extraction.parser_2026 import parse_w2_2026_observations
from w2_pipeline.ingestion import IngestionService


def run_confidence_analysis(
    *,
    manifest_path: str | Path,
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
    observation_acquirer = ObservationAcquirer(ocr_adapter=PaddleOcrAdapter(config=PaddleOcrConfig(device="gpu")))

    rows: list[dict[str, Any]] = []
    total_fields = 0
    correct_fields = 0
    failed_documents = 0
    total_duration = 0.0

    for entry in entries:
        row, field_totals, duration = _process_entry(
            entry, base_dir=base_dir, ingestion_service=ingestion_service, observation_acquirer=observation_acquirer
        )
        rows.append(row)
        if row["status"] != "success":
            failed_documents += 1
        else:
            total_fields += field_totals[0]
            correct_fields += field_totals[1]
        total_duration += duration

    return {
        "manifest_path": str(manifest_path),
        "documents": len(entries),
        "failed_documents": failed_documents,
        "total_fields": total_fields,
        "correct_fields": correct_fields,
        "field_accuracy": correct_fields / total_fields if total_fields else None,
        "average_duration_seconds": total_duration / len(entries) if entries else None,
        "confidence_analysis_field_paths": list(CONFIDENCE_ANALYSIS_FIELD_PATHS),
        "rows": rows,
    }


def _process_entry(
    entry: DatasetManifestEntry,
    *,
    base_dir: Path,
    ingestion_service: IngestionService,
    observation_acquirer: ObservationAcquirer,
) -> tuple[dict[str, Any], tuple[int, int], float]:
    document_path = base_dir / entry.document_path
    started = time.perf_counter()
    try:
        ingested = ingestion_service.ingest(document_path, document_id=entry.sample_id)
        observations = observation_acquirer.acquire(ingested)
        document, warnings = parse_w2_2026_observations(
            observations,
            document_id=entry.sample_id,
            source_filename=ingested.source_filename,
            source_type=ingested.source_type,
        )
    except Exception as exc:  # noqa: BLE001 - this analysis must not abort on one bad document.
        duration = time.perf_counter() - started
        return (
            {
                "document_id": entry.sample_id,
                "variant_id": entry.variant_id,
                "status": "extraction_failed",
                "message": f"{exc.__class__.__name__}: {exc}",
            },
            (0, 0),
            duration,
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

    confidence_matches = find_all_field_confidence_matches(document, observations.observations)
    field_rows = {
        field_path: {
            "correct": field_path not in incorrect_field_paths,
            "matched": match.matched,
            "contributing_observation_count": match.contributing_observation_count,
            "confidences": match.confidences,
        }
        for field_path, match in confidence_matches.items()
    }

    return (
        {
            "document_id": entry.sample_id,
            "variant_id": entry.variant_id,
            "status": "success",
            "duration_seconds": duration,
            "total_fields": evaluation.total_fields,
            "correct_fields": evaluation.correct_fields,
            "fields": field_rows,
        },
        (evaluation.total_fields, evaluation.correct_fields),
        duration,
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_path", type=Path)
    parser.add_argument("--variant-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-rows-jsonl", type=Path, default=None)
    parser.add_argument("--no-rows", action="store_true")
    args = parser.parse_args(argv)

    report = run_confidence_analysis(manifest_path=args.manifest_path, variant_id=args.variant_id, limit=args.limit)

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
