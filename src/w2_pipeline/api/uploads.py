"""Safe upload staging for the demo UI's `POST /api/process` endpoint.

Every uploaded file becomes one `StagedUpload` whose `document_id` is
derived from the original filename but restricted to a safe
`[A-Za-z0-9_-]` charset -- never the raw filename -- so it can be used
directly as a directory/document ID throughout the application layer
and as a download-lookup key with no path-traversal risk. Extension
validation reuses `w2_pipeline.ingestion.service.SUPPORTED_EXTENSION_TYPES`
directly rather than a second hardcoded list.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from w2_pipeline.ingestion.service import SUPPORTED_EXTENSION_TYPES

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9_-]+")
_MAX_DOCUMENT_ID_LENGTH = 80


class UnsupportedUploadError(ValueError):
    """Raised for an upload whose extension ingestion cannot handle."""


@dataclass(frozen=True)
class StagedUpload:
    document_id: str
    original_filename: str
    path: Path


def supported_extensions() -> tuple[str, ...]:
    return tuple(sorted(SUPPORTED_EXTENSION_TYPES))


def stage_uploads(
    uploads: list[tuple[str, bytes]],
    *,
    destination_dir: Path,
) -> list[StagedUpload]:
    """Write each `(filename, content)` pair under `destination_dir`.

    Raises `UnsupportedUploadError` for any unsupported extension before
    writing anything, so a batch never partially stages.
    """

    for filename, _content in uploads:
        extension = Path(filename).suffix.lower()
        if extension not in SUPPORTED_EXTENSION_TYPES:
            raise UnsupportedUploadError(
                f"Unsupported file type {extension or '<none>'!r} for {filename!r}; "
                f"supported: {', '.join(supported_extensions())}."
            )

    destination_dir.mkdir(parents=True, exist_ok=True)
    used_document_ids: set[str] = set()
    staged: list[StagedUpload] = []
    for filename, content in uploads:
        document_id = _unique_document_id(filename, used_document_ids)
        extension = Path(filename).suffix.lower()
        staged_path = destination_dir / f"{document_id}{extension}"
        staged_path.write_bytes(content)
        staged.append(StagedUpload(document_id=document_id, original_filename=filename, path=staged_path))
    return staged


def _unique_document_id(filename: str, used: set[str]) -> str:
    base = _safe_stem(filename)
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}_{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def _safe_stem(filename: str) -> str:
    # `Path(...).stem` on just the basename discards any directory
    # component the browser sent, so a filename like "../../etc/passwd"
    # can never influence the staged path beyond its own stem text.
    stem = Path(filename).name
    stem = Path(stem).stem
    stem = _UNSAFE_CHARS.sub("_", stem).strip("_")
    return (stem or "document")[:_MAX_DOCUMENT_ID_LENGTH]
