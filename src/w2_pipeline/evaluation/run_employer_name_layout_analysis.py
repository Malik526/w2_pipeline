"""Phase 8C.6: instrumented PaddleOCR run measuring employer.name layout signals.

Not a replacement extraction benchmark (mirrors Phase 8C.4's
`run_pipeline_a_confidence.py` pattern). For each of the 600 manifest
documents, runs the same acquisition + parsing path
`PipelineAExtractor` uses, keeps the intermediate `ObservationSet` (raw
bounding boxes, no confidence needed here), and derives geometry-only
`employer.name` layout signals via
`w2_pipeline.evaluation.employer_name_layout_signals`. Correctness is
determined by exact string comparison against ground truth
`employer.name`, consulted only after the geometry signals are already
computed (leakage boundary).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.employer_name_layout_signals import compute_layout_signals
from w2_pipeline.evaluation.manifest import DatasetManifestEntry, load_manifest_jsonl
from w2_pipeline.extraction.acquisition import ObservationAcquirer
from w2_pipeline.extraction.ocr_paddle import PaddleOcrAdapter, PaddleOcrConfig
from w2_pipeline.extraction.parser_2026 import parse_w2_2026_observations
from w2_pipeline.ingestion import IngestionService


def run_layout_signal_analysis(
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

    rows = [_process_entry(entry, base_dir=base_dir, ingestion_service=ingestion_service, observation_acquirer=observation_acquirer) for entry in entries]

    return {
        "manifest_path": str(manifest_path),
        "documents": len(rows),
        "correct_documents": sum(1 for row in rows if row["correct"]),
        "erroneous_documents": sum(1 for row in rows if not row["correct"]),
        "rows": rows,
    }


def _process_entry(
    entry: DatasetManifestEntry,
    *,
    base_dir: Path,
    ingestion_service: IngestionService,
    observation_acquirer: ObservationAcquirer,
) -> dict[str, Any]:
    document_path = base_dir / entry.document_path
    try:
        ingested = ingestion_service.ingest(document_path, document_id=entry.sample_id)
        observations = observation_acquirer.acquire(ingested)
        document, _warnings = parse_w2_2026_observations(
            observations,
            document_id=entry.sample_id,
            source_filename=ingested.source_filename,
            source_type=ingested.source_type,
        )
    except Exception as exc:  # noqa: BLE001 - this analysis must not abort on one bad document.
        return {
            "document_id": entry.sample_id,
            "variant_id": entry.variant_id,
            "status": "extraction_failed",
            "message": f"{exc.__class__.__name__}: {exc}",
            "correct": False,
            "predicted_name": None,
            "signals": None,
        }

    predicted_name = document.employer.name

    # LEAKAGE BOUNDARY: geometry signals are computed from the prediction
    # and its own observations alone.
    signals = compute_layout_signals(predicted_name, observations.observations)

    ground_truth = W2Document.model_validate_json((base_dir / entry.ground_truth_path).read_text(encoding="utf-8"))
    ground_truth_name = ground_truth.employer.name
    is_correct = (
        predicted_name is not None
        and ground_truth_name is not None
        and predicted_name.strip() == ground_truth_name.strip()
    )

    return {
        "document_id": entry.sample_id,
        "variant_id": entry.variant_id,
        "status": "success",
        "predicted_name": predicted_name,
        "correct": is_correct,
        "signals": {
            "matched": signals.matched,
            "observation_count": signals.observation_count,
            "y_min": signals.y_min,
            "y_max": signals.y_max,
            "vertical_span_px": signals.vertical_span_px,
            "vertical_span_ratio": signals.vertical_span_ratio,
            "zone_span_ratio": signals.zone_span_ratio,
            "max_center_y_gap_px": signals.max_center_y_gap_px,
            "max_center_y_gap_ratio": signals.max_center_y_gap_ratio,
            "tight_sub_row_count": signals.tight_sub_row_count,
        },
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_path", type=Path)
    parser.add_argument("--variant-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-rows-jsonl", type=Path, default=None)
    parser.add_argument("--no-rows", action="store_true")
    args = parser.parse_args(argv)

    report = run_layout_signal_analysis(manifest_path=args.manifest_path, variant_id=args.variant_id, limit=args.limit)

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
