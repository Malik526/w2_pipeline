"""Pipeline B: Qwen3-VL vision-language model challenger for W-2 extraction.

Pipeline B stands on its own extraction architecture:

    pixels (rendered W-2 page image)
    -> Qwen3-VL-4B-Instruct
    -> structured JSON
    -> canonical W2Document

It deliberately does not import or depend on Pipeline A's OCR observations
(`w2_pipeline.extraction.ocr`/`ocr_paddle`/`ocr_backend`), regex/layout
parser (`parser_2026.py`), or `acquisition.py`. The only Pipeline A module it
shares is `pdf_rendering.py`, which is plain PyMuPDF page rasterization, not
extraction logic -- see `image_prep.py`.
"""

from __future__ import annotations

import time
from pathlib import Path

from w2_pipeline.evaluation.inputs import ExtractionInput
from w2_pipeline.extraction.pipeline_b.config import PipelineBConfig
from w2_pipeline.extraction.pipeline_b.image_prep import prepare_page_image
from w2_pipeline.extraction.pipeline_b.mapping import build_w2_document
from w2_pipeline.extraction.pipeline_b.model_runtime import QwenVlRuntime
from w2_pipeline.extraction.pipeline_b.models import PipelineBExtractionResult
from w2_pipeline.extraction.pipeline_b.prompt import build_extraction_prompt
from w2_pipeline.extraction.pipeline_b.response_parsing import parse_model_json
from w2_pipeline.ingestion import IngestionService
from w2_pipeline.ingestion.models import IngestedDocument


class PipelineBExtractor:
    """Vision-language model challenger: rendered page image -> W2Document."""

    pipeline_id = "pipeline_b"

    def __init__(
        self,
        *,
        ingestion_service: IngestionService | None = None,
        runtime: QwenVlRuntime | None = None,
        config: PipelineBConfig | None = None,
    ) -> None:
        self.ingestion_service = ingestion_service or IngestionService()
        self.runtime = runtime or QwenVlRuntime(config=config)

    def extract_ingested(self, ingested_document: IngestedDocument) -> PipelineBExtractionResult:
        """Extract one already-ingested document into canonical W-2 output."""

        started = time.perf_counter()
        with prepare_page_image(ingested_document) as image_path:
            raw_response = self.runtime.generate(image_path, build_extraction_prompt())

        parsed = parse_model_json(raw_response)
        document = build_w2_document(
            parsed,
            document_id=ingested_document.document_id,
            source_filename=ingested_document.source_filename,
            source_type=ingested_document.source_type,
        )
        duration = time.perf_counter() - started
        return PipelineBExtractionResult(
            document=document,
            model_id=self.runtime.config.model_id,
            duration_seconds=duration,
            model_load_duration_seconds=self.runtime.load_duration_seconds,
            device=self.runtime.config.device,
            dtype=self.runtime.config.dtype,
            gpu_diagnostics=self.runtime.gpu_diagnostics,
            raw_response_length=len(raw_response),
        )

    def extract(self, extraction_input: ExtractionInput) -> PipelineBExtractionResult:
        """Evaluation-runner adapter that receives annotation-free input."""

        ingested_document = self.ingestion_service.ingest(
            Path(extraction_input.document_path),
            document_id=extraction_input.document_id,
        )
        return self.extract_ingested(ingested_document)
