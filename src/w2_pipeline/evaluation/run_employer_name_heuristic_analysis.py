"""Phase 8C.5: evaluate address-leak heuristics against frozen Phase 8C.2 predictions.

Offline validation experiment, not a production change. Reuses the
already-frozen Phase 8C.2 prediction artifact directly -- no OCR rerun,
no parser change, no modification to any prior Phase 8 artifact.

## Leakage boundary

For each of the 600 saved predictions: the heuristic is evaluated against
`record.document.employer.name` alone (flagged / not flagged). Only
*after* that decision is made is ground truth (loaded from the manifest's
`ground_truth_path`) consulted, purely to label whether the prediction was
actually correct -- exactly the same ordering
`validator_effectiveness_predictions.py` uses for the production
validator.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.employer_name_heuristics import CANDIDATE_RULES
from w2_pipeline.evaluation.manifest import load_manifest_jsonl
from w2_pipeline.evaluation.predictions import load_prediction_records_jsonl


def run_employer_name_heuristic_analysis(
    *,
    predictions_path: str | Path,
    manifest_path: str | Path,
) -> dict[str, Any]:
    records = load_prediction_records_jsonl(predictions_path)
    manifest = load_manifest_jsonl(manifest_path)
    base_dir = Path(manifest_path).parent
    entries_by_key = {(entry.sample_id, entry.variant_id): entry for entry in manifest.entries}

    ground_truth_cache: dict[str, W2Document] = {}
    rows: list[dict[str, Any]] = []

    for record in records:
        entry = entries_by_key.get((record.document_id, record.variant_id))
        if entry is None:
            raise ValueError(f"No manifest entry for {(record.document_id, record.variant_id)!r}.")

        predicted_name = record.document.employer.name if record.document is not None else None

        # LEAKAGE BOUNDARY: every candidate rule sees only the predicted name.
        flags = (
            {rule_name: bool(rule_fn(predicted_name)) for rule_name, rule_fn in CANDIDATE_RULES.items()}
            if predicted_name is not None
            else dict.fromkeys(CANDIDATE_RULES, False)
        )

        if entry.ground_truth_path not in ground_truth_cache:
            ground_truth_cache[entry.ground_truth_path] = W2Document.model_validate_json(
                (base_dir / entry.ground_truth_path).read_text(encoding="utf-8")
            )
        ground_truth_name = ground_truth_cache[entry.ground_truth_path].employer.name

        is_correct = (
            predicted_name is not None
            and ground_truth_name is not None
            and predicted_name.strip() == ground_truth_name.strip()
        )

        rows.append(
            {
                "document_id": record.document_id,
                "variant_id": record.variant_id,
                "predicted_name": predicted_name,
                "ground_truth_name": ground_truth_name,
                "correct": is_correct,
                "flags": flags,
            }
        )

    return {
        "source_predictions_jsonl": str(predictions_path),
        "source_manifest": str(manifest_path),
        "leakage_boundary": (
            "each candidate rule is evaluated against record.document.employer.name "
            "alone; ground truth is loaded and compared only afterward, to label "
            "correctness, never to influence the flag."
        ),
        "total_documents": len(rows),
        "correct_documents": sum(1 for row in rows if row["correct"]),
        "erroneous_documents": sum(1 for row in rows if not row["correct"]),
        "candidate_rules": {name: _confusion(rows, name) for name in CANDIDATE_RULES},
        "rows": rows,
    }


def _confusion(rows: list[dict[str, Any]], rule_name: str) -> dict[str, Any]:
    true_positive = [r for r in rows if not r["correct"] and r["flags"][rule_name]]
    false_negative = [r for r in rows if not r["correct"] and not r["flags"][rule_name]]
    false_positive = [r for r in rows if r["correct"] and r["flags"][rule_name]]
    true_negative = [r for r in rows if r["correct"] and not r["flags"][rule_name]]

    erroneous_total = len(true_positive) + len(false_negative)
    correct_total = len(false_positive) + len(true_negative)
    flagged_total = len(true_positive) + len(false_positive)

    return {
        "true_positives": len(true_positive),
        "false_negatives": len(false_negative),
        "false_positives": len(false_positive),
        "true_negatives": len(true_negative),
        "recall": _ratio(len(true_positive), erroneous_total),
        "precision": _ratio(len(true_positive), flagged_total),
        "false_review_rate": _ratio(len(false_positive), correct_total),
        "specificity": _ratio(len(true_negative), correct_total),
        "false_positive_document_ids": sorted(
            f"{r['document_id']}::{r['variant_id']}" for r in false_positive
        ),
        "false_negative_document_ids": sorted(
            f"{r['document_id']}::{r['variant_id']}" for r in false_negative
        ),
    }


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions_jsonl_path", type=Path)
    parser.add_argument("manifest_path", type=Path)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-rows-jsonl", type=Path, default=None)
    parser.add_argument("--no-rows", action="store_true")
    args = parser.parse_args(argv)

    report = run_employer_name_heuristic_analysis(
        predictions_path=args.predictions_jsonl_path, manifest_path=args.manifest_path
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
