"""CSV downstream output adapter.

Strategy: one row per document. Every scalar field (metadata, employee,
employer, federal boxes, Box 13 flags) flattens into its own column using
the same dotted-path convention
`w2_pipeline.evaluation.comparison.flatten_w2_document` uses for scoring.
Repeated structures (Box 12/14 entries, tipped occupation codes,
state/local entries) do not flatten sensibly into fixed scalar columns --
a document can have zero, one, or several of each -- so each is
JSON-string-encoded into a single cell (option A from the brief: simplest
stable choice, avoids a variable, document-dependent column count or a
second output file per repeated structure).
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from w2_pipeline.downstream.models import FinalizedW2

_REPEATED_FIELDS = (
    "box_12_entries",
    "box_14_entries",
    "tipped_occupation_codes",
    "state_local_entries",
)
_EXCLUDED_FIELDS = ("field_observations",)


def export_csv(finalized: FinalizedW2, path: str | Path | None = None) -> str:
    """Return the finalized document as a single-row CSV string.

    Writes the same text to `path` (UTF-8) when given.
    """

    payload = finalized.document.model_dump(mode="json")
    row: dict[str, str] = {}
    scalar_payload = {
        key: value
        for key, value in payload.items()
        if key not in _REPEATED_FIELDS and key not in _EXCLUDED_FIELDS
    }
    _flatten_scalars(scalar_payload, prefix="", row=row)
    for field_name in _REPEATED_FIELDS:
        row[field_name] = json.dumps(payload.get(field_name) or [], ensure_ascii=False)

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=sorted(row))
    writer.writeheader()
    writer.writerow(row)
    text = buffer.getvalue()

    if path is not None:
        Path(path).write_text(text, encoding="utf-8")
    return text


def _flatten_scalars(value: Any, *, prefix: str, row: dict[str, str]) -> None:
    if isinstance(value, dict):
        for key in sorted(value):
            _flatten_scalars(value[key], prefix=f"{prefix}.{key}" if prefix else key, row=row)
        return
    row[prefix] = "" if value is None else str(value)
