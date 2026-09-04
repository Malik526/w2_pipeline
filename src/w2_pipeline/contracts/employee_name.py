"""Helpers for canonical Employee name semantics."""

from __future__ import annotations

from dataclasses import dataclass
import re

_SUFFIXES = {"JR", "SR", "II", "III", "IV", "V"}


@dataclass(frozen=True)
class ParsedEmployeeName:
    """Employee name split into the canonical W-2 name fields."""

    first_name: str | None
    middle_initial: str | None
    last_name: str | None
    suffix: str | None


def split_first_name_and_initial(value: str) -> tuple[str | None, str | None]:
    """Split Form W-2 Box e's first-name-and-initial region."""

    parts = _name_parts(value)
    if not parts:
        return None, None
    if len(parts) >= 2 and _is_middle_initial(parts[-1]):
        return " ".join(parts[:-1]) or None, _normalize_initial(parts[-1])
    return " ".join(parts), None


def parse_employee_name(value: str) -> ParsedEmployeeName:
    """Parse a full employee display name into canonical name fields."""

    parts = _name_parts(value)
    if not parts:
        return ParsedEmployeeName(None, None, None, None)

    suffix = None
    if _is_suffix(parts[-1]):
        suffix = parts[-1]
        parts = parts[:-1]

    if not parts:
        return ParsedEmployeeName(None, None, None, suffix)
    if len(parts) == 1:
        return ParsedEmployeeName(parts[0], None, None, suffix)
    if len(parts) == 2:
        return ParsedEmployeeName(parts[0], None, parts[1], suffix)

    middle_initial = (
        _normalize_initial(parts[1]) if _is_middle_initial(parts[1]) else None
    )
    last_start = 2 if middle_initial is not None else 1
    return ParsedEmployeeName(
        first_name=parts[0],
        middle_initial=middle_initial,
        last_name=" ".join(parts[last_start:]) or None,
        suffix=suffix,
    )


def _name_parts(value: str) -> list[str]:
    return [part for part in re.split(r"\s+", value.strip()) if part]


def _is_middle_initial(value: str) -> bool:
    token = value.rstrip(".")
    return len(token) == 1 and token.isalpha() and token.isupper()


def _normalize_initial(value: str) -> str:
    return value.rstrip(".")


def _is_suffix(value: str) -> bool:
    return value.rstrip(".").upper() in _SUFFIXES
