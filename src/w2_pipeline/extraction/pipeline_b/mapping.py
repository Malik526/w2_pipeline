"""Map Qwen3-VL's parsed JSON payload onto the canonical W2Document contract.

This is the only place Pipeline B constructs canonical types. It fills in
`W2Metadata` itself (document ID, source filename, and the fixed 2026
tax-year/schema-version scope are operational/pipeline-level facts, not
visual observations the model should be asked for) and performs structural
defaulting only for entirely-absent sections (so a model that omits an
empty nested object/list is not penalized versus one that includes it
explicitly) and one key-name normalization for `state_local_entries` (see
`_STATE_LOCAL_KEY_ALIASES`, discovered during Phase 5A smoke testing). It
never repairs, regexes, or reinterprets a leaf *value* the model
provided -- that would blur Pipeline B's extraction boundary with Pipeline
A's deterministic parser. A leaf value that fails canonical validation is
reported as a schema validation failure, not silently corrected.
"""

from __future__ import annotations

from pydantic import ValidationError

from w2_pipeline.contracts.w2 import (
    Box12Entry,
    Box13Flags,
    Box14Entry,
    Employee,
    Employer,
    FederalWagesAndTaxes,
    SourceFileType,
    StateLocalEntry,
    TippedOccupationCode,
    W2Document,
    W2Metadata,
)
from w2_pipeline.extraction.pipeline_b.errors import SchemaValidationError
from w2_pipeline.ingestion.models import SourceDocumentType

_SOURCE_FILE_TYPES = {
    SourceDocumentType.PDF: SourceFileType.PDF,
    SourceDocumentType.JPEG: SourceFileType.JPEG,
    SourceDocumentType.PNG: SourceFileType.PNG,
}

# Observed during Phase 5A smoke testing: despite the prompt's explicit
# `box_15_state`-style canonical key names, the model sometimes drops the
# box-number prefix for this one nested section (e.g. `"state"` instead of
# `"box_15_state"`) while every other section matches the canonical keys
# exactly. This is a structural JSON key rename, not a value
# repair/inference -- the "normalize representation into the canonical
# Pydantic model" step the Phase 5A brief explicitly allows -- so it is
# applied uniformly to every `state_local_entries` item before validation.
_STATE_LOCAL_KEY_ALIASES = {
    "state": "box_15_state",
    "employer_state_id_number": "box_15_employer_state_id_number",
    "state_wages_tips_etc": "box_16_state_wages_tips_etc",
    "state_income_tax": "box_17_state_income_tax",
    "local_wages_tips_etc": "box_18_local_wages_tips_etc",
    "local_income_tax": "box_19_local_income_tax",
    "locality_name": "box_20_locality_name",
}


def build_w2_document(
    parsed: dict,
    *,
    document_id: str,
    source_filename: str | None,
    source_type: SourceDocumentType,
) -> W2Document:
    """Validate a parsed VLM JSON payload into the canonical W2Document."""

    try:
        return W2Document(
            metadata=W2Metadata(
                document_type="W-2",
                tax_year=2026,
                schema_version=2026,
                document_id=document_id,
                source_filename=source_filename,
                source_file_type=_SOURCE_FILE_TYPES[source_type],
            ),
            employee=Employee.model_validate(_with_default_address(parsed.get("employee"))),
            employer=Employer.model_validate(_with_default_address(parsed.get("employer"))),
            federal_wages_and_taxes=FederalWagesAndTaxes.model_validate(
                parsed.get("federal_wages_and_taxes") or {}
            ),
            box_12_entries=[
                Box12Entry.model_validate(entry) for entry in parsed.get("box_12_entries") or []
            ],
            box_13=Box13Flags.model_validate(parsed.get("box_13") or {}),
            box_14_entries=[
                Box14Entry.model_validate(entry) for entry in parsed.get("box_14_entries") or []
            ],
            tipped_occupation_codes=[
                TippedOccupationCode.model_validate(entry)
                for entry in parsed.get("tipped_occupation_codes") or []
            ],
            state_local_entries=[
                StateLocalEntry.model_validate(_normalize_state_local_entry(entry))
                for entry in parsed.get("state_local_entries") or []
            ],
        )
    except ValidationError as exc:
        raise SchemaValidationError(
            f"Model output failed canonical W2Document validation: {exc}"
        ) from exc


def _with_default_address(section: dict | None) -> dict:
    """Default a missing `address` key to `{}` (an all-null Address).

    `Employee.address`/`Employer.address` are required fields with no
    default, unlike every other field on those models, so a model response
    that omits the key entirely (rather than returning an all-null address
    object) would otherwise fail validation for a structural omission the
    model was never asked to avoid.
    """

    section = dict(section or {})
    section.setdefault("address", {})
    return section


def _normalize_state_local_entry(entry: dict) -> dict:
    """Rename known non-prefixed key variants to their canonical box-N name.

    Only renames keys the model actually used the alias for; a response that
    already used the canonical `box_15_state`-style key is left untouched.
    """

    return {_STATE_LOCAL_KEY_ALIASES.get(key, key): value for key, value in entry.items()}
