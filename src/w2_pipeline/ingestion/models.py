"""Typed ingestion result models shared by future extraction pipelines."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class IngestionModel(BaseModel):
    """Base model for strict ingestion contracts."""

    model_config = ConfigDict(extra="forbid")


class SourceDocumentType(str, Enum):
    """Supported source document types at the Phase 2 system boundary."""

    PDF = "pdf"
    JPEG = "jpeg"
    PNG = "png"


class PdfTextMode(str, Enum):
    """Aggregate PDF text routing classification."""

    EMBEDDED_TEXT = "embedded_text"
    IMAGE_ONLY = "image_only"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class IngestionStatus(str, Enum):
    """Successful ingestion status for normalized intake results."""

    READY = "ready"
    REJECTED = "rejected"
    FAILED = "failed"


class PdfPageInspection(IngestionModel):
    """Page-level PDF embedded-text inspection result."""

    page_number: int = Field(ge=1)
    meaningful_text_character_count: int = Field(ge=0)
    has_usable_embedded_text: bool


class PdfInspectionResult(IngestionModel):
    """Lightweight PDF inspection result used for extraction routing later."""

    page_count: int = Field(ge=0)
    pdf_text_mode: PdfTextMode
    has_usable_embedded_text: bool
    pages: list[PdfPageInspection] = Field(default_factory=list)


class ImageInspectionResult(IngestionModel):
    """Lightweight image readability and dimensions result."""

    width_pixels: int = Field(gt=0)
    height_pixels: int = Field(gt=0)


class IngestedDocument(IngestionModel):
    """Normalized intake result returned before any W-2 field extraction."""

    document_id: str = Field(min_length=1)
    source_path: str = Field(min_length=1)
    source_filename: str = Field(min_length=1)
    source_type: SourceDocumentType
    mime_type: str = Field(min_length=1)
    file_size_bytes: int = Field(ge=0)
    sha256: str = Field(min_length=64, max_length=64)
    page_count: int | None = Field(default=None, ge=0)
    pdf_text_mode: PdfTextMode | None = None
    has_usable_embedded_text: bool | None = None
    image_width_pixels: int | None = Field(default=None, gt=0)
    image_height_pixels: int | None = Field(default=None, gt=0)
    status: IngestionStatus = IngestionStatus.READY
