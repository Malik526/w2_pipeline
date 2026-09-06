"""Phase 8C.8: fresh instrumented PaddleOCR run carrying employer.name layout provenance.

Not a replacement extraction benchmark. Uses the real, unmodified
`PipelineAExtractor` (now emitting
`ExtractionResult.employer_name_observation_count`, promoted into
production this phase) to produce a fresh `PredictionRecord` set for all
600 manifest documents, storing the layout-provenance count in
`pipeline_metadata` (the existing flexible metadata bag) so
`w2_pipeline.evaluation.validator_effectiveness_predictions` can thread it
into `ExtractionSignals` unchanged.

**Stability requirement**: since the frozen Phase 8C.2 `PredictionRecord`
artifact never carried this signal, a fresh extraction pass is
unavoidable to obtain it -- but the extracted `document` for every one of
the 600 documents is verified byte-identical to Phase 8C.2's frozen
prediction before anything is scored. A real mismatch stops the run
rather than silently proceeding (this phase promotes new *validation*
behavior only; it must not also silently re-benchmark extraction).
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.manifest import DatasetManifestEntry, load_manifest_jsonl
from w2_pipeline.evaluation.predictions import PredictionRecord, write_prediction_records_jsonl
from w2_pipeline.extraction.acquisition import ObservationAcquirer
from w2_pipeline.extraction.ocr_paddle import PaddleOcrAdapter, PaddleOcrConfig
from w2_pipeline.extraction.pipeline_a import PipelineAExtractor
from w2_pipeline.ingestion import IngestionService


def run(
    *,
    manifest_path: str | Path,
    frozen_predictions_path: str | Path,
    variant_id: str | None = None,
    limit: int | None = None,
) -> tuple[list[PredictionRecord], dict[str, Any]]:
    manifest_path = Path(manifest_path)
    manifest = load_manifest_jsonl(manifest_path)
    base_dir = manifest_path.parent
    entries = manifest.entries
    if variant_id is not None:
        entries = [entry for entry in entries if entry.variant_id == variant_id]
    if limit is not None:
        entries = entries[:limit]

    frozen_by_key = _load_frozen_documents(frozen_predictions_path)

    extractor = PipelineAExtractor(observation_acquirer=ObservationAcquirer(ocr_adapter=PaddleOcrAdapter(config=PaddleOcrConfig(device="gpu"))))

    records: list[PredictionRecord] = []
    mismatches: list[str] = []
    total_duration = 0.0

    for entry in entries:
        record, duration, mismatch = _process_entry(entry, base_dir=base_dir, extractor=extractor, frozen_by_key=frozen_by_key)
        records.append(record)
        total_duration += duration
        if mismatch:
            mismatches.append(mismatch)

    stability_report = {
        "documents_checked": len(entries),
        "documents_matching_frozen_phase8c2": len(entries) - len(mismatches),
        "mismatches": mismatches,
        "average_extraction_duration_seconds": total_duration / len(entries) if entries else None,
    }
    if mismatches:
        raise ValueError(
            f"{len(mismatches)} document(s) diverged from the frozen Phase 8C.2 prediction; "
            f"refusing to proceed. First mismatch: {mismatches[0]}"
        )
    return records, stability_report


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
    extractor: PipelineAExtractor,
    frozen_by_key: dict[tuple[str, str], W2Document | None],
) -> tuple[PredictionRecord, float, str | None]:
    document_path = base_dir / entry.document_path
    started = time.perf_counter()
    # Matches `w2_pipeline.evaluation.runner._evaluate_entry`'s own
    # `ExtractionInput.document_id` convention exactly (the same one Phase
    # 8C.2's frozen run used) -- `metadata.document_id` is excluded from
    # `compare_w2_documents` scoring, but the stability check below does a
    # full document equality, so the convention must match precisely.
    ingested = extractor.ingestion_service.ingest(
        document_path, document_id=f"{entry.sample_id}:{entry.variant_id}"
    )
    result = extractor.extract_ingested(ingested)
    duration = time.perf_counter() - started

    key = (entry.sample_id, entry.variant_id)
    frozen_document = frozen_by_key.get(key)
    mismatch = None
    if frozen_document is None or result.document != frozen_document:
        mismatch = f"{key!r}: fresh extraction diverged from frozen Phase 8C.2 prediction"

    record = PredictionRecord(
        document_id=entry.sample_id,
        variant_id=entry.variant_id,
        pipeline_id=extractor.pipeline_id,
        status="success",
        document=result.document,
        extraction_route=result.route.value,
        duration_seconds=duration,
        pipeline_metadata={"employer_name_observation_count": result.employer_name_observation_count},
    )
    return record, duration, mismatch


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_path", type=Path)
    parser.add_argument("frozen_predictions_path", type=Path)
    parser.add_argument("--variant-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-predictions-jsonl", type=Path, required=True)
    parser.add_argument("--output-stability-json", type=Path, default=None)
    args = parser.parse_args(argv)

    records, stability_report = run(
        manifest_path=args.manifest_path,
        frozen_predictions_path=args.frozen_predictions_path,
        variant_id=args.variant_id,
        limit=args.limit,
    )

    write_prediction_records_jsonl(args.output_predictions_jsonl, records)
    print(json.dumps(stability_report, indent=2, sort_keys=True))
    if args.output_stability_json is not None:
        args.output_stability_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_stability_json.write_text(json.dumps(stability_report, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
