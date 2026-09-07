"""Phase 8D.1B: validator effectiveness with address/Box-12 evidence threaded.

Extends Phase 8D.1A's `run_expanded_validator_effectiveness.py` with the
two new evidence signals this phase adds --
`employer_address_evidence`/`employee_address_evidence` and
`box_12_amount_without_code_found` -- reusing that module's reporting
helpers unchanged (`_summarize`, `_unsafe_acceptance_by_field_family`,
`_build_report`) so the two runs are directly comparable. Does not
modify or re-run the Phase 8D.1A script itself, matching this project's
convention of one new instrumented-run script per phase rather than
mutating a previous phase's frozen script.
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
from w2_pipeline.evaluation.run_expanded_validator_effectiveness import (
    _build_report,
)
from w2_pipeline.extraction.acquisition import ObservationAcquirer
from w2_pipeline.extraction.ocr_paddle import PaddleOcrAdapter, PaddleOcrConfig
from w2_pipeline.extraction.pipeline_a import PipelineAExtractor
from w2_pipeline.validation.models import ExtractionSignals
from w2_pipeline.validation.validator import validate_w2_document


def _signals_for_result(result: Any) -> ExtractionSignals:
    checkbox = result.box_13_checkbox_evidence
    employer_address = result.employer_address_evidence
    employee_address = result.employee_address_evidence
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
        box_12_amount_without_code_found=result.box_12_amount_without_code_found,
        employer_address_evidence_region_observation_count=(
            employer_address.region_observation_count if employer_address else None
        ),
        employer_address_evidence_usable_row_count=(
            employer_address.usable_row_count if employer_address else None
        ),
        employer_address_evidence_parse_complete=(
            employer_address.parse_complete if employer_address else None
        ),
        employee_address_evidence_region_observation_count=(
            employee_address.region_observation_count if employee_address else None
        ),
        employee_address_evidence_usable_row_count=(
            employee_address.usable_row_count if employee_address else None
        ),
        employee_address_evidence_parse_complete=(
            employee_address.parse_complete if employee_address else None
        ),
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
