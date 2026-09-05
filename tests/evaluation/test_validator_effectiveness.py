import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.dataset import generate_evaluation_dataset
from w2_pipeline.evaluation.manifest import load_manifest_jsonl
from w2_pipeline.evaluation.validator_effectiveness import (
    measure_validator_effectiveness,
    reconstruct_predicted_document,
)


def _write_result_json(
    path: Path,
    *,
    variant_scope: list[str],
    field_failures: list[dict],
) -> None:
    payload = {
        "benchmark_metadata": {"variant_scope": variant_scope},
        "field_failures": field_failures,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_reconstruct_predicted_document_applies_only_recorded_failures() -> None:
    from w2_pipeline.evaluation.synthetic import generate_synthetic_w2_documents

    ground_truth = generate_synthetic_w2_documents()[0]
    failures = [
        {
            "field_path": "employee.ssn",
            "expected": ground_truth.employee.ssn,
            "predicted": None,
            "failure_kind": "missing",
        }
    ]

    predicted, skipped = reconstruct_predicted_document(ground_truth, failures)

    assert predicted.employee.ssn is None
    assert skipped == []
    # Every other field is untouched, exactly equal to ground truth.
    assert predicted.employee.first_name == ground_truth.employee.first_name
    assert predicted.employer.ein == ground_truth.employer.ein


def test_reconstruct_predicted_document_skips_unexpected_failures() -> None:
    from w2_pipeline.evaluation.synthetic import generate_synthetic_w2_documents

    ground_truth = generate_synthetic_w2_documents()[0]
    failures = [{"field_path": "box_12_entries[5].code", "failure_kind": "unexpected", "predicted": "X"}]

    predicted, skipped = reconstruct_predicted_document(ground_truth, failures)

    assert predicted == ground_truth
    assert skipped == ["box_12_entries[5].code"]


def test_measure_validator_effectiveness_end_to_end(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    generate_evaluation_dataset(dataset_dir, sample_count=3, seed=2026)
    manifest = load_manifest_jsonl(dataset_dir / "manifest.jsonl")
    clean_entries = [e for e in manifest.entries if e.variant_id == "clean_pdf"]
    assert len(clean_entries) == 3

    ground_truths = {
        entry.sample_id: W2Document.model_validate_json(
            (dataset_dir / entry.ground_truth_path).read_text(encoding="utf-8")
        )
        for entry in clean_entries
    }
    sample_ids = list(ground_truths)

    # Document 1: a detectable error (missing SSN -> required_field_missing).
    detectable_doc = sample_ids[0]
    # Document 2: an undetectable error (a plausible-but-wrong money value,
    # still non-negative with 2 decimal places -- passes every format rule).
    undetectable_doc = sample_ids[1]
    plausible_wrong_wages = (
        ground_truths[undetectable_doc].federal_wages_and_taxes.box_1_wages_tips_other_compensation
        + Decimal("100.00")
    )
    # Document 3: no recorded failures at all (fully correct).

    result_path = tmp_path / "result.json"
    _write_result_json(
        result_path,
        variant_scope=["clean_pdf"],
        field_failures=[
            {
                "document_id": detectable_doc,
                "variant_id": "clean_pdf",
                "field_path": "employee.ssn",
                "expected": ground_truths[detectable_doc].employee.ssn,
                "predicted": None,
                "failure_kind": "missing",
            },
            {
                "document_id": undetectable_doc,
                "variant_id": "clean_pdf",
                "field_path": "federal_wages_and_taxes.box_1_wages_tips_other_compensation",
                "expected": str(
                    ground_truths[undetectable_doc]
                    .federal_wages_and_taxes.box_1_wages_tips_other_compensation
                ),
                "predicted": str(plausible_wrong_wages),
                "failure_kind": "mismatch",
            },
        ],
    )

    summary = measure_validator_effectiveness(
        result_json_path=result_path,
        manifest_path=dataset_dir / "manifest.jsonl",
    )

    assert summary["raw"]["total_documents"] == 3
    assert summary["raw"]["erroneous_documents"] == 2
    assert summary["raw"]["correct_documents"] == 1
    # The missing-SSN document is a detectable error: caught.
    # The plausible-wrong-money document is undetectable: missed.
    assert summary["raw"]["erroneous_caught_needs_review"] == 1
    assert summary["raw"]["erroneous_missed_accepted"] == 1
    assert summary["raw"]["missed_erroneous_document_ids"] == [undetectable_doc]
    # The one fully-correct document is accepted, not falsely flagged.
    assert summary["raw"]["correct_flagged_needs_review"] == 0
    assert summary["raw"]["correct_accepted"] == 1


def test_measure_validator_effectiveness_recall_and_false_review_rate_math(
    tmp_path: Path,
) -> None:
    dataset_dir = tmp_path / "dataset"
    generate_evaluation_dataset(dataset_dir, sample_count=2, seed=2026)
    manifest = load_manifest_jsonl(dataset_dir / "manifest.jsonl")
    clean_entries = [e for e in manifest.entries if e.variant_id == "clean_pdf"]
    ground_truth = W2Document.model_validate_json(
        (dataset_dir / clean_entries[0].ground_truth_path).read_text(encoding="utf-8")
    )

    result_path = tmp_path / "result.json"
    _write_result_json(
        result_path,
        variant_scope=["clean_pdf"],
        field_failures=[
            {
                "document_id": clean_entries[0].sample_id,
                "variant_id": "clean_pdf",
                "field_path": "employee.ssn",
                "expected": ground_truth.employee.ssn,
                "predicted": None,
                "failure_kind": "missing",
            }
        ],
    )

    summary = measure_validator_effectiveness(
        result_json_path=result_path, manifest_path=dataset_dir / "manifest.jsonl"
    )

    assert summary["raw"]["error_detection_recall"] == 1.0
    assert summary["raw"]["false_review_rate"] == 0.0
    assert summary["raw"]["automatic_acceptance_rate"] == 0.5


def test_known_ground_truth_gap_adjustment_only_affects_named_field(tmp_path: Path) -> None:
    """Internally generated ground truth always has `employer.name` set, so
    the Symage-specific known-gap adjustment should be a no-op here --
    confirming the adjustment is scoped to the one named field, not a
    blanket relaxation."""

    dataset_dir = tmp_path / "dataset"
    generate_evaluation_dataset(dataset_dir, sample_count=1, seed=2026)
    manifest = load_manifest_jsonl(dataset_dir / "manifest.jsonl")
    clean_entries = [e for e in manifest.entries if e.variant_id == "clean_pdf"]

    result_path = tmp_path / "result.json"
    _write_result_json(result_path, variant_scope=["clean_pdf"], field_failures=[])

    summary = measure_validator_effectiveness(
        result_json_path=result_path, manifest_path=dataset_dir / "manifest.jsonl"
    )

    assert summary["raw"] == summary["adjusted_for_known_ground_truth_gaps"]


def test_validator_only_ever_receives_the_reconstructed_prediction_not_ground_truth(
    tmp_path: Path,
) -> None:
    """Structural safeguard against ground-truth leakage into the validator
    call: patches validate_w2_document to record what it was actually
    called with, and asserts it differs from ground truth exactly where
    the reconstructed prediction should differ."""

    dataset_dir = tmp_path / "dataset"
    generate_evaluation_dataset(dataset_dir, sample_count=1, seed=2026)
    manifest = load_manifest_jsonl(dataset_dir / "manifest.jsonl")
    entry = next(e for e in manifest.entries if e.variant_id == "clean_pdf")
    ground_truth = W2Document.model_validate_json(
        (dataset_dir / entry.ground_truth_path).read_text(encoding="utf-8")
    )

    result_path = tmp_path / "result.json"
    _write_result_json(
        result_path,
        variant_scope=["clean_pdf"],
        field_failures=[
            {
                "document_id": entry.sample_id,
                "variant_id": "clean_pdf",
                "field_path": "employee.ssn",
                "expected": ground_truth.employee.ssn,
                "predicted": None,
                "failure_kind": "missing",
            }
        ],
    )

    with patch(
        "w2_pipeline.evaluation.validator_effectiveness.validate_w2_document",
        wraps=__import__(
            "w2_pipeline.validation.validator", fromlist=["validate_w2_document"]
        ).validate_w2_document,
    ) as spy:
        measure_validator_effectiveness(
            result_json_path=result_path, manifest_path=dataset_dir / "manifest.jsonl"
        )

    assert spy.call_count == 1
    called_with = spy.call_args[0][0]
    assert called_with.employee.ssn is None
    assert ground_truth.employee.ssn is not None
    assert called_with != ground_truth
