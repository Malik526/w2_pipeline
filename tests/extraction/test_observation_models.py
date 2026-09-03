import pytest
from pydantic import ValidationError

from w2_pipeline.extraction.models import (
    AcquisitionRoute,
    BoundingBox,
    ObservationSet,
    ObservationSource,
    TextObservation,
)


def test_text_observation_serializes_with_bbox_and_source_route() -> None:
    observation = TextObservation(
        text="SSN: 000-00-0001",
        page=1,
        bbox=BoundingBox(x0=10, y0=20, x1=120, y1=40),
        source=ObservationSource.NATIVE_PDF,
    )
    observation_set = ObservationSet(
        observations=[observation],
        route=AcquisitionRoute.NATIVE_PDF,
    )

    payload = observation_set.model_dump()

    assert payload["route"] == AcquisitionRoute.NATIVE_PDF
    assert payload["observations"][0]["bbox"]["x0"] == 10
    assert payload["observations"][0]["source"] == ObservationSource.NATIVE_PDF


def test_bbox_rejects_inverted_coordinates() -> None:
    with pytest.raises(ValidationError):
        BoundingBox(x0=10, y0=20, x1=5, y1=40)
