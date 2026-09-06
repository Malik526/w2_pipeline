"""Phase 8C.10: full 600-document benchmark with the anchor-relative checkbox detector.

Compares the frozen Phase 8C.2 pipeline (A) against the identical
pipeline with only the `box_13.retirement_plan` detector swapped for the
new anchor-relative one (B). Every other field is verified to be
bit-identical to the frozen Phase 8C.2 prediction -- the *only* intended
behavior change is `box_13.retirement_plan`.
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
from w2_pipeline.extraction.ocr_paddle import PaddleOcrAdapter, PaddleOcrConfig
from w2_pipeline.extraction.parser_2026 import parse_w2_2026_observations
from w2_pipeline.ingestion import IngestionService


def run_benchmark(
    *,
    manifest_path: str | Path,
    frozen_predictions_path: str | Path,
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

    frozen_by_key = _load_frozen_documents(frozen_predictions_path)

    ingestion_service = IngestionService()
    observation_acquirer = ObservationAcquirer(
        ocr_adapter=PaddleOcrAdapter(config=PaddleOcrConfig(device="gpu")),
        enable_anchor_relative_checkbox=True,
    )

    rows: list[dict[str, Any]] = []
    total_fields = 0
    correct_fields = 0
    non_checkbox_mismatches: list[str] = []

    for entry in entries:
        row, field_totals, mismatch = _process_entry(
            entry,
            base_dir=base_dir,
            ingestion_service=ingestion_service,
            observation_acquirer=observation_acquirer,
            frozen_by_key=frozen_by_key,
        )
        rows.append(row)
        total_fields += field_totals[0]
        correct_fields += field_totals[1]
        if mismatch:
            non_checkbox_mismatches.append(mismatch)

    return {
        "manifest_path": str(manifest_path),
        "documents": len(rows),
        "total_fields": total_fields,
        "correct_fields": correct_fields,
        "field_accuracy": correct_fields / total_fields if total_fields else None,
        "non_checkbox_field_mismatches_vs_frozen_phase8c2": non_checkbox_mismatches,
        "rows": rows,
    }


def _load_frozen_documents(path: str | Path) -> dict[tuple[str, str], W2Document | None]:
    frozen: dict[tuple[str, str], W2Document | None] = {}
    with Path(path).open("r", encoding="utf-8") as file_obj:
        for line in file_obj:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            key = (payload["document_id"], payload["variant_id"])
            frozen[key] = W2Document.model_validate(payload["document"]) if payload.get("document") else None
    return frozen


def _process_entry(
    entry: DatasetManifestEntry,
    *,
    base_dir: Path,
    ingestion_service: IngestionService,
    observation_acquirer: ObservationAcquirer,
    frozen_by_key: dict[tuple[str, str], W2Document | None],
) -> tuple[dict[str, Any], tuple[int, int], str | None]:
    document_path = base_dir / entry.document_path
    started = time.perf_counter()
    ingested = ingestion_service.ingest(document_path, document_id=f"{entry.sample_id}:{entry.variant_id}")
    observations = observation_acquirer.acquire(ingested)
    document, _warnings = parse_w2_2026_observations(
        observations,
        document_id=ingested.document_id,
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

    key = (entry.sample_id, entry.variant_id)
    frozen_document = frozen_by_key.get(key)
    mismatch = None
    if frozen_document is not None:
        new_dump = document.model_dump(mode="python")
        old_dump = frozen_document.model_dump(mode="python")
        new_dump["box_13"]["retirement_plan"] = None
        old_dump["box_13"]["retirement_plan"] = None
        if new_dump != old_dump:
            mismatch = f"{key!r}: a non-checkbox field diverged from the frozen Phase 8C.2 prediction"

    row = {
        "document_id": entry.sample_id,
        "variant_id": entry.variant_id,
        "warnings": _warnings,
        "employer_name_correct": "employer.name" not in incorrect_field_paths,
        "retirement_plan_correct": "box_13.retirement_plan" not in incorrect_field_paths,
        "total_fields": evaluation.total_fields,
        "correct_fields": evaluation.correct_fields,
        "duration_seconds": duration,
    }
    return row, (evaluation.total_fields, evaluation.correct_fields), mismatch


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_path", type=Path)
    parser.add_argument("frozen_predictions_path", type=Path)
    parser.add_argument("--variant-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-rows-jsonl", type=Path, default=None)
    parser.add_argument("--no-rows", action="store_true")
    args = parser.parse_args(argv)

    report = run_benchmark(
        manifest_path=args.manifest_path,
        frozen_predictions_path=args.frozen_predictions_path,
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
