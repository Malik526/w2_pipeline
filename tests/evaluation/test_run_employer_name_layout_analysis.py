from pathlib import Path

from w2_pipeline.evaluation.dataset import generate_evaluation_dataset
from w2_pipeline.evaluation.manifest import load_manifest_jsonl
from w2_pipeline.evaluation.run_employer_name_layout_analysis import run_layout_signal_analysis


def test_end_to_end_on_synthetic_dataset_reports_matched_signals(tmp_path: Path) -> None:
    """Uses the internal synthetic generator (native PDF text, not OCR) --
    confirms the pipeline runs end to end and reports geometry signals
    without crashing, and that correctness is computed independently of
    the signals themselves (leakage boundary: ground truth is not
    consulted until after `compute_layout_signals` already ran)."""

    dataset_dir = tmp_path / "dataset"
    generate_evaluation_dataset(dataset_dir, sample_count=2, seed=2026)
    manifest_path = dataset_dir / "manifest.jsonl"
    manifest = load_manifest_jsonl(manifest_path)
    clean_entries = [entry for entry in manifest.entries if entry.variant_id == "clean_pdf"]
    assert len(clean_entries) == 2

    report = run_layout_signal_analysis(manifest_path=manifest_path, variant_id="clean_pdf")

    assert report["documents"] == 2
    assert report["correct_documents"] + report["erroneous_documents"] == 2
    for row in report["rows"]:
        assert row["status"] == "success"
        assert "signals" in row


def test_limit_and_variant_filters_are_respected(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    generate_evaluation_dataset(dataset_dir, sample_count=3, seed=2026)
    manifest_path = dataset_dir / "manifest.jsonl"

    report = run_layout_signal_analysis(manifest_path=manifest_path, variant_id="clean_pdf", limit=1)

    assert report["documents"] == 1
    assert report["rows"][0]["variant_id"] == "clean_pdf"
