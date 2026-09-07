"""Phase 8D.1A: validator effectiveness under the expanded ground-truth contract.

Re-extracts all 600 documents with the real, unmodified `PipelineAExtractor`
(no flags -- the current production default), attaches the same
`employer_name_observation_count`/`box_13_checkbox_evidence` signals
Phase 8C.12 already established the pattern for, validates each
document, and scores against the Phase 8D.1A-repaired ground truth
(employer/employee address, Box 12, state/local now included).

Unlike Phase 8C.12's `run_pipeline_a_with_checkbox_evidence_signals.py`,
this does NOT assert byte-identical-to-frozen-Phase-8C.2 extraction:
that comparison assumed only `box_13.retirement_plan` could legitimately
differ, but this phase's new address/Box-12/state-local parser fallbacks
intentionally populate fields the frozen baseline always left empty --
divergence there is the expected, desired outcome, not a regression to
guard against.
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
from w2_pipeline.extraction.pipeline_a import PipelineAExtractor
from w2_pipeline.ingestion import IngestionService
from w2_pipeline.validation.models import ExtractionSignals
from w2_pipeline.validation.validator import validate_w2_document


def _signals_for_result(result: Any) -> ExtractionSignals:
    checkbox = result.box_13_checkbox_evidence
    return ExtractionSignals(
        pipeline_id="pipeline_a",
        route=result.route.value,
        employer_name_observation_count=result.employer_name_observation_count,
        checkbox_evidence_detection_method=checkbox.detection_method if checkbox else None,
        checkbox_evidence_fallback_used=checkbox.fallback_used if checkbox else None,
        checkbox_evidence_anchor_found=checkbox.anchor_found if checkbox else None,
        checkbox_evidence_checkbox_found=checkbox.checkbox_found if checkbox else None,
        checkbox_evidence_anchor_distance_px=checkbox.anchor_distance_px if checkbox else None,
        checkbox_evidence_horizontal_alignment_offset_px=(
            checkbox.horizontal_alignment_offset_px if checkbox else None
        ),
        checkbox_evidence_shape_score=checkbox.shape_score if checkbox else None,
        checkbox_evidence_interior_ink_ratio=checkbox.interior_ink_ratio if checkbox else None,
        checkbox_evidence_decision_margin=checkbox.decision_margin if checkbox else None,
    )


def run(
    *,
    manifest_path: str | Path,
    paddle_device: str = "gpu",
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

    extractor = PipelineAExtractor(
        observation_acquirer=ObservationAcquirer(ocr_adapter=PaddleOcrAdapter(config=PaddleOcrConfig(device=paddle_device)))
    )
    ingestion_service: IngestionService = extractor.ingestion_service

    rows = [_process_entry(entry, base_dir=base_dir, extractor=extractor) for entry in entries]
    return _build_report(rows, manifest_path=manifest_path)


def _process_entry(
    entry: DatasetManifestEntry, *, base_dir: Path, extractor: PipelineAExtractor
) -> dict[str, Any]:
    document_path = base_dir / entry.document_path
    started = time.perf_counter()
    ingested = extractor.ingestion_service.ingest(document_path, document_id=f"{entry.sample_id}:{entry.variant_id}")
    result = extractor.extract_ingested(ingested)
    duration = time.perf_counter() - started

    signals = _signals_for_result(result)
    validation_result = validate_w2_document(result.document, signals=signals)

    ground_truth = W2Document.model_validate_json((base_dir / entry.ground_truth_path).read_text(encoding="utf-8"))
    evaluation = compare_w2_documents(
        expected=ground_truth,
        predicted=result.document,
        sample_id=entry.sample_id,
        variant_id=entry.variant_id,
        pipeline_id="pipeline_a",
        evaluated_field_paths=entry.evaluated_field_paths,
    )
    has_error = evaluation.correct_fields < evaluation.total_fields
    failing_field_paths = [failure.field_path for failure in evaluation.failures if failure.field_path]

    return {
        "document_id": entry.sample_id,
        "variant_id": entry.variant_id,
        "has_error": has_error,
        "failing_field_paths": failing_field_paths,
        "total_fields": evaluation.total_fields,
        "correct_fields": evaluation.correct_fields,
        "validation_status": validation_result.status.value,
        "validation_issues": [
            {"code": issue.code, "severity": issue.severity.value, "field_path": issue.field_path}
            for issue in validation_result.issues
        ],
        "duration_seconds": duration,
    }


def _is_needs_review(row: dict[str, Any]) -> bool:
    return row["validation_status"] == "needs_review"


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    erroneous = [row for row in rows if row["has_error"]]
    correct = [row for row in rows if not row["has_error"]]
    needs_review = [row for row in rows if _is_needs_review(row)]
    accepted = [row for row in rows if not _is_needs_review(row)]

    erroneous_reviewed = [row for row in erroneous if _is_needs_review(row)]
    erroneous_accepted = [row for row in erroneous if not _is_needs_review(row)]
    correct_reviewed = [row for row in correct if _is_needs_review(row)]
    correct_accepted = [row for row in correct if not _is_needs_review(row)]

    def ratio(numerator: int, denominator: int) -> float | None:
        return numerator / denominator if denominator else None

    return {
        "total_documents": total,
        "correct_documents": len(correct),
        "erroneous_documents": len(erroneous),
        "accepted_documents": len(accepted),
        "needs_review_documents": len(needs_review),
        "correct_accepted": len(correct_accepted),
        "correct_routed_needs_review": len(correct_reviewed),
        "erroneous_accepted": len(erroneous_accepted),
        "erroneous_routed_needs_review": len(erroneous_reviewed),
        "error_detection_recall": ratio(len(erroneous_reviewed), len(erroneous)),
        "false_review_rate": ratio(len(correct_reviewed), len(correct)),
        "automatic_acceptance_rate": ratio(len(accepted), total),
        "unsafe_acceptance_rate": ratio(len(erroneous_accepted), total),
        "review_queue_precision": ratio(len(erroneous_reviewed), len(needs_review)),
    }


def _unsafe_acceptance_by_field_family(rows: list[dict[str, Any]]) -> dict[str, int]:
    def family(field_path: str) -> str:
        if field_path.startswith("employer.address") or field_path.startswith("employee.address"):
            return "address"
        if field_path.startswith("box_12_entries"):
            return "box_12"
        if field_path.startswith("box_13"):
            return "box_13"
        if field_path.startswith("state_local_entries"):
            return "state_local"
        if field_path == "employer.name":
            return "employer_name"
        if field_path.startswith("employee.") or field_path.startswith("employer."):
            return "identity"
        return "other"

    counts: dict[str, int] = {}
    for row in rows:
        if row["has_error"] and not _is_needs_review(row):
            families = {family(path) for path in row["failing_field_paths"]}
            for fam in families:
                counts[fam] = counts.get(fam, 0) + 1
    return counts


def _build_report(rows: list[dict[str, Any]], *, manifest_path: str | Path) -> dict[str, Any]:
    variant_ids = sorted({row["variant_id"] for row in rows})
    return {
        "source_manifest": str(manifest_path),
        "overall": _summarize(rows),
        "by_variant": {variant_id: _summarize([r for r in rows if r["variant_id"] == variant_id]) for variant_id in variant_ids},
        "unsafe_acceptance_by_field_family": _unsafe_acceptance_by_field_family(rows),
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_path", type=Path)
    parser.add_argument("--paddle-device", default="gpu")
    parser.add_argument("--variant-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-rows-jsonl", type=Path, default=None)
    parser.add_argument("--no-rows", action="store_true")
    args = parser.parse_args(argv)

    report = run(
        manifest_path=args.manifest_path,
        paddle_device=args.paddle_device,
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
