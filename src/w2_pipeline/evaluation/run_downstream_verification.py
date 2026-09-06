"""Phase 8D.1: verify downstream JSON/CSV output against real production predictions.

Not a new downstream feature -- this script exercises the existing
`w2_pipeline.downstream` package (`validate_w2_document` ->
`finalize_document` -> `export_json`/`export_csv`) against real Phase
8C.11/8C.12 predictions (`phase8c12_checkbox_signals_600_predictions.jsonl`,
which already carries both `employer_name_observation_count` and
`box_13_checkbox_evidence` in `pipeline_metadata`) rather than synthetic
fixtures, and against one of the four known `employer.name` residual
documents to confirm the accepted/needs-review export gate holds on real
data, not just constructed test cases.

Produces:
- `phase8d1_example_w2.json` / `.csv`: one real, accepted, representative
  happy-path document (checked retirement-plan box, populated money
  fields), saved as a durable example of the actual emitted contract.
- `phase8d1_downstream_verification.json`: the full verification report
  this file's checks build up.
"""

from __future__ import annotations

import csv
import io
import json
import time
from pathlib import Path
from typing import Any

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.downstream.csv_output import export_csv
from w2_pipeline.downstream.errors import NotAcceptedError
from w2_pipeline.downstream.finalize import finalize_document
from w2_pipeline.downstream.json_output import export_json
from w2_pipeline.evaluation.predictions import PredictionRecord, load_prediction_records_jsonl
from w2_pipeline.validation.models import ExtractionSignals
from w2_pipeline.validation.validator import validate_w2_document

DEFAULT_PREDICTIONS_PATH = Path("data/evaluation/results/phase8c12_checkbox_signals_600_predictions.jsonl")

_REPEATED_FIELDS = ("box_12_entries", "box_14_entries", "tipped_occupation_codes", "state_local_entries")
_JSON_ONLY_FIELDS = ("field_observations",)

_KNOWN_EMPLOYER_NAME_RESIDUALS = (
    ("symage_900033-irs_w2_single_page_2026-p0", "rotated_png"),
    ("symage_900045-irs_w2_single_page_2026-p0", "rotated_png"),
    ("symage_900082-irs_w2_single_page_2026-p0", "rotated_png"),
    ("symage_900146-irs_w2_single_page_2026-p0", "rotated_png"),
)


def _signals_for_record(record: PredictionRecord) -> ExtractionSignals:
    meta = record.pipeline_metadata or {}
    checkbox = meta.get("box_13_checkbox_evidence") or {}
    return ExtractionSignals(
        pipeline_id=record.pipeline_id,
        route=record.extraction_route,
        employer_name_observation_count=meta.get("employer_name_observation_count"),
        checkbox_evidence_detection_method=checkbox.get("detection_method"),
        checkbox_evidence_fallback_used=checkbox.get("fallback_used"),
        checkbox_evidence_anchor_found=checkbox.get("anchor_found"),
        checkbox_evidence_checkbox_found=checkbox.get("checkbox_found"),
        checkbox_evidence_anchor_distance_px=checkbox.get("anchor_distance_px"),
        checkbox_evidence_horizontal_alignment_offset_px=checkbox.get("horizontal_alignment_offset_px"),
        checkbox_evidence_shape_score=checkbox.get("shape_score"),
        checkbox_evidence_interior_ink_ratio=checkbox.get("interior_ink_ratio"),
        checkbox_evidence_decision_margin=checkbox.get("decision_margin"),
    )


def _flatten(prefix: str, value: Any, out: dict[str, Any]) -> None:
    if isinstance(value, dict):
        for key in sorted(value):
            _flatten(f"{prefix}.{key}" if prefix else key, value[key], out)
        return
    out[prefix] = value


def _normalize_json_leaf_for_csv_comparison(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)  # Python-style "True"/"False", matching csv_output.py's str(bool)
    return str(value)


def _json_csv_consistency_check(finalized_json_payload: dict, csv_row: dict[str, str]) -> dict[str, Any]:
    flat_json: dict[str, Any] = {}
    _flatten("", finalized_json_payload["document"], flat_json)

    mismatches: list[dict[str, Any]] = []
    scalar_keys_compared = 0
    for key, json_value in flat_json.items():
        top_level_field = key.split(".")[0]
        if top_level_field in _REPEATED_FIELDS or top_level_field in _JSON_ONLY_FIELDS:
            continue
        scalar_keys_compared += 1
        csv_value = csv_row.get(key)
        if csv_value is None:
            mismatches.append({"field": key, "issue": "missing_from_csv", "json_value": json_value})
            continue
        normalized_json = _normalize_json_leaf_for_csv_comparison(json_value)
        if normalized_json != csv_value:
            mismatches.append(
                {"field": key, "issue": "value_mismatch", "json_value": normalized_json, "csv_value": csv_value}
            )

    repeated_structure_checks = {}
    for field in _REPEATED_FIELDS:
        json_value = finalized_json_payload["document"].get(field, [])
        csv_value = json.loads(csv_row[field]) if field in csv_row else None
        repeated_structure_checks[field] = {
            "matches": json_value == csv_value,
            "json_value": json_value,
            "csv_value": csv_value,
        }

    return {
        "scalar_keys_compared": scalar_keys_compared,
        "scalar_mismatches": mismatches,
        "repeated_structure_checks": repeated_structure_checks,
        "field_observations_json_only": (
            "field_observations" in finalized_json_payload["document"] and "field_observations" not in csv_row
        ),
    }


def run_verification(predictions_path: str | Path = DEFAULT_PREDICTIONS_PATH) -> dict[str, Any]:
    records = load_prediction_records_jsonl(predictions_path)
    by_key = {(record.document_id, record.variant_id): record for record in records}

    report: dict[str, Any] = {"source_predictions_jsonl": str(predictions_path)}

    # --- 1. Real happy-path example: first accepted, checked document ---
    example_record = None
    example_finalized = None
    for record in records:
        if record.document is None or not record.document.box_13.retirement_plan:
            continue
        result = validate_w2_document(record.document, signals=_signals_for_record(record))
        if result.status.value == "accepted":
            example_record = record
            example_finalized = finalize_document(record.document, result)
            break
    assert example_record is not None and example_finalized is not None, (
        "Expected at least one accepted, checked-retirement-plan document in the real predictions."
    )

    example_json_text = export_json(example_finalized)
    example_csv_text = export_csv(example_finalized)
    example_json_payload = json.loads(example_json_text)
    example_csv_row = next(csv.DictReader(io.StringIO(example_csv_text)))

    report["example_document"] = {
        "document_id": example_record.document_id,
        "variant_id": example_record.variant_id,
        "retirement_plan": True,
    }

    # --- 2. Determinism ---
    report["determinism"] = {
        "json_byte_identical_on_repeat": export_json(example_finalized) == example_json_text,
        "csv_byte_identical_on_repeat": export_csv(example_finalized) == example_csv_text,
    }

    # --- 3. JSON/CSV consistency ---
    report["json_csv_consistency"] = _json_csv_consistency_check(example_json_payload, example_csv_row)

    # --- 4. Money format check (exact string, no float artifacts) ---
    money_field = example_json_payload["document"]["federal_wages_and_taxes"]["box_1_wages_tips_other_compensation"]
    report["money_format"] = {
        "json_value": money_field,
        "json_type": type(money_field).__name__,
        "csv_value": example_csv_row["federal_wages_and_taxes.box_1_wages_tips_other_compensation"],
        "matches": str(money_field) == example_csv_row["federal_wages_and_taxes.box_1_wages_tips_other_compensation"],
    }

    # --- 5. Boolean representation ---
    report["boolean_representation"] = {
        "json_retirement_plan": example_json_payload["document"]["box_13"]["retirement_plan"],
        "json_type": type(example_json_payload["document"]["box_13"]["retirement_plan"]).__name__,
        "csv_retirement_plan": example_csv_row["box_13.retirement_plan"],
    }

    # --- 6. SSN/EIN leading-zero preservation (constructed, since real
    #     dataset SSNs/EINs may not happen to start with 0) ---
    leading_zero_document = example_record.document.model_copy(
        update={"employee": example_record.document.employee.model_copy(update={"ssn": "012-34-5678"})}
    )
    leading_zero_result = validate_w2_document(leading_zero_document, signals=_signals_for_record(example_record))
    leading_zero_finalized = finalize_document(leading_zero_document, leading_zero_result)
    leading_zero_json = json.loads(export_json(leading_zero_finalized))
    leading_zero_row = next(csv.DictReader(io.StringIO(export_csv(leading_zero_finalized))))
    report["ssn_leading_zero_preservation"] = {
        "json_value": leading_zero_json["document"]["employee"]["ssn"],
        "csv_value": leading_zero_row["employee.ssn"],
        "preserved_in_both": (
            leading_zero_json["document"]["employee"]["ssn"] == "012-34-5678"
            and leading_zero_row["employee.ssn"] == "012-34-5678"
        ),
    }

    # --- 7. CSV escaping (constructed: real dataset employer names don't
    #     happen to contain commas/quotes) ---
    tricky_name = 'Smith, "Jones" & O\'Brien Corp'
    tricky_document = example_record.document.model_copy(
        update={"employer": example_record.document.employer.model_copy(update={"name": tricky_name})}
    )
    tricky_finalized = finalize_document(
        tricky_document, validate_w2_document(tricky_document, signals=_signals_for_record(example_record))
    )
    tricky_row = next(csv.DictReader(io.StringIO(export_csv(tricky_finalized))))
    report["csv_escaping"] = {
        "input": tricky_name,
        "round_tripped_value": tricky_row["employer.name"],
        "matches": tricky_row["employer.name"] == tricky_name,
    }

    # --- 8. Gating: real needs_review residual document blocked ---
    residual_key = _KNOWN_EMPLOYER_NAME_RESIDUALS[0]
    residual_record = by_key[residual_key]
    residual_result = validate_w2_document(residual_record.document, signals=_signals_for_record(residual_record))
    residual_blocked = False
    residual_error_message = None
    try:
        finalize_document(residual_record.document, residual_result)
    except NotAcceptedError as exc:
        residual_blocked = True
        residual_error_message = str(exc)
    report["gating"] = {
        "residual_document": {"document_id": residual_key[0], "variant_id": residual_key[1]},
        "validation_status": residual_result.status.value,
        "validation_issue_codes": [issue.code for issue in residual_result.issues],
        "export_blocked": residual_blocked,
        "error_message": residual_error_message,
    }

    # --- 9. Batch composition sanity: 3 real documents exported
    #     individually, headers identical, no cross-contamination ---
    batch_records = [
        record
        for record in records[:50]
        if record.document is not None
        and validate_w2_document(record.document, signals=_signals_for_record(record)).status.value == "accepted"
    ][:3]
    batch_rows = []
    batch_headers = []
    for record in batch_records:
        finalized = finalize_document(record.document, validate_w2_document(record.document, signals=_signals_for_record(record)))
        text = export_csv(finalized)
        batch_headers.append(text.splitlines()[0])
        batch_rows.append(next(csv.DictReader(io.StringIO(text))))
    report["batch_composition"] = {
        "documents": len(batch_records),
        "headers_identical_across_documents": len(set(batch_headers)) == 1,
        "distinct_document_ids": len({row["metadata.document_id"] for row in batch_rows}) == len(batch_rows),
        "note": (
            "No batch export function exists (export_json/export_csv each take exactly one "
            "FinalizedW2); this checks that calling the single-document primitive repeatedly "
            "produces consistent, non-contaminating output, not a new batch feature."
        ),
    }

    # --- 10. Performance ---
    accepted_finalized = []
    for record in records:
        if record.document is None:
            continue
        result = validate_w2_document(record.document, signals=_signals_for_record(record))
        if result.status.value == "accepted":
            accepted_finalized.append(finalize_document(record.document, result))

    started = time.perf_counter()
    for finalized in accepted_finalized:
        export_json(finalized)
    json_total = time.perf_counter() - started

    started = time.perf_counter()
    for finalized in accepted_finalized:
        export_csv(finalized)
    csv_total = time.perf_counter() - started

    report["performance"] = {
        "documents": len(accepted_finalized),
        "json_total_seconds": json_total,
        "json_mean_microseconds_per_doc": (json_total / len(accepted_finalized)) * 1e6,
        "csv_total_seconds": csv_total,
        "csv_mean_microseconds_per_doc": (csv_total / len(accepted_finalized)) * 1e6,
    }

    return report, example_json_text, example_csv_text


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions-jsonl", type=Path, default=DEFAULT_PREDICTIONS_PATH)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--example-json-path", type=Path, default=None)
    parser.add_argument("--example-csv-path", type=Path, default=None)
    args = parser.parse_args(argv)

    report, example_json_text, example_csv_text = run_verification(args.predictions_jsonl)

    text = json.dumps(report, indent=2, sort_keys=True, default=str)
    print(text)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text, encoding="utf-8")
    if args.example_json_path is not None:
        args.example_json_path.parent.mkdir(parents=True, exist_ok=True)
        args.example_json_path.write_text(example_json_text, encoding="utf-8")
    if args.example_csv_path is not None:
        args.example_csv_path.parent.mkdir(parents=True, exist_ok=True)
        args.example_csv_path.write_text(example_csv_text, encoding="utf-8")


if __name__ == "__main__":
    main()
