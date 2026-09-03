from pathlib import Path

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.dataset import generate_evaluation_dataset
from w2_pipeline.evaluation.manifest import VariantType, load_manifest_jsonl
from w2_pipeline.evaluation.models import DocumentEvaluationStatus
from w2_pipeline.evaluation.runner import evaluate_manifest
from w2_pipeline.ingestion import SourceDocumentType, ingest_document


class GroundTruthExtractor:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def extract(self, document_path: Path) -> W2Document:
        sample_id = document_path.name.split("_clean", maxsplit=1)[0]
        if "_rotated" in document_path.name:
            sample_id = document_path.name.split("_rotated", maxsplit=1)[0]
        if "_compressed" in document_path.name:
            sample_id = document_path.name.split("_compressed", maxsplit=1)[0]
        if "_blurred" in document_path.name:
            sample_id = document_path.name.split("_blurred", maxsplit=1)[0]
        ground_truth_path = self.base_dir / "ground_truth" / f"{sample_id}.json"
        return W2Document.model_validate_json(ground_truth_path.read_text(encoding="utf-8"))


class FailingExtractor:
    def extract(self, document_path: Path) -> W2Document:
        raise RuntimeError("synthetic failure")


class InvalidExtractor:
    def extract(self, document_path: Path) -> dict:
        return {"not": "a canonical w2"}


def test_dataset_generator_writes_manifest_ground_truth_and_documents(tmp_path: Path) -> None:
    entries = generate_evaluation_dataset(tmp_path, sample_count=2, seed=2026)

    manifest = load_manifest_jsonl(tmp_path / "manifest.jsonl")

    assert len(entries) == 10
    assert len(manifest.entries) == 10
    assert (tmp_path / "ground_truth" / "w2_2026_0001.json").exists()
    assert (tmp_path / "documents" / "w2_2026_0001_clean.pdf").exists()
    assert {entry.tax_year for entry in manifest.entries} == {2026}
    assert {entry.source.value for entry in manifest.entries} == {"synthetic"}


def test_generated_representative_documents_pass_phase_2_ingestion(tmp_path: Path) -> None:
    generate_evaluation_dataset(tmp_path, sample_count=1, seed=2026)
    manifest = load_manifest_jsonl(tmp_path / "manifest.jsonl")
    by_variant = {entry.variant_type: entry for entry in manifest.entries}

    pdf = ingest_document(tmp_path / by_variant[VariantType.CLEAN_PDF].document_path)
    png = ingest_document(tmp_path / by_variant[VariantType.CLEAN_PNG].document_path)
    jpeg = ingest_document(tmp_path / by_variant[VariantType.COMPRESSED_JPEG].document_path)

    assert pdf.source_type == SourceDocumentType.PDF
    assert pdf.page_count == 1
    assert png.source_type == SourceDocumentType.PNG
    assert png.image_width_pixels is not None
    assert jpeg.source_type == SourceDocumentType.JPEG
    assert jpeg.image_height_pixels is not None


def test_runner_records_success_latency_and_accuracy(tmp_path: Path) -> None:
    generate_evaluation_dataset(tmp_path, sample_count=1, seed=2026)
    manifest = load_manifest_jsonl(tmp_path / "manifest.jsonl")

    result = evaluate_manifest(
        entries=[manifest.entries[0]],
        manifest_base_dir=tmp_path,
        extractor=GroundTruthExtractor(tmp_path),
        pipeline_id="stub-ground-truth",
    )

    evaluation = result.document_evaluations[0]
    assert result.field_accuracy == 1.0
    assert evaluation.status == DocumentEvaluationStatus.SUCCESS
    assert evaluation.started_at is not None
    assert evaluation.duration_seconds is not None


def test_runner_isolates_pipeline_exceptions(tmp_path: Path) -> None:
    generate_evaluation_dataset(tmp_path, sample_count=1, seed=2026)
    manifest = load_manifest_jsonl(tmp_path / "manifest.jsonl")

    result = evaluate_manifest(
        entries=[manifest.entries[0]],
        manifest_base_dir=tmp_path,
        extractor=FailingExtractor(),
        pipeline_id="stub-failing",
    )

    evaluation = result.document_evaluations[0]
    assert evaluation.status == DocumentEvaluationStatus.EXTRACTION_FAILED
    assert evaluation.field_accuracy == 0.0
    assert result.failure_rate == 1.0


def test_runner_reports_invalid_canonical_predictions(tmp_path: Path) -> None:
    generate_evaluation_dataset(tmp_path, sample_count=1, seed=2026)
    manifest = load_manifest_jsonl(tmp_path / "manifest.jsonl")

    result = evaluate_manifest(
        entries=[manifest.entries[0]],
        manifest_base_dir=tmp_path,
        extractor=InvalidExtractor(),
        pipeline_id="stub-invalid",
    )

    assert result.document_evaluations[0].status == DocumentEvaluationStatus.INVALID_CANONICAL_RESULT
