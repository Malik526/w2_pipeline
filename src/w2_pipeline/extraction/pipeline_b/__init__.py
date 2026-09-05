"""Pipeline B: Qwen3-VL-4B-Instruct vision-language W-2 extraction challenger.

See `docs/contracts/extraction-pipeline-b.md` for the architecture contract.
"""

from w2_pipeline.extraction.pipeline_b.config import PipelineBConfig, describe_gpu_availability
from w2_pipeline.extraction.pipeline_b.errors import (
    ImagePreparationError,
    MalformedModelOutputError,
    ModelLoadError,
    PipelineBError,
    SchemaValidationError,
    VlmInferenceError,
)
from w2_pipeline.extraction.pipeline_b.extractor import PipelineBExtractor
from w2_pipeline.extraction.pipeline_b.model_runtime import QwenVlRuntime
from w2_pipeline.extraction.pipeline_b.models import PipelineBExtractionResult

__all__ = [
    "ImagePreparationError",
    "MalformedModelOutputError",
    "ModelLoadError",
    "PipelineBConfig",
    "PipelineBError",
    "PipelineBExtractionResult",
    "PipelineBExtractor",
    "QwenVlRuntime",
    "SchemaValidationError",
    "VlmInferenceError",
    "describe_gpu_availability",
]
