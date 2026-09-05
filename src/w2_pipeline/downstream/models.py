"""Phase 7 downstream output contract.

`FinalizedW2` is the one artifact this project's extraction/validation/
review pipeline ultimately produces. It can only be constructed through
`finalize_document()` (`finalize.py`), which enforces the `accepted`
invariant -- there is no public constructor path that skips validation.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from w2_pipeline.contracts.w2 import W2Document


class FinalizedW2(BaseModel):
    """A validated, downstream-ready canonical W-2 result."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1)
    status: str = "accepted"
    schema_version: int
    tax_year: int
    document: W2Document
