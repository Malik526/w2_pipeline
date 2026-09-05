"""Explicit extraction errors for Pipeline B's Qwen3-VL runtime.

Mirrors the diagnostic granularity `w2_pipeline.extraction.errors` gives
Pipeline A (`MissingOcrDependencyError`, `OcrExecutionError`), but for the
distinct failure surface of a vision-language model pipeline: model load,
image preparation, inference, malformed output, and schema validation are
each their own class so a caller can tell them apart.
"""


class PipelineBError(Exception):
    """Base class for Pipeline B failures."""


class ModelLoadError(PipelineBError):
    """Raised when the Qwen3-VL model/processor cannot be loaded."""


class ImagePreparationError(PipelineBError):
    """Raised when the source document cannot be prepared as a page image."""


class VlmInferenceError(PipelineBError):
    """Raised when model inference itself fails."""


class MalformedModelOutputError(PipelineBError):
    """Raised when the model's raw response is not parseable JSON."""


class SchemaValidationError(PipelineBError):
    """Raised when parsed JSON fails canonical W2Document validation."""
