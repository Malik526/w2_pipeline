"""Document intake service for supported local source files."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from uuid import uuid4

from w2_pipeline.ingestion.errors import (
    CorruptImageError,
    CorruptPdfError,
    DocumentNotFoundError,
    DocumentTypeMismatchError,
    UnreadableDocumentError,
    UnsupportedDocumentTypeError,
)
from w2_pipeline.ingestion.image_inspector import inspect_image
from w2_pipeline.ingestion.models import IngestedDocument, SourceDocumentType
from w2_pipeline.ingestion.pdf_inspector import inspect_pdf

SUPPORTED_EXTENSION_TYPES = {
    ".pdf": SourceDocumentType.PDF,
    ".jpg": SourceDocumentType.JPEG,
    ".jpeg": SourceDocumentType.JPEG,
    ".png": SourceDocumentType.PNG,
}

MIME_TYPES = {
    SourceDocumentType.PDF: "application/pdf",
    SourceDocumentType.JPEG: "image/jpeg",
    SourceDocumentType.PNG: "image/png",
}


class IngestionService:
    """Validates and inspects local documents before extraction."""

    def ingest(self, source_path: str | Path, document_id: str | None = None) -> IngestedDocument:
        path = Path(source_path)
        self._ensure_readable_file(path)

        expected_type = self._expected_type_from_extension(path)
        actual_type = self._detect_type_from_magic(path)
        self._ensure_type_match(path, expected_type, actual_type)

        file_size_bytes = path.stat().st_size
        file_hash = self.calculate_sha256(path)
        stable_document_id = document_id or str(uuid4())

        if expected_type == SourceDocumentType.PDF:
            pdf_result = inspect_pdf(path)
            return IngestedDocument(
                document_id=stable_document_id,
                source_path=str(path),
                source_filename=path.name,
                source_type=expected_type,
                mime_type=MIME_TYPES[expected_type],
                file_size_bytes=file_size_bytes,
                sha256=file_hash,
                page_count=pdf_result.page_count,
                pdf_text_mode=pdf_result.pdf_text_mode,
                has_usable_embedded_text=pdf_result.has_usable_embedded_text,
            )

        try:
            image_result = inspect_image(path, expected_type)
        except (CorruptImageError, DocumentTypeMismatchError):
            raise

        return IngestedDocument(
            document_id=stable_document_id,
            source_path=str(path),
            source_filename=path.name,
            source_type=expected_type,
            mime_type=MIME_TYPES[expected_type],
            file_size_bytes=file_size_bytes,
            sha256=file_hash,
            image_width_pixels=image_result.width_pixels,
            image_height_pixels=image_result.height_pixels,
        )

    @staticmethod
    def calculate_sha256(path: str | Path) -> str:
        """Calculate a deterministic SHA-256 content fingerprint."""

        digest = hashlib.sha256()
        try:
            with Path(path).open("rb") as file_obj:
                for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError as exc:
            raise UnreadableDocumentError(f"Could not read source document: {Path(path).name}") from exc
        return digest.hexdigest()

    @staticmethod
    def _ensure_readable_file(path: Path) -> None:
        if not path.exists() or not path.is_file():
            raise DocumentNotFoundError(f"Source document not found: {path.name}")
        if not os.access(path, os.R_OK):
            raise UnreadableDocumentError(f"Source document is not readable: {path.name}")

    @staticmethod
    def _expected_type_from_extension(path: Path) -> SourceDocumentType:
        try:
            return SUPPORTED_EXTENSION_TYPES[path.suffix.lower()]
        except KeyError as exc:
            raise UnsupportedDocumentTypeError(
                f"Unsupported source document extension: {path.suffix or '<none>'}"
            ) from exc

    @staticmethod
    def _detect_type_from_magic(path: Path) -> SourceDocumentType | None:
        try:
            with path.open("rb") as file_obj:
                header = file_obj.read(16)
        except OSError as exc:
            raise UnreadableDocumentError(f"Could not read source document: {path.name}") from exc

        if header.startswith(b"%PDF-"):
            return SourceDocumentType.PDF
        if header.startswith(b"\xff\xd8\xff"):
            return SourceDocumentType.JPEG
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return SourceDocumentType.PNG
        return None

    @staticmethod
    def _ensure_type_match(
        path: Path,
        expected_type: SourceDocumentType,
        actual_type: SourceDocumentType | None,
    ) -> None:
        if actual_type is None:
            if expected_type == SourceDocumentType.PDF:
                raise CorruptPdfError(f"Source file is not a readable PDF: {path.name}")
            raise CorruptImageError(f"Source file is not a readable image: {path.name}")

        if actual_type != expected_type:
            raise DocumentTypeMismatchError(
                f"Source file extension does not match detected content type: {path.name}"
            )


def ingest_document(source_path: str | Path, document_id: str | None = None) -> IngestedDocument:
    """Ingest one local source document with the default service."""

    return IngestionService().ingest(source_path=source_path, document_id=document_id)
