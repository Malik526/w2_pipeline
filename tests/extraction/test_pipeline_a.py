from pathlib import Path

import pytest

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.comparison import compare_w2_documents
from w2_pipeline.evaluation.dataset import generate_evaluation_dataset
from w2_pipeline.evaluation.inputs import ExtractionInput
from w2_pipeline.evaluation.manifest import DatasetSource, VariantType, load_manifest_jsonl
from w2_pipeline.evaluation.runner import evaluate_manifest
from w2_pipeline.extraction import MissingOcrDependencyError, PipelineAExtractor
from w2_pipeline.extraction.acquisition import ObservationAcquirer
from w2_pipeline.extraction.models import AcquisitionRoute
from w2_pipeline.extraction.ocr import TesseractOcrAdapter
from w2_pipeline.ingestion import ingest_document


def test_pipeline_a_extracts_internal_clean_pdf_with_native_route(tmp_path: Path) -> None:
    generate_evaluation_dataset(tmp_path, sample_count=5, seed=2026)
    pdf_path = tmp_path / "documents" / "w2_2026_0005_clean.pdf"
    expected = (tmp_path / "ground_truth" / "w2_2026_0005.json").read_text(encoding="utf-8")
    ingested = ingest_document(pdf_path, document_id="doc")

    result = PipelineAExtractor().extract_ingested(ingested)
    evaluation = compare_w2_documents(
        expected=W2Document.model_validate_json(expected),
        predicted=result.document,
        sample_id="w2_2026_0005",
        variant_id="clean_pdf",
    )

    assert result.route == AcquisitionRoute.NATIVE_PDF
    assert result.observation_count > 0
    assert evaluation.field_accuracy == 1.0


def test_pipeline_a_plugs_into_evaluation_runner_and_records_route(tmp_path: Path) -> None:
    generate_evaluation_dataset(tmp_path, sample_count=1, seed=2026)
    manifest = load_manifest_jsonl(tmp_path / "manifest.jsonl")
    clean_pdf = [entry for entry in manifest.entries if entry.variant_type == VariantType.CLEAN_PDF]

    result = evaluate_manifest(
        entries=clean_pdf,
        manifest_base_dir=tmp_path,
        extractor=PipelineAExtractor(),
        pipeline_id="pipeline_a",
    )

    assert result.document_evaluations[0].extraction_route == AcquisitionRoute.NATIVE_PDF.value


def test_pipeline_a_missing_ocr_failure_records_ocr_route(tmp_path: Path) -> None:
    from PIL import Image

    image_path = tmp_path / "sample.png"
    Image.new("RGB", (20, 10), color="white").save(image_path)
    ground_truth_dir = tmp_path / "ground_truth"
    ground_truth_dir.mkdir()
    from w2_pipeline.evaluation.synthetic import generate_synthetic_w2_documents
    expected = generate_synthetic_w2_documents()[0]
    (ground_truth_dir / "sample.json").write_text(expected.model_dump_json(), encoding="utf-8")

    from w2_pipeline.evaluation.manifest import (
        DatasetManifestEntry,
        ExpectedQuality,
        VariantType,
    )

    entry = DatasetManifestEntry(
        sample_id="sample",
        tax_year=2026,
        variant_id="clean_png",
        document_path="sample.png",
        ground_truth_path="ground_truth/sample.json",
        variant_type=VariantType.CLEAN_PNG,
        expected_quality=ExpectedQuality.CLEAN,
    )

    result = evaluate_manifest(
        entries=[entry],
        manifest_base_dir=tmp_path,
        extractor=PipelineAExtractor(),
        pipeline_id="pipeline_a",
    )

    assert result.document_evaluations[0].extraction_route == AcquisitionRoute.OCR.value


def test_pipeline_a_extraction_input_has_no_external_annotations(tmp_path: Path) -> None:
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nnot actually read")
    extraction_input = ExtractionInput(
        document_path=image_path,
        document_id="doc",
        source=DatasetSource.HUGGINGFACE,
        tax_year_hint=2026,
    )

    assert not hasattr(extraction_input, "tokens")
    assert not hasattr(extraction_input, "funsd_json")


def test_pipeline_a_image_route_reports_missing_ocr_runtime(tmp_path: Path) -> None:
    from PIL import Image

    image_path = tmp_path / "sample.png"
    Image.new("RGB", (20, 10), color="white").save(image_path)

    with pytest.raises(MissingOcrDependencyError):
        PipelineAExtractor(
            observation_acquirer=ObservationAcquirer(
                ocr_adapter=TesseractOcrAdapter(executable="definitely-missing-tesseract")
            )
        ).extract(
            ExtractionInput(
                document_path=image_path,
                document_id="doc",
                source=DatasetSource.SYNTHETIC,
                tax_year_hint=2026,
            )
        )
