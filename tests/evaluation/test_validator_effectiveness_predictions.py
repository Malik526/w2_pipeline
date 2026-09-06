from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.dataset import generate_evaluation_dataset
from w2_pipeline.evaluation.manifest import load_manifest_jsonl
from w2_pipeline.evaluation.predictions import PredictionRecord, write_prediction_records_jsonl
from w2_pipeline.evaluation.validator_effectiveness_predictions import (
    measure_validator_effectiveness_from_predictions,
)
from w2_pipeline.review.field_paths import set_field_value


def _clean_entries(dataset_dir: Path, sample_count: int) -> list:
    generate_evaluation_dataset(dataset_dir, sample_count=sample_count, seed=2026)
    manifest = load_manifest_jsonl(dataset_dir / "manifest.jsonl")
    return [entry for entry in manifest.entries if entry.variant_id == "clean_pdf"]


def _ground_truth(dataset_dir: Path, entry) -> W2Document:
    return W2Document.model_validate_json((dataset_dir / entry.ground_truth_path).read_text(encoding="utf-8"))


def _write_predictions(path: Path, records: list[PredictionRecord]) -> None:
    write_prediction_records_jsonl(path, records)


def test_end_to_end_counts_correct_detectable_and_undetectable_errors(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    entries = _clean_entries(dataset_dir, sample_count=3)
    ground_truths = {entry.sample_id: _ground_truth(dataset_dir, entry) for entry in entries}

    correct_id, detectable_id, undetectable_id = (entry.sample_id for entry in entries)

    # Fully correct document: accepted.
    correct_doc = ground_truths[correct_id]
    # Detectable error: missing SSN triggers required_field_missing -> needs_review.
    detectable_doc = set_field_value(ground_truths[detectable_id], "employee.ssn", None)
    # Undetectable error: plausible-but-wrong money value, still passes every format rule.
    wrong_wages = ground_truths[undetectable_id].federal_wages_and_taxes.box_1_wages_tips_other_compensation + Decimal(
        "100.00"
    )
    undetectable_doc = set_field_value(
        ground_truths[undetectable_id],
        "federal_wages_and_taxes.box_1_wages_tips_other_compensation",
        str(wrong_wages),
    )

    predictions_path = tmp_path / "predictions.jsonl"
    _write_predictions(
        predictions_path,
        [
            PredictionRecord(
                document_id=correct_id,
                variant_id="clean_pdf",
                pipeline_id="pipeline_a",
                status="success",
                document=correct_doc,
                extraction_route="ocr",
            ),
            PredictionRecord(
                document_id=detectable_id,
                variant_id="clean_pdf",
                pipeline_id="pipeline_a",
                status="success",
                document=detectable_doc,
                extraction_route="ocr",
            ),
            PredictionRecord(
                document_id=undetectable_id,
                variant_id="clean_pdf",
                pipeline_id="pipeline_a",
                status="success",
                document=undetectable_doc,
                extraction_route="ocr",
            ),
        ],
    )

    report = measure_validator_effectiveness_from_predictions(
        predictions_path=predictions_path, manifest_path=dataset_dir / "manifest.jsonl"
    )
    overall = report["overall"]

    assert overall["total_documents"] == 3
    assert overall["correct_documents"] == 1
    assert overall["erroneous_documents"] == 2
    assert overall["erroneous_routed_needs_review"] == 1
    assert overall["erroneous_accepted"] == 1
    assert overall["correct_accepted"] == 1
    assert overall["correct_routed_needs_review"] == 0
    assert overall["error_detection_recall"] == 0.5
    assert overall["false_review_rate"] == 0.0
    assert overall["unsafe_acceptance_rate"] == 1 / 3
    assert overall["automatic_acceptance_rate"] == 2 / 3
    assert overall["review_queue_precision"] == 1.0


def test_validator_receives_only_the_real_prediction_never_ground_truth(tmp_path: Path) -> None:
    """Leakage-boundary safeguard: patches validate_w2_document to record
    what it was actually called with, confirming it is the saved
    prediction (with its real defect intact) and never ground truth."""

    dataset_dir = tmp_path / "dataset"
    entries = _clean_entries(dataset_dir, sample_count=1)
    entry = entries[0]
    ground_truth = _ground_truth(dataset_dir, entry)
    broken_doc = set_field_value(ground_truth, "employee.ssn", None)

    predictions_path = tmp_path / "predictions.jsonl"
    _write_predictions(
        predictions_path,
        [
            PredictionRecord(
                document_id=entry.sample_id,
                variant_id="clean_pdf",
                pipeline_id="pipeline_a",
                status="success",
                document=broken_doc,
                extraction_route="ocr",
            )
        ],
    )

    with patch(
        "w2_pipeline.evaluation.validator_effectiveness_predictions.validate_w2_document",
        wraps=__import__(
            "w2_pipeline.validation.validator", fromlist=["validate_w2_document"]
        ).validate_w2_document,
    ) as spy:
        measure_validator_effectiveness_from_predictions(
            predictions_path=predictions_path, manifest_path=dataset_dir / "manifest.jsonl"
        )

    assert spy.call_count == 1
    called_with = spy.call_args[0][0]
    assert called_with.employee.ssn is None
    assert ground_truth.employee.ssn is not None
    assert called_with != ground_truth


def test_row_merge_style_wrong_but_nonblank_employer_name_is_now_caught(tmp_path: Path) -> None:
    """Reproduces the real Phase 8C.2 residual shape: employer.name holds a
    non-blank, structurally valid string that happens to be wrong (the
    correct name plus trailing address text). At the time this analysis
    module was written (Phase 8C.3), no validation rule inspected
    employer.name's content beyond blankness, so this was accepted, not
    routed to review -- the real finding that motivated Phase 8C.5's
    address-leak heuristic and its Phase 8C.8 promotion into
    `w2_pipeline.validation.rules._check_employer_name_address_leak`.
    This exact shape (a street-number-like digit plus a road-suffix word)
    is now caught -- this test asserts the post-promotion behavior, not
    the original gap."""

    dataset_dir = tmp_path / "dataset"
    entries = _clean_entries(dataset_dir, sample_count=1)
    entry = entries[0]
    ground_truth = _ground_truth(dataset_dir, entry)
    row_merge_doc = set_field_value(
        ground_truth, "employer.name", f"{ground_truth.employer.name} 123 Fake Rd"
    )

    predictions_path = tmp_path / "predictions.jsonl"
    _write_predictions(
        predictions_path,
        [
            PredictionRecord(
                document_id=entry.sample_id,
                variant_id="clean_pdf",
                pipeline_id="pipeline_a",
                status="success",
                document=row_merge_doc,
                extraction_route="ocr",
            )
        ],
    )

    report = measure_validator_effectiveness_from_predictions(
        predictions_path=predictions_path, manifest_path=dataset_dir / "manifest.jsonl"
    )

    employer_name_class = report["error_classes"]["employer.name"]
    assert employer_name_class["affected_documents"] == 1
    assert employer_name_class["routed_needs_review"] == 1
    assert employer_name_class["accepted"] == 0
    assert employer_name_class["catch_rate"] == 1.0


def test_document_with_two_wrong_fields_counts_as_one_erroneous_document(tmp_path: Path) -> None:
    """Field-failure count must not be conflated with erroneous-document
    count: one document with two wrong fields is one erroneous document,
    contributing two entries to total_field_failures."""

    dataset_dir = tmp_path / "dataset"
    entries = _clean_entries(dataset_dir, sample_count=1)
    entry = entries[0]
    ground_truth = _ground_truth(dataset_dir, entry)
    doc = set_field_value(ground_truth, "employee.ssn", None)
    doc = set_field_value(doc, "employer.control_number", "WRONG-VALUE")

    predictions_path = tmp_path / "predictions.jsonl"
    _write_predictions(
        predictions_path,
        [
            PredictionRecord(
                document_id=entry.sample_id,
                variant_id="clean_pdf",
                pipeline_id="pipeline_a",
                status="success",
                document=doc,
                extraction_route="ocr",
            )
        ],
    )

    report = measure_validator_effectiveness_from_predictions(
        predictions_path=predictions_path, manifest_path=dataset_dir / "manifest.jsonl"
    )

    assert report["overall"]["total_documents"] == 1
    assert report["overall"]["erroneous_documents"] == 1
    assert report["total_field_failures"] == 2


def test_overlap_between_error_classes_detected_when_same_document_has_both(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    entries = _clean_entries(dataset_dir, sample_count=1)
    entry = entries[0]
    ground_truth = _ground_truth(dataset_dir, entry)
    doc = set_field_value(ground_truth, "employer.name", "Wrong Corp Extra Street")
    doc = set_field_value(doc, "box_13.retirement_plan", not ground_truth.box_13.retirement_plan)

    predictions_path = tmp_path / "predictions.jsonl"
    _write_predictions(
        predictions_path,
        [
            PredictionRecord(
                document_id=entry.sample_id,
                variant_id="clean_pdf",
                pipeline_id="pipeline_a",
                status="success",
                document=doc,
                extraction_route="ocr",
            )
        ],
    )

    report = measure_validator_effectiveness_from_predictions(
        predictions_path=predictions_path, manifest_path=dataset_dir / "manifest.jsonl"
    )

    overlap = report["error_classes"]["overlap_between_classes"]
    assert overlap["count"] == 1
    assert overlap["documents_with_both_failures"] == [f"{entry.sample_id}::clean_pdf"]


def test_per_variant_aggregation_isolates_each_variant(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    generate_evaluation_dataset(dataset_dir, sample_count=1, seed=2026)
    manifest = load_manifest_jsonl(dataset_dir / "manifest.jsonl")
    clean_entry = next(e for e in manifest.entries if e.variant_id == "clean_pdf")
    other_entry = next(e for e in manifest.entries if e.variant_id != "clean_pdf")
    clean_truth = _ground_truth(dataset_dir, clean_entry)
    other_truth = _ground_truth(dataset_dir, other_entry)
    broken = set_field_value(other_truth, "employee.ssn", None)

    predictions_path = tmp_path / "predictions.jsonl"
    _write_predictions(
        predictions_path,
        [
            PredictionRecord(
                document_id=clean_entry.sample_id,
                variant_id=clean_entry.variant_id,
                pipeline_id="pipeline_a",
                status="success",
                document=clean_truth,
                extraction_route="ocr",
            ),
            PredictionRecord(
                document_id=other_entry.sample_id,
                variant_id=other_entry.variant_id,
                pipeline_id="pipeline_a",
                status="success",
                document=broken,
                extraction_route="ocr",
            ),
        ],
    )

    report = measure_validator_effectiveness_from_predictions(
        predictions_path=predictions_path, manifest_path=dataset_dir / "manifest.jsonl"
    )

    assert report["by_variant"][clean_entry.variant_id]["erroneous_documents"] == 0
    assert report["by_variant"][other_entry.variant_id]["erroneous_documents"] == 1
    assert report["by_variant"][other_entry.variant_id]["erroneous_routed_needs_review"] == 1


def test_extraction_failure_status_treated_as_document_none() -> None:
    from w2_pipeline.evaluation.validator_effectiveness_predictions import _signals_for_record
    from w2_pipeline.validation.models import ExtractionOutcome

    failed_record = PredictionRecord(
        document_id="x",
        variant_id="clean_pdf",
        pipeline_id="pipeline_a",
        status="extraction_failed",
        document=None,
        extraction_route=None,
    )
    signals = _signals_for_record(failed_record)
    assert signals.outcome == ExtractionOutcome.EXTRACTION_FAILED


def test_employer_name_observation_count_threaded_from_pipeline_metadata() -> None:
    from w2_pipeline.evaluation.validator_effectiveness_predictions import _signals_for_record

    record = PredictionRecord(
        document_id="x",
        variant_id="clean_pdf",
        pipeline_id="pipeline_a",
        status="success",
        document=None,
        pipeline_metadata={"employer_name_observation_count": 2},
    )

    signals = _signals_for_record(record)

    assert signals.employer_name_observation_count == 2


def test_employer_name_observation_count_absent_for_records_that_predate_it() -> None:
    from w2_pipeline.evaluation.validator_effectiveness_predictions import _signals_for_record

    record = PredictionRecord(
        document_id="x", variant_id="clean_pdf", pipeline_id="pipeline_a", status="success", document=None
    )

    signals = _signals_for_record(record)

    assert signals.employer_name_observation_count is None
