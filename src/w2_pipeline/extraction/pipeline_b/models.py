"""Pipeline B result contract: canonical output plus VLM run diagnostics.

Deliberately separate from Pipeline A's `ExtractionResult`
(`w2_pipeline.extraction.models`), which types its `route` field as
`AcquisitionRoute` (`native_pdf`/`ocr`/`mixed`) -- an OCR-routing concept
that does not apply to a single vision-language model call. Both pipelines'
result types converge on the same canonical `W2Document`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from w2_pipeline.contracts.w2 import W2Document


class PipelineBExtractionResult(BaseModel):
    """Pipeline B result wrapper with canonical output and run diagnostics."""

    model_config = ConfigDict(extra="forbid")

    document: W2Document
    pipeline: str = "pipeline_b"
    route: str = "vlm"
    model_id: str
    duration_seconds: float = Field(ge=0)
    model_load_duration_seconds: float | None = Field(default=None, ge=0)
    device: str | None = None
    dtype: str | None = None
    gpu_diagnostics: dict[str, Any] | None = None
    raw_response_length: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)
