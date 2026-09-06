"""Phase 8C.7: join the frozen Phase 8C.5/8C.6 row artifacts and score combinations.

Deliberately does NOT rerun OCR or recompute either underlying signal --
this phase is pure combination-logic evaluation over two already-computed,
already-verified per-document signal artifacts:

    data/evaluation/results/phase8c5_employer_name_address_leak_rows.jsonl
    data/evaluation/results/phase8c6_employer_name_layout_span_rows.jsonl

Both were produced against the identical frozen Phase 8C.2 600-document
prediction set, and their `(document_id, variant_id)` key sets and
`correct` labels are cross-checked for exact agreement before any
combination logic runs -- a real mismatch there would mean the two
artifacts do not describe the same predictions, which must stop the
analysis rather than silently proceed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from w2_pipeline.evaluation.combined_employer_name_signals import (
    AgreementState,
    SignalRow,
    agreement_state_counts,
    classify_agreement,
    confusion_matrix,
)

ADDRESS_SIGNAL_KEY = "C_expanded_number_and_suffix"  # Phase 8C.5's best candidate.


def _load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    with Path(path).open("r", encoding="utf-8") as file_obj:
        for line in file_obj:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def build_signal_rows(
    address_leak_rows: list[dict[str, Any]], layout_span_rows: list[dict[str, Any]]
) -> list[SignalRow]:
    address_by_key = {(row["document_id"], row["variant_id"]): row for row in address_leak_rows}
    layout_by_key = {(row["document_id"], row["variant_id"]): row for row in layout_span_rows}

    if address_by_key.keys() != layout_by_key.keys():
        raise ValueError(
            "Phase 8C.5 and Phase 8C.6 row artifacts do not describe the same document set; "
            "refusing to combine signals over mismatched inputs."
        )

    rows: list[SignalRow] = []
    for key, address_row in address_by_key.items():
        layout_row = layout_by_key[key]
        if address_row["correct"] != layout_row["correct"]:
            raise ValueError(
                f"Correctness disagreement between Phase 8C.5 and 8C.6 artifacts for {key!r}; "
                "they should describe the identical frozen predictions."
            )
        document_id, variant_id = key
        rows.append(
            SignalRow(
                document_id=document_id,
                variant_id=variant_id,
                address_signal=bool(address_row["flags"][ADDRESS_SIGNAL_KEY]),
                layout_signal=bool(layout_row["signals"]["observation_count"] and layout_row["signals"]["observation_count"] > 1),
                correct=bool(address_row["correct"]),
            )
        )
    return rows


def run_combined_analysis(
    *,
    address_leak_rows_path: str | Path,
    layout_span_rows_path: str | Path,
) -> dict[str, Any]:
    address_leak_rows = _load_jsonl(address_leak_rows_path)
    layout_span_rows = _load_jsonl(layout_span_rows_path)
    signal_rows = build_signal_rows(address_leak_rows, layout_span_rows)

    disagreements = [
        row
        for row in signal_rows
        if classify_agreement(row.address_signal, row.layout_signal)
        in (AgreementState.ADDRESS_ONLY, AgreementState.LAYOUT_ONLY)
    ]

    return {
        "source_address_leak_rows": str(address_leak_rows_path),
        "source_layout_span_rows": str(layout_span_rows_path),
        "address_signal_definition": ADDRESS_SIGNAL_KEY,
        "layout_signal_definition": "observation_count > 1",
        "total_documents": len(signal_rows),
        "correct_documents": sum(1 for row in signal_rows if row.correct),
        "erroneous_documents": sum(1 for row in signal_rows if not row.correct),
        "agreement_state_counts": agreement_state_counts(signal_rows),
        "known_failures_agreement": [
            {
                "document_id": row.document_id,
                "variant_id": row.variant_id,
                "address_signal": row.address_signal,
                "layout_signal": row.layout_signal,
                "agreement_state": classify_agreement(row.address_signal, row.layout_signal).value,
            }
            for row in signal_rows
            if not row.correct
        ],
        "disagreements": [
            {
                "document_id": row.document_id,
                "variant_id": row.variant_id,
                "address_signal": row.address_signal,
                "layout_signal": row.layout_signal,
                "correct": row.correct,
                "agreement_state": classify_agreement(row.address_signal, row.layout_signal).value,
            }
            for row in disagreements
        ],
        "confusion_matrices": {
            "address_alone": confusion_matrix(signal_rows, flag_key="address"),
            "layout_alone": confusion_matrix(signal_rows, flag_key="layout"),
            "or_combined": confusion_matrix(signal_rows, flag_key="or"),
            "and_combined": confusion_matrix(signal_rows, flag_key="and"),
        },
        "rows": [
            {
                "document_id": row.document_id,
                "variant_id": row.variant_id,
                "address_signal": row.address_signal,
                "layout_signal": row.layout_signal,
                "agreement_state": classify_agreement(row.address_signal, row.layout_signal).value,
                "correct": row.correct,
            }
            for row in signal_rows
        ],
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("address_leak_rows_path", type=Path)
    parser.add_argument("layout_span_rows_path", type=Path)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-rows-jsonl", type=Path, default=None)
    parser.add_argument("--no-rows", action="store_true")
    args = parser.parse_args(argv)

    report = run_combined_analysis(
        address_leak_rows_path=args.address_leak_rows_path,
        layout_span_rows_path=args.layout_span_rows_path,
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
