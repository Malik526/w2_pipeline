"""Phase 8C.3: measure validator effectiveness against complete, real predictions.

`validator_effectiveness.py` (Phase 8) had to *reconstruct* a predicted
`W2Document` from ground truth plus a benchmark's recorded field failures,
because no historical Pipeline A/B run ever persisted the complete
predicted document -- only aggregate field-level failures. That
reconstruction is unnecessary here: Phase 8A's `--save-predictions`
final-run artifacts (e.g.
`data/evaluation/results/phase8c2_final_paddleocr_gpu_all_variants_600_predictions.jsonl`)
already contain the complete, real, ground-truth-free `PredictionRecord`
for every document -- the actual `W2Document` the pipeline produced. This
module consumes those directly.

This also means the reconstruction module's `employer.name` ground-truth
adjustment (`KNOWN_GROUND_TRUTH_GAPS`) does not apply and is not used
here: that adjustment existed only because the Symage ground truth had
`employer.name = null` for every record before Phase 8A added an
authoritative FUNSD-derived mapping. Ground truth loaded by this module
always has a real `employer.name`, so no adjustment is needed -- this is
the first validator-effectiveness analysis run against fully-covered
ground truth, and is intended as the authoritative one.

## Leakage boundary

For every saved `PredictionRecord`:

    record.document (the ACTUAL, complete prediction)
        -> validate_w2_document()      <- ground truth never passed in here
        -> accepted / needs_review
        -> THEN, and only then, ground truth (loaded from the manifest's
           own `ground_truth_path`, scored with the same
           `evaluated_field_paths` and `compare_w2_documents` the original
           benchmark run used) is consulted to label whether the document
           was actually correct or erroneous.

`ExtractionSignals` passed to the validator carries only what a real
caller would have at inference time (`pipeline_id`, `extraction_route`,
and an outcome derived from the record's own `status`) -- never
`variant_id`/`document_condition`, which is dataset metadata identifying
which synthetic degradation was applied and would not exist for a real
incoming document. `tests/evaluation/test_validator_effectiveness_predictions.py`
enforces the ordering with a call-spy, the same technique
`test_validator_effectiveness.py` uses.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.comparison import compare_w2_documents
from w2_pipeline.evaluation.manifest import load_manifest_jsonl
from w2_pipeline.evaluation.predictions import PredictionRecord, load_prediction_records_jsonl
from w2_pipeline.validation.models import ExtractionOutcome, ExtractionSignals, ValidationStatus
from w2_pipeline.validation.routing import RoutingPolicy
from w2_pipeline.validation.validator import validate_w2_document


def _signals_for_record(record: PredictionRecord) -> ExtractionSignals:
    """Build the `ExtractionSignals` a real caller would have at inference
    time -- derived only from the record's own extraction outcome, never
    from dataset/benchmark metadata such as `variant_id`."""

    if record.status == "success":
        # A "success" status with no document is an inconsistent state
        # (the pipeline reported success but produced nothing usable),
        # distinct from a reported extraction failure.
        outcome = ExtractionOutcome.SUCCEEDED if record.document is not None else ExtractionOutcome.INVALID_CANONICAL_RESULT
    elif record.status == "extraction_failed":
        outcome = ExtractionOutcome.EXTRACTION_FAILED
    else:
        outcome = ExtractionOutcome.INVALID_CANONICAL_RESULT
    return ExtractionSignals(
        pipeline_id=record.pipeline_id,
        route=record.extraction_route,
        outcome=outcome,
    )


def _document_key(record: PredictionRecord) -> tuple[str, str]:
    return (record.document_id, record.variant_id)


def measure_validator_effectiveness_from_predictions(
    *,
    predictions_path: str | Path,
    manifest_path: str | Path,
    policy: RoutingPolicy | None = None,
) -> dict[str, Any]:
    """Score the current production validator against real saved predictions.

    `predictions_path` is a `PredictionRecord` JSONL file written by
    `--save-predictions` (a complete predicted `W2Document` per row, no
    ground truth). `manifest_path` is the manifest that produced the
    underlying benchmark run -- used only to look up each document's
    `ground_truth_path` and `evaluated_field_paths`, both consulted only
    *after* the validator call.
    """

    records = load_prediction_records_jsonl(predictions_path)
    manifest = load_manifest_jsonl(manifest_path)
    base_dir = Path(manifest_path).parent
    entries_by_key = {(entry.sample_id, entry.variant_id): entry for entry in manifest.entries}

    ground_truth_cache: dict[str, W2Document] = {}
    rows: list[dict[str, Any]] = []

    for record in records:
        key = _document_key(record)
        entry = entries_by_key.get(key)
        if entry is None:
            raise ValueError(f"No manifest entry found for prediction key {key!r}.")

        # LEAKAGE BOUNDARY: the validator sees only the real prediction and
        # signals a real caller would have. No ground truth is in scope here.
        signals = _signals_for_record(record)
        validation_result = validate_w2_document(record.document, signals=signals, policy=policy)

        # Ground truth is consulted from this point on, purely to score
        # whether the document was actually correct -- never fed back into
        # extraction, validation, or routing.
        if entry.ground_truth_path not in ground_truth_cache:
            ground_truth_cache[entry.ground_truth_path] = W2Document.model_validate_json(
                (base_dir / entry.ground_truth_path).read_text(encoding="utf-8")
            )
        ground_truth = ground_truth_cache[entry.ground_truth_path]

        if record.document is None:
            has_error = True
            failing_field_paths: list[str] = []
        else:
            evaluation = compare_w2_documents(
                expected=ground_truth,
                predicted=record.document,
                sample_id=record.document_id,
                variant_id=record.variant_id,
                pipeline_id=record.pipeline_id,
                evaluated_field_paths=entry.evaluated_field_paths,
            )
            has_error = evaluation.correct_fields < evaluation.total_fields
            failing_field_paths = [failure.field_path for failure in evaluation.failures if failure.field_path]

        rows.append(
            {
                "document_id": record.document_id,
                "variant_id": record.variant_id,
                "has_error": has_error,
                "failing_field_paths": failing_field_paths,
                "validation_status": validation_result.status.value,
                "validation_issues": [
                    {"code": issue.code, "severity": issue.severity.value, "field_path": issue.field_path}
                    for issue in validation_result.issues
                ],
            }
        )

    return _build_report(rows, predictions_path=predictions_path, manifest_path=manifest_path)


def _build_report(
    rows: list[dict[str, Any]],
    *,
    predictions_path: str | Path,
    manifest_path: str | Path,
) -> dict[str, Any]:
    variant_ids = sorted({row["variant_id"] for row in rows})
    all_field_paths = sorted({path for row in rows for path in row["failing_field_paths"]})

    box13_key = "box_13.retirement_plan"
    employer_name_key = "employer.name"
    box13_docs = {
        (row["document_id"], row["variant_id"]) for row in rows if box13_key in row["failing_field_paths"]
    }
    employer_name_docs = {
        (row["document_id"], row["variant_id"])
        for row in rows
        if employer_name_key in row["failing_field_paths"]
    }

    return {
        "method": "complete_saved_predictions_no_reconstruction",
        "source_predictions_jsonl": str(predictions_path),
        "source_manifest": str(manifest_path),
        "leakage_boundary": (
            "validate_w2_document() called with only record.document and "
            "signals derived from record.status/pipeline_id/extraction_route; "
            "ground truth loaded and compared only after that call returns."
        ),
        "total_field_failures": sum(len(row["failing_field_paths"]) for row in rows),
        "distinct_failing_field_paths_observed": all_field_paths,
        "overall": _summarize(rows),
        "by_variant": {variant_id: _summarize([r for r in rows if r["variant_id"] == variant_id]) for variant_id in variant_ids},
        "error_classes": {
            box13_key: _error_class_report(rows, box13_key),
            employer_name_key: _error_class_report(rows, employer_name_key),
            "overlap_between_classes": {
                "documents_with_both_failures": sorted(f"{doc}::{variant}" for doc, variant in (box13_docs & employer_name_docs)),
                "count": len(box13_docs & employer_name_docs),
            },
        },
        "validator_issue_taxonomy": _issue_taxonomy(rows),
        "rows": rows,
    }


def _is_needs_review(row: dict[str, Any]) -> bool:
    return row["validation_status"] == ValidationStatus.NEEDS_REVIEW.value


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
        "error_detection_recall": _ratio(len(erroneous_reviewed), len(erroneous)),
        "false_review_rate": _ratio(len(correct_reviewed), len(correct)),
        "automatic_acceptance_rate": _ratio(len(accepted), total),
        "unsafe_acceptance_rate": _ratio(len(erroneous_accepted), total),
        "review_queue_precision": _ratio(len(erroneous_reviewed), len(needs_review)),
    }


def _error_class_report(rows: list[dict[str, Any]], field_path: str) -> dict[str, Any]:
    affected = [row for row in rows if field_path in row["failing_field_paths"]]
    routed_review = [row for row in affected if row["validation_status"] == ValidationStatus.NEEDS_REVIEW.value]
    accepted = [row for row in affected if row["validation_status"] == ValidationStatus.ACCEPTED.value]
    return {
        "field_path": field_path,
        "affected_documents": len(affected),
        "routed_needs_review": len(routed_review),
        "accepted": len(accepted),
        "catch_rate": _ratio(len(routed_review), len(affected)),
        "affected_document_ids": sorted(f"{row['document_id']}::{row['variant_id']}" for row in affected),
    }


def _issue_taxonomy(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tally, for documents routed `needs_review`, which issue code(s) fired
    and whether that document was actually correct or erroneous -- one
    count per (document, issue code) pair, so a document with the same
    code twice (impossible today, but not assumed) is not double-counted."""

    buckets: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row["validation_status"] != ValidationStatus.NEEDS_REVIEW.value:
            continue
        seen_codes: set[str] = set()
        for issue in row["validation_issues"]:
            code = issue["code"]
            if code in seen_codes:
                continue
            seen_codes.add(code)
            bucket = buckets.setdefault(
                code,
                {
                    "issue_code": code,
                    "severity": issue["severity"],
                    "document_count": 0,
                    "correct_document_count": 0,
                    "erroneous_document_count": 0,
                },
            )
            bucket["document_count"] += 1
            if row["has_error"]:
                bucket["erroneous_document_count"] += 1
            else:
                bucket["correct_document_count"] += 1

    return sorted(buckets.values(), key=lambda bucket: (-bucket["document_count"], bucket["issue_code"]))


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions_jsonl_path", type=Path)
    parser.add_argument("manifest_path", type=Path)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-rows-jsonl", type=Path, default=None)
    parser.add_argument(
        "--no-rows",
        action="store_true",
        help="Omit the per-document row detail from the printed/saved summary JSON.",
    )
    args = parser.parse_args(argv)

    report = measure_validator_effectiveness_from_predictions(
        predictions_path=args.predictions_jsonl_path,
        manifest_path=args.manifest_path,
    )

    rows = report["rows"]
    if args.output_rows_jsonl is not None:
        args.output_rows_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with args.output_rows_jsonl.open("w", encoding="utf-8", newline="\n") as file_obj:
            for row in rows:
                file_obj.write(json.dumps(row))
                file_obj.write("\n")

    if args.no_rows:
        report = {key: value for key, value in report.items() if key != "rows"}

    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
