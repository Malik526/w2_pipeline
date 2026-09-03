"""Extractor input boundary that prevents annotation leakage."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from w2_pipeline.evaluation.manifest import DatasetSource


class ExtractionInput(BaseModel):
    """Production-realistic input passed to evaluated extraction pipelines.

    Dataset annotations such as tokens, bounding boxes, entity tags, FUNSD,
    COCO, and YOLO data are deliberately absent from this strict model.
    """

    model_config = ConfigDict(extra="forbid")

    document_path: Path
    document_id: str = Field(min_length=1)
    tax_year_hint: int | None = None
    source: DatasetSource
