from pathlib import Path

from w2_pipeline.evaluation.dataset import generate_evaluation_dataset
from w2_pipeline.extraction.native_pdf import extract_native_pdf_observations
from w2_pipeline.extraction.models import ObservationSource


def test_native_pdf_extraction_produces_ordered_observations_with_coordinates(tmp_path: Path) -> None:
    generate_evaluation_dataset(tmp_path, sample_count=1, seed=2026)
    pdf_path = tmp_path / "documents" / "w2_2026_0001_clean.pdf"

    observations = extract_native_pdf_observations(pdf_path)

    assert observations
    assert all(observation.source == ObservationSource.NATIVE_PDF for observation in observations)
    assert all(observation.page == 1 for observation in observations)
    assert observations == sorted(
        observations,
        key=lambda observation: (observation.page, observation.bbox.y0, observation.bbox.x0),
    )
    assert any(observation.text.startswith("SSN:") for observation in observations)
    assert all(observation.bbox.x1 >= observation.bbox.x0 for observation in observations)
