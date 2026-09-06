from pathlib import Path

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.dataset import generate_evaluation_dataset
from w2_pipeline.evaluation.manifest import load_manifest_jsonl
from w2_pipeline.evaluation.predictions import PredictionRecord, write_prediction_records_jsonl
from w2_pipeline.evaluation.run_employer_name_heuristic_analysis import (
    run_employer_name_heuristic_analysis,
)
from w2_pipeline.review.field_paths import set_field_value


def test_confusion_matrix_and_leakage_boundary_end_to_end(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    generate_evaluation_dataset(dataset_dir, sample_count=2, seed=2026)
    manifest = load_manifest_jsonl(dataset_dir / "manifest.jsonl")
    entries = [entry for entry in manifest.entries if entry.variant_id == "clean_pdf"]
    correct_entry, leak_entry = entries[0], entries[1]

    correct_truth = W2Document.model_validate_json(
        (dataset_dir / correct_entry.ground_truth_path).read_text(encoding="utf-8")
    )
    leak_truth = W2Document.model_validate_json(
        (dataset_dir / leak_entry.ground_truth_path).read_text(encoding="utf-8")
    )
    leaked_doc = set_field_value(
        leak_truth, "employer.name", f"{leak_truth.employer.name} 2861 Geneva Ponce De Leon Rd"
    )

    predictions_path = tmp_path / "predictions.jsonl"
    write_prediction_records_jsonl(
        predictions_path,
        [
            PredictionRecord(
                document_id=correct_entry.sample_id,
                variant_id="clean_pdf",
                pipeline_id="pipeline_a",
                status="success",
                document=correct_truth,
                extraction_route="ocr",
            ),
            PredictionRecord(
                document_id=leak_entry.sample_id,
                variant_id="clean_pdf",
                pipeline_id="pipeline_a",
                status="success",
                document=leaked_doc,
                extraction_route="ocr",
            ),
        ],
    )

    report = run_employer_name_heuristic_analysis(
        predictions_path=predictions_path, manifest_path=dataset_dir / "manifest.jsonl"
    )

    assert report["total_documents"] == 2
    assert report["correct_documents"] == 1
    assert report["erroneous_documents"] == 1

    combined = report["candidate_rules"]["C_expanded_number_and_suffix"]
    assert combined["true_positives"] == 1
    assert combined["false_positives"] == 0
    assert combined["recall"] == 1.0
    assert combined["precision"] == 1.0
    assert combined["false_review_rate"] == 0.0
    assert f"{leak_entry.sample_id}::clean_pdf" not in combined["false_negative_document_ids"]


def test_missing_document_flags_every_rule_false_without_error(tmp_path: Path) -> None:
    """A failed extraction (document=None) must not crash the analysis or
    be fabricated as a flag -- every rule reports False for it."""

    dataset_dir = tmp_path / "dataset"
    generate_evaluation_dataset(dataset_dir, sample_count=1, seed=2026)
    manifest = load_manifest_jsonl(dataset_dir / "manifest.jsonl")
    entry = next(e for e in manifest.entries if e.variant_id == "clean_pdf")

    predictions_path = tmp_path / "predictions.jsonl"
    write_prediction_records_jsonl(
        predictions_path,
        [
            PredictionRecord(
                document_id=entry.sample_id,
                variant_id="clean_pdf",
                pipeline_id="pipeline_a",
                status="extraction_failed",
                document=None,
            )
        ],
    )

    report = run_employer_name_heuristic_analysis(
        predictions_path=predictions_path, manifest_path=dataset_dir / "manifest.jsonl"
    )

    assert report["rows"][0]["correct"] is False
    assert all(flag is False for flag in report["rows"][0]["flags"].values())
