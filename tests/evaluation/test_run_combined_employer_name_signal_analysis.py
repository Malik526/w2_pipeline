import json
from pathlib import Path

import pytest

from w2_pipeline.evaluation.run_combined_employer_name_signal_analysis import (
    build_signal_rows,
    run_combined_analysis,
)


def _address_row(doc_id: str, variant: str, *, flag: bool, correct: bool) -> dict:
    return {
        "document_id": doc_id,
        "variant_id": variant,
        "predicted_name": "irrelevant",
        "ground_truth_name": "irrelevant",
        "correct": correct,
        "flags": {"C_expanded_number_and_suffix": flag, "A_contains_street_number": flag},
    }


def _layout_row(doc_id: str, variant: str, *, observation_count: int, correct: bool) -> dict:
    return {
        "document_id": doc_id,
        "variant_id": variant,
        "status": "success",
        "predicted_name": "irrelevant",
        "correct": correct,
        "signals": {"matched": True, "observation_count": observation_count},
    }


def test_build_signal_rows_joins_by_document_and_variant() -> None:
    address_rows = [_address_row("d1", "rotated_png", flag=True, correct=False)]
    layout_rows = [_layout_row("d1", "rotated_png", observation_count=2, correct=False)]

    rows = build_signal_rows(address_rows, layout_rows)

    assert len(rows) == 1
    assert rows[0].address_signal is True
    assert rows[0].layout_signal is True
    assert rows[0].correct is False


def test_build_signal_rows_rejects_mismatched_document_sets() -> None:
    address_rows = [_address_row("d1", "rotated_png", flag=True, correct=False)]
    layout_rows = [_layout_row("d2", "rotated_png", observation_count=2, correct=False)]

    with pytest.raises(ValueError, match="do not describe the same document set"):
        build_signal_rows(address_rows, layout_rows)


def test_build_signal_rows_rejects_correctness_disagreement() -> None:
    address_rows = [_address_row("d1", "rotated_png", flag=True, correct=True)]
    layout_rows = [_layout_row("d1", "rotated_png", observation_count=2, correct=False)]

    with pytest.raises(ValueError, match="Correctness disagreement"):
        build_signal_rows(address_rows, layout_rows)


def test_run_combined_analysis_end_to_end(tmp_path: Path) -> None:
    address_path = tmp_path / "address.jsonl"
    layout_path = tmp_path / "layout.jsonl"

    address_rows = [
        _address_row("both", "rotated_png", flag=True, correct=False),
        _address_row("addr-only", "rotated_png", flag=True, correct=True),
        _address_row("clean", "rotated_png", flag=False, correct=True),
    ]
    layout_rows = [
        _layout_row("both", "rotated_png", observation_count=2, correct=False),
        _layout_row("addr-only", "rotated_png", observation_count=1, correct=True),
        _layout_row("clean", "rotated_png", observation_count=1, correct=True),
    ]
    address_path.write_text("\n".join(json.dumps(r) for r in address_rows), encoding="utf-8")
    layout_path.write_text("\n".join(json.dumps(r) for r in layout_rows), encoding="utf-8")

    report = run_combined_analysis(address_leak_rows_path=address_path, layout_span_rows_path=layout_path)

    assert report["total_documents"] == 3
    assert report["agreement_state_counts"] == {"both": 1, "address_only": 1, "layout_only": 0, "neither": 1}
    assert len(report["disagreements"]) == 1
    assert report["disagreements"][0]["document_id"] == "addr-only"
    assert report["confusion_matrices"]["or_combined"]["false_positives"] == 1
    assert report["confusion_matrices"]["and_combined"]["false_positives"] == 0


def test_run_combined_analysis_reports_no_disagreements_when_there_are_none(tmp_path: Path) -> None:
    address_path = tmp_path / "address.jsonl"
    layout_path = tmp_path / "layout.jsonl"

    address_rows = [_address_row("both", "rotated_png", flag=True, correct=False)]
    layout_rows = [_layout_row("both", "rotated_png", observation_count=2, correct=False)]
    address_path.write_text(json.dumps(address_rows[0]), encoding="utf-8")
    layout_path.write_text(json.dumps(layout_rows[0]), encoding="utf-8")

    report = run_combined_analysis(address_leak_rows_path=address_path, layout_span_rows_path=layout_path)

    assert report["disagreements"] == []
