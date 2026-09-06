"""Phase 7 downstream output contract.

`FinalizedW2` is the one artifact this project's extraction/validation/
review pipeline ultimately produces. Every real caller in this codebase
constructs it only through `finalize_document()` (`finalize.py`), which
enforces the `accepted` invariant by checking a `ValidationResult` before
ever building one.

`status: Literal["accepted"]` (Phase 8D.1) closes the one gap that
convention alone left open: without it, `FinalizedW2(status="needs_review",
...)` -- or any other string -- was previously syntactically valid,
silently defeating `finalize_document`'s gate for a caller who
constructed the model directly instead of going through it. This does
NOT make `finalize_document()` redundant: `FinalizedW2` still has no way
to verify that the `document` it was actually given passed validation
(it does not retain a `ValidationResult`), so a caller could still, in
principle, construct one with `status="accepted"` for a document that
was never checked. Closing that residual gap would mean re-validating
inside the model itself -- duplicating `finalize_document`'s job rather
than trusting it -- so it is intentionally left as a caller-discipline
invariant, same as before; only the impossible-by-construction status
string is now actually impossible.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from w2_pipeline.contracts.w2 import W2Document


class FinalizedW2(BaseModel):
    """A validated, downstream-ready canonical W-2 result."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1)
    status: Literal["accepted"] = "accepted"
    schema_version: int
    tax_year: int
    document: W2Document
