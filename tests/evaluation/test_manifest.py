from pathlib import Path

import pytest

from w2_pipeline.evaluation.manifest import (
    DatasetManifestEntry,
    DatasetSource,
    ExpectedQuality,
    VariantType,
    load_manifest_jsonl,
    write_manifest_jsonl,
)


def test_manifest_entries_round_trip_and_retain_metadata(tmp_path: Path) -> None:
    document_path = tmp_path / "documents" / "w2_2026_0001_clean.pdf"
    ground_truth_path = tmp_path / "ground_truth" / "w2_2026_0001.json"
    document_path.parent.mkdir()
    ground_truth_path.parent.mkdir()
    document_path.write_bytes(b"%PDF-1.7\n%%EOF")
    ground_truth_path.write_text("{}", encoding="utf-8")
    entry = DatasetManifestEntry(
        sample_id="w2_2026_0001",
        tax_year=2026,
        variant_id="clean_pdf",
        document_path="documents/w2_2026_0001_clean.pdf",
        ground_truth_path="ground_truth/w2_2026_0001.json",
        variant_type=VariantType.CLEAN_PDF,
        expected_quality=ExpectedQuality.CLEAN,
        source=DatasetSource.SYNTHETIC,
        pii=False,
        generator_seed=2026,
    )
    manifest_path = tmp_path / "manifest.jsonl"

    write_manifest_jsonl(manifest_path, [entry])
    manifest = load_manifest_jsonl(manifest_path)

    loaded = manifest.entries[0]
    assert loaded.sample_id == "w2_2026_0001"
    assert loaded.tax_year == 2026
    assert loaded.source == DatasetSource.SYNTHETIC
    assert loaded.variant_type == VariantType.CLEAN_PDF
    assert loaded.pii is False


def test_manifest_loader_detects_missing_referenced_files(tmp_path: Path) -> None:
    entry = DatasetManifestEntry(
        sample_id="w2_2026_0001",
        tax_year=2026,
        variant_id="clean_pdf",
        document_path="documents/missing.pdf",
        ground_truth_path="ground_truth/missing.json",
        variant_type=VariantType.CLEAN_PDF,
        expected_quality=ExpectedQuality.CLEAN,
        pii=False,
    )
    manifest_path = tmp_path / "manifest.jsonl"
    write_manifest_jsonl(manifest_path, [entry])

    with pytest.raises(FileNotFoundError):
        load_manifest_jsonl(manifest_path)


def test_synthetic_manifest_entries_cannot_mark_pii_true() -> None:
    with pytest.raises(ValueError):
        DatasetManifestEntry(
            sample_id="w2_2026_0001",
            tax_year=2026,
            variant_id="clean_pdf",
            document_path="documents/sample.pdf",
            ground_truth_path="ground_truth/sample.json",
            variant_type=VariantType.CLEAN_PDF,
            expected_quality=ExpectedQuality.CLEAN,
            source=DatasetSource.SYNTHETIC,
            pii=True,
        )
