"""Safe by-path read/write access to a canonical W2Document.

Corrections address a field by the same dotted, index-bracketed path
convention the evaluator already uses for comparison
(`w2_pipeline.evaluation.comparison.flatten_w2_document`), e.g.
`employee.ssn` or `box_12_entries[0].code`. Only paths that resolve
against the document's own declared structure are ever accepted --
`W2Document`'s `extra="forbid"` config means an unknown key cannot appear
in `model_dump()` output at all, so navigating one naturally rejects it.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import ValidationError

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.review.errors import CorrectionValidationError, InvalidFieldPathError

_SEGMENT_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)(?:\[(\d+)\])?$")


def get_field(document: W2Document, field_path: str) -> Any:
    """Return the current value at `field_path`.

    Raises `InvalidFieldPathError` if the path does not resolve.
    """

    node: Any = document.model_dump(mode="python")
    for name, index in _parse_path(field_path):
        node = _step(node, name, index, field_path)
    return node


def set_field_value(document: W2Document, field_path: str, new_value: Any) -> W2Document:
    """Return a NEW `W2Document` with `field_path` set to `new_value`.

    Never mutates `document`. Raises `InvalidFieldPathError` if the path
    does not resolve, or `CorrectionValidationError` if `new_value` fails
    canonical validation for that field.
    """

    segments = _parse_path(field_path)
    data = document.model_dump(mode="python")
    node: Any = data
    for name, index in segments[:-1]:
        node = _step(node, name, index, field_path)

    last_name, last_index = segments[-1]
    container = _step_into_container(node, last_name, field_path)
    if last_index is not None:
        if not isinstance(container, list) or not (0 <= last_index < len(container)):
            raise InvalidFieldPathError(
                f"Field path {field_path!r} has an out-of-range list index."
            )
        container[last_index] = new_value
    else:
        node[last_name] = new_value

    try:
        return W2Document.model_validate(data)
    except ValidationError as exc:
        raise CorrectionValidationError(
            f"New value for {field_path!r} failed canonical validation: {exc}"
        ) from exc


def _parse_path(field_path: str) -> list[tuple[str, int | None]]:
    if not field_path:
        raise InvalidFieldPathError("Field path must not be empty.")
    segments: list[tuple[str, int | None]] = []
    for part in field_path.split("."):
        match = _SEGMENT_RE.match(part)
        if not match:
            raise InvalidFieldPathError(f"Field path {field_path!r} is not well-formed.")
        name, index = match.groups()
        segments.append((name, int(index) if index is not None else None))
    return segments


def _step(node: Any, name: str, index: int | None, field_path: str) -> Any:
    container = _step_into_container(node, name, field_path)
    if index is None:
        return container
    if not isinstance(container, list) or not (0 <= index < len(container)):
        raise InvalidFieldPathError(f"Field path {field_path!r} has an out-of-range list index.")
    return container[index]


def _step_into_container(node: Any, name: str, field_path: str) -> Any:
    if not isinstance(node, dict) or name not in node:
        raise InvalidFieldPathError(f"Field path {field_path!r} does not exist on W2Document.")
    return node[name]
