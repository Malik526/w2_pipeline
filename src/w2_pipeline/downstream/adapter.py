"""Downstream output adapter boundary.

```text
FinalizedW2
    |
    +--> export_json()  (json_output.py)
    +--> export_csv()   (csv_output.py)
    +--> (future) internal database / tax software / REST API / webhook /
         QuickBooks or other accounting-platform adapter
```

A future adapter only needs to accept a `FinalizedW2` and return/persist
its own representation -- it never touches extraction, validation, or
review workflow code, and it can rely on `FinalizedW2` already being
`accepted` (enforced once, in `finalize.py`). No vendor-specific
integration (QuickBooks or otherwise) is implemented in this phase;
`OutputAdapter` exists to document and type-check that boundary, not to
force every adapter into a class hierarchy -- `export_json`/`export_csv`
are plain functions satisfying it structurally.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from w2_pipeline.downstream.models import FinalizedW2


@runtime_checkable
class OutputAdapter(Protocol):
    """Structural contract every downstream output adapter satisfies."""

    def __call__(self, finalized: FinalizedW2, path: str | Path | None = None) -> str:
        """Render `finalized`, optionally writing it to `path`, and return the text."""
