"""Phase 8D.8A: instrumented PaddleOCR run for the recognition-confidence
residual audit.

For each manifest document this runs the exact same acquisition + parsing
path `PipelineAExtractor` uses -- `ObservationAcquirer.acquire` then
`parse_w2_2026_observations`, called directly (as Phase 8C.4's
`run_pipeline_a_confidence.py` does) only so the intermediate,
confidence-bearing `ObservationSet` can be kept for
`find_all_field_confidence_matches` -- then builds the SAME
`ExtractionSignals` `run_expanded_validator_effectiveness.py` builds from a
real `ExtractionResult`'s fields (route, employer-name observation count,
checkbox evidence) and calls the real, unmodified `validate_w2_document`.
One OCR pass therefore produces everything this phase needs: raw
observations for confidence provenance, the real validator's routing
decision, and (via ground truth, consulted only afterward) correctness --
never a second inference pass.

This is NOT a replacement extraction benchmark and does not touch
`run_pipeline_a.py` or any frozen Phase 8B/8C.2/8D.1A artifact.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.comparison import compare_w2_documents
from w2_pipeline.evaluation.field_confidence import find_all_field_confidence_matches
from w2_pipeline.evaluation.manifest import DatasetManifestEntry, load_manifest_jsonl
from w2_pipeline.evaluation.recognition_confidence_residual_audit import (
    RESIDUAL_AUDIT_FIELD_PATHS,
    distribution_summary,
    field_confidence_signal,
    non_ascii_field_values,
    sweep_thresholds,
)
from w2_pipeline.extraction.acquisition import ObservationAcquirer
from w2_pipeline.extraction.models import ExtractionResult, ExtractionWarning
from w2_pipeline.extraction.ocr_paddle import PaddleOcrAdapter, PaddleOcrConfig
from w2_pipeline.extraction.parser_2026 import (
    compute_box_12_amount_without_code_found,
    compute_employee_address_evidence,
    compute_employer_address_evidence,
    compute_employer_name_observation_count,
    parse_w2_2026_observations,
)
from w2_pipeline.extraction.signals import build_extraction_signals
from w2_pipeline.ingestion import IngestionService
from w2_pipeline.validation.validator import validate_w2_document

DEFAULT_THRESHOLDS: list[float] = [
    round(0.50 + 0.05 * i, 2) for i in range(9)  # 0.50 .. 0.90
] + [round(0.90 + 0.01 * i, 2) for i in range(1, 10)] + [  # 0.91 .. 0.99
    0.991,
    0.992,
    0.993,
    0.994,
    0.995,
    0.996,
    0.997,
    0.998,
    0.999,
    0.9995,
    0.9999,
]


def _extraction_result_for(document: W2Document, warnings: list[Any], observations: Any) -> ExtractionResult:
    """Build the same `ExtractionResult` `PipelineAExtractor.extract_ingested` would.

    Inlined (rather than calling `extract_ingested` itself) only so the
    intermediate `ObservationSet` -- needed for confidence provenance --
    is not discarded. Every field mirrors the real production wrapper
    exactly (`src/w2_pipeline/extraction/pipeline_a.py`), including the
    Phase 8D.1B address-evidence fields the production validator's
    `_check_address_extraction_evidence` rule actually reads -- omitting
    them (as an earlier version of this script did) silently reproduces
    the pre-8D.1B validator baseline instead of current production
    behavior.
    """

    return ExtractionResult(
        document=document,
        route=observations.route,
        observation_count=len(observations.observations),
        warnings=[
            *warnings,
            *[ExtractionWarning(message=message) for message in observations.warnings],
        ],
        employer_name_observation_count=compute_employer_name_observation_count(
            document, observations.observations
        ),
        box_13_checkbox_evidence=observations.box_13_checkbox_evidence,
        box_12_amount_without_code_found=compute_box_12_amount_without_code_found(observations.observations),
        employer_address_evidence=compute_employer_address_evidence(document, observations.observations),
        employee_address_evidence=compute_employee_address_evidence(document, observations.observations),
    )


def _process_entry(
    entry: DatasetManifestEntry,
    *,
    base_dir: Path,
    ingestion_service: IngestionService,
    observation_acquirer: ObservationAcquirer,
) -> tuple[dict[str, Any], float]:
    document_path = base_dir / entry.document_path
    started = time.perf_counter()
    try:
        ingested = ingestion_service.ingest(document_path, document_id=f"{entry.sample_id}:{entry.variant_id}")
        observations = observation_acquirer.acquire(ingested)
        document, warnings = parse_w2_2026_observations(
            observations,
            document_id=ingested.document_id,
            source_filename=ingested.source_filename,
            source_type=ingested.source_type,
        )
    except Exception as exc:  # noqa: BLE001 - one bad document must not abort the run.
        duration = time.perf_counter() - started
        return (
            {
                "document_id": entry.sample_id,
                "variant_id": entry.variant_id,
                "status": "extraction_failed",
                "message": f"{exc.__class__.__name__}: {exc}",
            },
            duration,
        )

    result = _extraction_result_for(document, warnings, observations)
    signals = build_extraction_signals(result)
    validation_result = validate_w2_document(document, signals=signals)

    ground_truth = W2Document.model_validate_json((base_dir / entry.ground_truth_path).read_text(encoding="utf-8"))
    evaluation = compare_w2_documents(
        expected=ground_truth,
        predicted=document,
        sample_id=entry.sample_id,
        variant_id=entry.variant_id,
        pipeline_id="pipeline_a",
        evaluated_field_paths=entry.evaluated_field_paths,
    )
    failing_field_paths = [failure.field_path for failure in evaluation.failures if failure.field_path]
    has_error = evaluation.correct_fields < evaluation.total_fields

    confidence_matches = find_all_field_confidence_matches(
        document, observations.observations, field_paths=RESIDUAL_AUDIT_FIELD_PATHS
    )
    field_signals = {
        field_path: field_confidence_signal(match) for field_path, match in confidence_matches.items()
    }
    for field_path, signal in field_signals.items():
        signal["correct"] = field_path not in failing_field_paths

    duration = time.perf_counter() - started
    return (
        {
            "document_id": entry.sample_id,
            "variant_id": entry.variant_id,
            "status": "success",
            "duration_seconds": duration,
            "total_fields": evaluation.total_fields,
            "correct_fields": evaluation.correct_fields,
            "has_error": has_error,
            "failing_field_paths": failing_field_paths,
            "validator_status": validation_result.status.value,
            "field_signals": field_signals,
        },
        duration,
    )


def run_audit(
    *,
    manifest_path: str | Path,
    variant_id: str | None = None,
    document_ids: list[str] | None = None,
    limit: int | None = None,
    thresholds: list[float] | None = None,
) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    manifest = load_manifest_jsonl(manifest_path)
    base_dir = manifest_path.parent
    entries = manifest.entries
    if variant_id is not None:
        entries = [entry for entry in entries if entry.variant_id == variant_id]
    if document_ids:
        wanted = set(document_ids)
        entries = [entry for entry in entries if entry.sample_id in wanted]
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
        row, duration = _process_entry(
            entry, base_dir=base_dir, ingestion_service=ingestion_service, observation_acquirer=observation_acquirer
        )
        rows.append(row)
        total_duration += duration
        if row["status"] != "success":
            failed_documents += 1
        else:
            total_fields += row["total_fields"]
            correct_fields += row["correct_fields"]

    successful_rows = [row for row in rows if row["status"] == "success"]

    audit = _build_audit(successful_rows, manifest_path=manifest_path, documents=len(entries))
    audit["failed_documents"] = failed_documents
    audit["total_fields"] = total_fields
    audit["correct_fields"] = correct_fields
    audit["field_accuracy"] = correct_fields / total_fields if total_fields else None
    audit["average_duration_seconds"] = total_duration / len(entries) if entries else None
    audit["total_duration_seconds"] = total_duration

    threshold_report = sweep_thresholds(
        [
            {
                "document_id": row["document_id"],
                "variant_id": row["variant_id"],
                "has_error": row["has_error"],
                "validator_status": row["validator_status"],
                "field_signals": row["field_signals"],
            }
            for row in successful_rows
        ],
        thresholds=thresholds if thresholds is not None else DEFAULT_THRESHOLDS,
    )

    return {"audit": audit, "thresholds": threshold_report, "rows": rows}


def _build_audit(rows: list[dict[str, Any]], *, manifest_path: str | Path, documents: int) -> dict[str, Any]:
    known_residuals = _known_residual_table(rows)

    address_correct: list[float] = []
    address_incorrect: list[dict[str, Any]] = []
    all_correct: list[float] = []
    all_incorrect: list[dict[str, Any]] = []

    from w2_pipeline.evaluation.recognition_confidence_residual_audit import ADDRESS_FIELD_PATHS

    for row in rows:
        for field_path, signal in row["field_signals"].items():
            if signal["selected"] is None:
                continue
            is_address = field_path in ADDRESS_FIELD_PATHS
            if signal["correct"]:
                all_correct.append(signal["selected"])
                if is_address:
                    address_correct.append(signal["selected"])
            else:
                entry = {
                    "document_id": row["document_id"],
                    "variant_id": row["variant_id"],
                    "field_path": field_path,
                    "field_value": signal["field_value"],
                    "selected": signal["selected"],
                }
                all_incorrect.append(entry)
                if is_address:
                    address_incorrect.append(entry)

    return {
        "manifest_path": str(manifest_path),
        "documents": documents,
        "residual_audit_field_paths": list(RESIDUAL_AUDIT_FIELD_PATHS),
        "known_residuals": known_residuals,
        "address_correct_distribution": distribution_summary(address_correct),
        "address_incorrect_observations": address_incorrect,
        "all_correct_distribution": distribution_summary(all_correct),
        "all_incorrect_observations": all_incorrect,
        "non_ascii_field_values": non_ascii_field_values(rows),
    }


_KNOWN_RESIDUAL_DOCS = {"symage_900027-irs_w2_single_page_2026-p0", "symage_900061-irs_w2_single_page_2026-p0"}


def _known_residual_table(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    table = []
    for row in rows:
        if row["document_id"] not in _KNOWN_RESIDUAL_DOCS:
            continue
        for field_path in ("employer.address.address_line_1", "employee.address.address_line_1"):
            signal = row["field_signals"].get(field_path)
            if signal is None:
                continue
            table.append(
                {
                    "document_id": row["document_id"],
                    "variant_id": row["variant_id"],
                    "field": field_path,
                    "correct": signal["correct"],
                    "field_value": signal["field_value"],
                    "selected": signal["selected"],
                    "min": signal["min"],
                    "mean": signal["mean"],
                    "selected_reason": signal["selected_reason"],
                }
            )
    return table


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_path", type=Path)
    parser.add_argument("--variant-id", default=None)
    parser.add_argument("--document-id", action="append", default=None, dest="document_ids")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-audit-json", type=Path, default=None)
    parser.add_argument("--output-rows-jsonl", type=Path, default=None)
    parser.add_argument("--output-thresholds-json", type=Path, default=None)
    args = parser.parse_args(argv)

    result = run_audit(
        manifest_path=args.manifest_path,
        variant_id=args.variant_id,
        document_ids=args.document_ids,
        limit=args.limit,
    )

    if args.output_rows_jsonl is not None:
        args.output_rows_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with args.output_rows_jsonl.open("w", encoding="utf-8", newline="\n") as file_obj:
            for row in result["rows"]:
                file_obj.write(json.dumps(row))
                file_obj.write("\n")

    if args.output_audit_json is not None:
        args.output_audit_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_audit_json.write_text(json.dumps(result["audit"], indent=2, sort_keys=True), encoding="utf-8")

    if args.output_thresholds_json is not None:
        args.output_thresholds_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_thresholds_json.write_text(
            json.dumps(result["thresholds"], indent=2, sort_keys=True), encoding="utf-8"
        )

    print(json.dumps(result["audit"], indent=2, sort_keys=True, default=str)[:4000])


if __name__ == "__main__":
    main()
