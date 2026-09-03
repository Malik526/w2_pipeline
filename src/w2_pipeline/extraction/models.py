"""Common text/layout observation and extraction result contracts."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from w2_pipeline.contracts.w2 import W2Document


class ExtractionModel(BaseModel):
    """Base model for strict extraction contracts."""

    model_config = ConfigDict(extra="forbid")


class ObservationSource(str, Enum):
    """Source route that produced one text/layout observation."""

    NATIVE_PDF = "native_pdf"
    OCR = "ocr"


class AcquisitionRoute(str, Enum):
    """Document-level route used by Pipeline A."""

    NATIVE_PDF = "native_pdf"
    OCR = "ocr"
    MIXED = "mixed"


class BoundingBox(ExtractionModel):
    """Top-left-origin bounding box using x0, y0, x1, y1 coordinates."""

    x0: float
    y0: float
    x1: float
    y1: float

    @model_validator(mode="after")
    def require_ordered_coordinates(self) -> "BoundingBox":
        if self.x1 < self.x0 or self.y1 < self.y0:
            raise ValueError("BoundingBox requires x1 >= x0 and y1 >= y0.")
        return self


class TextObservation(ExtractionModel):
    """One text observation with page and spatial coordinates."""

    text: str = Field(min_length=1)
    page: int = Field(ge=1)
    bbox: BoundingBox
    source: ObservationSource


class ObservationSet(ExtractionModel):
    """Common text/layout representation consumed by the W-2 parser."""

    observations: list[TextObservation] = Field(default_factory=list)
    route: AcquisitionRoute
    warnings: list[str] = Field(default_factory=list)


class ExtractionWarning(ExtractionModel):
    """Recoverable field-level warning emitted by Pipeline A."""

    field_path: str | None = None
    message: str = Field(min_length=1)


class ExtractionResult(ExtractionModel):
    """Pipeline A result wrapper with canonical output and route metadata."""

    document: W2Document
    pipeline: str = "pipeline_a"
    route: AcquisitionRoute
    observation_count: int = Field(ge=0)
    warnings: list[ExtractionWarning] = Field(default_factory=list)
