"""Document ingestion boundary for W-2 Pipeline."""

from w2_pipeline.ingestion.errors import (
    CorruptImageError,
    CorruptPdfError,
    DocumentNotFoundError,
    DocumentTypeMismatchError,
    IngestionError,
    UnreadableDocumentError,
    UnsupportedDocumentTypeError,
)
from w2_pipeline.ingestion.models import (
    ImageInspectionResult,
    IngestedDocument,
    IngestionStatus,
    PdfInspectionResult,
    PdfPageInspection,
    PdfTextMode,
    SourceDocumentType,
)
from w2_pipeline.ingestion.service import IngestionService, ingest_document

__all__ = [
    "CorruptImageError",
    "CorruptPdfError",
    "DocumentNotFoundError",
    "DocumentTypeMismatchError",
    "ImageInspectionResult",
    "IngestedDocument",
    "IngestionError",
    "IngestionService",
    "IngestionStatus",
    "PdfInspectionResult",
    "PdfPageInspection",
    "PdfTextMode",
    "SourceDocumentType",
    "UnreadableDocumentError",
    "UnsupportedDocumentTypeError",
    "ingest_document",
]
