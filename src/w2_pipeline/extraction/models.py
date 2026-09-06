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
    ocr_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Native OCR engine recognition confidence for this observation, "
            "on a 0..1 scale, or None when unavailable. PaddleOCR emits this "
            "natively in 0..1 (`rec_scores`); Tesseract's TSV `conf` column "
            "is native 0..100 and is divided by 100 before being stored here "
            "so both backends share one comparable scale -- a linear "
            "rescale of the engine's own real value, not a fabricated one. "
            "Native PDF text observations always leave this None (there is "
            "no OCR recognition step to have a confidence for). This is "
            "instrumentation only: no parser or validator decision may "
            "depend on it (Phase 8C.4)."
        ),
    )
    is_supplemental: bool = Field(
        default=False,
        description=(
            "True when this observation came from a targeted supplemental "
            "OCR pass (e.g. Tesseract's SSN-recovery PSM 6 pass) rather than "
            "the main pass. Supplemental observations are geo-fenced to "
            "their own approved zone(s) at the OCR adapter and are excluded "
            "from primary row-based line reconstruction in the parser, so a "
            "second pass over the same page can never duplicate or corrupt "
            "an already-successful primary-path field; it can only feed the "
            "existing zone-based OCR fallbacks that already fire solely "
            "when the primary path left a field empty."
        ),
    )


class ObservationSet(ExtractionModel):
    """Common text/layout representation consumed by the W-2 parser."""

    observations: list[TextObservation] = Field(default_factory=list)
    route: AcquisitionRoute
    warnings: list[str] = Field(default_factory=list)
    box_13_visual_marks: dict[str, bool] = Field(
        default_factory=dict,
        description=(
            "Backend-neutral pixel-based Box 13 checkbox detections, keyed "
            "by flag name (e.g. 'retirement_plan'), independent of OCR text "
            "output. See w2_pipeline.extraction.checkbox_vision."
        ),
    )


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
    employer_name_observation_count: int | None = Field(
        default=None,
        ge=0,
        description=(
            "How many OCR observations contributed to employer.name's "
            "value (Phase 8C.8 layout-provenance signal), None when "
            "employer.name is None or no matching observation row was "
            "found. Carried to the validator via "
            "ExtractionSignals.employer_name_observation_count -- never "
            "a parser/extraction decision input."
        ),
    )
