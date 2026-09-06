from pathlib import Path

import pytest

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.dataset import generate_evaluation_dataset
from w2_pipeline.evaluation.manifest import load_manifest_jsonl
from w2_pipeline.evaluation.predictions import (
    PredictionRecord,
    load_prediction_records_jsonl,
    write_prediction_records_jsonl,
)
from w2_pipeline.evaluation.runner import evaluate_manifest


def test_prediction_record_never_carries_ground_truth_fields() -> None:
    # Structural check: PredictionRecord's own schema has no field named
    # or shaped like an "expected"/ground-truth value -- only what an
    # extractor produced.
    assert set(PredictionRecord.model_fields) == {
        "document_id",
        "variant_id",
        "pipeline_id",
        "status",
        "document",
        "extraction_route",
        "duration_seconds",
        "message",
        "pipeline_metadata",
    }


def test_write_and_load_prediction_records_round_trip(tmp_path: Path) -> None:
    from w2_pipeline.evaluation.synthetic import generate_synthetic_w2_documents

    document = generate_synthetic_w2_documents()[0]
    records = [
        PredictionRecord(
            document_id="doc-1",
            variant_id="clean_pdf",
            pipeline_id="pipeline_a",
            status="success",
            document=document,
            extraction_route="native_pdf",
            duration_seconds=1.23,
        ),
        PredictionRecord(
            document_id="doc-2",
            variant_id="clean_pdf",
            pipeline_id="pipeline_a",
            status="extraction_failed",
            document=None,
            message="Extractor raised MissingOcrDependencyError.",
        ),
    ]
    path = tmp_path / "predictions.jsonl"

    write_prediction_records_jsonl(path, records)
    loaded = load_prediction_records_jsonl(path)

    assert len(loaded) == 2
    assert loaded[0].document == document
    assert loaded[0].status == "success"
    assert loaded[1].document is None
    assert loaded[1].status == "extraction_failed"


def test_evaluate_manifest_populates_predictions_out_on_success(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    generate_evaluation_dataset(dataset_dir, sample_count=2, seed=2026)
    manifest = load_manifest_jsonl(dataset_dir / "manifest.jsonl")
    clean_entries = [e for e in manifest.entries if e.variant_id == "clean_pdf"]

    class EchoExtractor:
        def extract(self, extraction_input):
            ground_truth_path = next(
                dataset_dir / e.ground_truth_path
                for e in clean_entries
                if f"{e.sample_id}:{e.variant_id}" == extraction_input.document_id
            )
            return W2Document.model_validate_json(ground_truth_path.read_text())

    predictions: list[PredictionRecord] = []
    result = evaluate_manifest(
        entries=clean_entries,
        manifest_base_dir=dataset_dir,
        extractor=EchoExtractor(),
        pipeline_id="pipeline_a",
        predictions_out=predictions,
    )

    assert result.field_accuracy == 1.0
    assert len(predictions) == 2
    assert all(record.status == "success" for record in predictions)
    assert all(record.document is not None for record in predictions)
    assert all(record.pipeline_id == "pipeline_a" for record in predictions)
    assert {record.document_id for record in predictions} == {
        entry.sample_id for entry in clean_entries
    }


def test_evaluate_manifest_records_extraction_failure_in_predictions_out(
    tmp_path: Path,
) -> None:
    dataset_dir = tmp_path / "dataset"
    generate_evaluation_dataset(dataset_dir, sample_count=1, seed=2026)
    manifest = load_manifest_jsonl(dataset_dir / "manifest.jsonl")
    entry = next(e for e in manifest.entries if e.variant_id == "clean_pdf")

    class FailingExtractor:
        def extract(self, extraction_input):
            raise RuntimeError("boom")

    predictions: list[PredictionRecord] = []
    evaluate_manifest(
        entries=[entry],
        manifest_base_dir=dataset_dir,
        extractor=FailingExtractor(),
        pipeline_id="pipeline_a",
        predictions_out=predictions,
    )

    assert len(predictions) == 1
    assert predictions[0].status == "extraction_failed"
    assert predictions[0].document is None
    assert "boom" not in (predictions[0].message or "")  # message names the exception class, not its text
    assert "RuntimeError" in predictions[0].message


def test_evaluate_manifest_does_not_require_predictions_out(tmp_path: Path) -> None:
    """Backward compatibility: omitting predictions_out changes nothing."""

    dataset_dir = tmp_path / "dataset"
    generate_evaluation_dataset(dataset_dir, sample_count=1, seed=2026)
    manifest = load_manifest_jsonl(dataset_dir / "manifest.jsonl")
    entry = next(e for e in manifest.entries if e.variant_id == "clean_pdf")

    class FailingExtractor:
        def extract(self, extraction_input):
            raise RuntimeError("boom")

    result = evaluate_manifest(
        entries=[entry],
        manifest_base_dir=dataset_dir,
        extractor=FailingExtractor(),
        pipeline_id="pipeline_a",
    )

    assert result.total_documents == 1
