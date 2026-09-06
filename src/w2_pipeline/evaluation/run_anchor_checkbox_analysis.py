"""Phase 8C.10: localization + classification analysis for the anchor-relative checkbox detector.

Runs the real, unmodified `PipelineAExtractor`'s OCR path (no second OCR
pass -- the same observations Pipeline A already produces) plus
`w2_pipeline.extraction.checkbox_anchor.detect_retirement_plan` against
all 600 manifest documents. Ground truth is loaded and compared only
*after* detection completes, purely to label correctness and support
offline threshold calibration -- never as a detection input.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from w2_pipeline.evaluation.manifest import DatasetManifestEntry, load_manifest_jsonl
from w2_pipeline.extraction.acquisition import ObservationAcquirer
from w2_pipeline.extraction.checkbox_anchor import DEFAULT_INTERIOR_INK_THRESHOLD, detect_retirement_plan
from w2_pipeline.extraction.ocr_paddle import PaddleOcrAdapter, PaddleOcrConfig
from w2_pipeline.ingestion import IngestionService


def run_analysis(
    *,
    manifest_path: str | Path,
    interior_ink_threshold: float = DEFAULT_INTERIOR_INK_THRESHOLD,
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

    rows = [
        _process_entry(
            entry,
            base_dir=base_dir,
            ingestion_service=ingestion_service,
            observation_acquirer=observation_acquirer,
            interior_ink_threshold=interior_ink_threshold,
        )
        for entry in entries
    ]

    return {
        "manifest_path": str(manifest_path),
        "interior_ink_threshold": interior_ink_threshold,
        "documents": len(rows),
        "anchor_found_count": sum(1 for row in rows if row["anchor_found"]),
        "checkbox_found_count": sum(1 for row in rows if row["checkbox_found"]),
        "rows": rows,
    }


def _process_entry(
    entry: DatasetManifestEntry,
    *,
    base_dir: Path,
    ingestion_service: IngestionService,
    observation_acquirer: ObservationAcquirer,
    interior_ink_threshold: float,
) -> dict[str, Any]:
    document_path = base_dir / entry.document_path
    ground_truth_path = base_dir / entry.ground_truth_path

    started = time.perf_counter()
    ingested = ingestion_service.ingest(document_path, document_id=f"{entry.sample_id}:{entry.variant_id}")
    observations = observation_acquirer.acquire(ingested)
    detection_started = time.perf_counter()
    detection = detect_retirement_plan(
        document_path, observations.observations, interior_ink_threshold=interior_ink_threshold
    )
    detection_duration = time.perf_counter() - detection_started
    total_duration = time.perf_counter() - started

    expected = json.loads(ground_truth_path.read_text(encoding="utf-8"))["box_13"]["retirement_plan"]

    return {
        "document_id": entry.sample_id,
        "variant_id": entry.variant_id,
        "anchor_found": detection.anchor_found,
        "checkbox_found": detection.checkbox_found,
        "checkbox_bbox": (
            [detection.checkbox.bbox.x0, detection.checkbox.bbox.y0, detection.checkbox.bbox.x1, detection.checkbox.bbox.y1]
            if detection.checkbox is not None
            else None
        ),
        "anchor_distance_px": detection.checkbox.anchor_distance_px if detection.checkbox is not None else None,
        "alignment_offset_px": detection.checkbox.horizontal_alignment_offset_px if detection.checkbox is not None else None,
        "shape_score": detection.checkbox.shape_score if detection.checkbox is not None else None,
        "interior_ink_ratio": detection.interior_ink_ratio,
        "decision_margin": detection.decision_margin,
        "predicted_retirement_plan": detection.retirement_plan,
        "expected_retirement_plan": expected,
        "correct": detection.retirement_plan == expected,
        "detection_duration_seconds": detection_duration,
        "duration_seconds": total_duration,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_path", type=Path)
    parser.add_argument("--interior-ink-threshold", type=float, default=DEFAULT_INTERIOR_INK_THRESHOLD)
    parser.add_argument("--variant-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-rows-jsonl", type=Path, default=None)
    parser.add_argument("--no-rows", action="store_true")
    args = parser.parse_args(argv)

    report = run_analysis(
        manifest_path=args.manifest_path,
        interior_ink_threshold=args.interior_ink_threshold,
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
