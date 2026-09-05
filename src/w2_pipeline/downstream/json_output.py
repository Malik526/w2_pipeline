"""JSON downstream output adapter.

Serializes a `FinalizedW2` as-is: the wrapper already carries
`document_id`/`status`/`schema_version`/`tax_year` alongside the full
canonical `document`, so no extra reshaping is needed. Pydantic's
`model_dump_json` preserves Unicode and canonical field names/semantics
exactly.
"""

from __future__ import annotations

from pathlib import Path

from w2_pipeline.downstream.models import FinalizedW2


def export_json(finalized: FinalizedW2, path: str | Path | None = None) -> str:
    """Return the finalized document as a JSON string.

    Writes the same text to `path` (UTF-8, Unicode preserved rather than
    `\\uXXXX`-escaped) when given.
    """

    text = finalized.model_dump_json(indent=2)
    if path is not None:
        Path(path).write_text(text, encoding="utf-8")
    return text
