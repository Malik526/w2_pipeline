"""Phase 8C.9 Section 4: scan all 600 source images with the skew detector, uncorrected.

Runs `w2_pipeline.extraction.deskew.estimate_skew_angle_degrees` against
every manifest document's real image file -- no correction is applied
here, and the detector itself never sees `variant_id`, filename, or any
other label. `variant_id` is attached to each row only *after* detection
completes, strictly for this script's own offline distribution analysis
-- exactly the ordering the brief requires.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from w2_pipeline.evaluation.manifest import load_manifest_jsonl
from w2_pipeline.extraction.deskew import estimate_skew_angle_degrees, should_deskew


def run_scan(
    *,
    manifest_path: str | Path,
    threshold_degrees: float,
    limit: int | None = None,
) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    manifest = load_manifest_jsonl(manifest_path)
    base_dir = manifest_path.parent
    entries = manifest.entries
    if limit is not None:
        entries = entries[:limit]

    rows: list[dict[str, Any]] = []
    for entry in entries:
        image_path = base_dir / entry.document_path
        started = time.perf_counter()
        angle = estimate_skew_angle_degrees(image_path)
        duration = time.perf_counter() - started
        rows.append(
            {
                "document_id": entry.sample_id,
                "variant_id": entry.variant_id,  # attached only after detection, for analysis only
                "estimated_skew_angle_degrees": angle,
                "absolute_skew_degrees": abs(angle),
                "would_trigger_deskew": should_deskew(angle, threshold_degrees=threshold_degrees),
                "detection_duration_seconds": duration,
            }
        )

    return {
        "manifest_path": str(manifest_path),
        "threshold_degrees": threshold_degrees,
        "documents": len(rows),
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_path", type=Path)
    parser.add_argument("--threshold-degrees", type=float, default=0.75)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-rows-jsonl", type=Path, required=True)
    parser.add_argument("--output-summary-json", type=Path, default=None)
    args = parser.parse_args(argv)

    report = run_scan(manifest_path=args.manifest_path, threshold_degrees=args.threshold_degrees, limit=args.limit)

    args.output_rows_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_rows_jsonl.open("w", encoding="utf-8", newline="\n") as file_obj:
        for row in report["rows"]:
            file_obj.write(json.dumps(row))
            file_obj.write("\n")

    summary = {key: value for key, value in report.items() if key != "rows"}
    print(json.dumps(summary, indent=2, sort_keys=True))
    if args.output_summary_json is not None:
        args.output_summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
