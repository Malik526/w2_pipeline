"""Explicit ingestion exceptions for safe document intake failures."""


class IngestionError(Exception):
    """Base class for ingestion failures."""


class DocumentNotFoundError(IngestionError):
    """Raised when a source document path does not exist or is not a file."""


class UnreadableDocumentError(IngestionError):
    """Raised when a source document cannot be read for intake metadata."""


class UnsupportedDocumentTypeError(IngestionError):
    """Raised when the source document type is not supported."""


class DocumentTypeMismatchError(IngestionError):
    """Raised when extension and detectable content type disagree."""


class CorruptPdfError(IngestionError):
    """Raised when a PDF cannot be opened or inspected as a PDF."""


class CorruptImageError(IngestionError):
    """Raised when an image cannot be opened or inspected as an image."""
