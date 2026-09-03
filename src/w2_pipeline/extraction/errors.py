"""Explicit extraction errors for deterministic W-2 pipelines."""


class ExtractionError(Exception):
    """Base class for extraction pipeline failures."""


class MissingOcrDependencyError(ExtractionError):
    """Raised when the configured OCR runtime is unavailable."""

    extraction_route = "ocr"


class OcrExecutionError(ExtractionError):
    """Raised when OCR execution fails."""
