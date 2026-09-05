"""PII redaction for validation issue diagnostics.

W-2s carry highly sensitive PII. When a rule needs to attach the offending
value to a `ValidationIssue` for human review, this module ensures known
PII-bearing canonical field paths are never included in the clear:
SSN/EIN are format-preserving masked (only the last 4 characters survive,
useful for a reviewer to spot-check which record an issue refers to
without exposing the full number); names and address lines are fully
replaced with a placeholder, since a partial name/address mask offers
little diagnostic value and no standard partial form.
"""

from __future__ import annotations

from typing import Any

REDACTED_PLACEHOLDER = "[REDACTED]"

_MASK_LAST_DIGITS_PATHS = frozenset({"employee.ssn", "employer.ein"})

_FULLY_REDACTED_PATHS = frozenset(
    {
        "employee.first_name",
        "employee.middle_initial",
        "employee.last_name",
        "employee.suffix",
        "employee.address.address_line_1",
        "employee.address.address_line_2",
        "employee.address.city",
        "employee.address.postal_code",
        "employer.name",
        "employer.address.address_line_1",
        "employer.address.address_line_2",
        "employer.address.city",
        "employer.address.postal_code",
        "employer.control_number",
    }
)


def is_sensitive_field(field_path: str) -> bool:
    """Return whether `field_path` names a known PII-bearing canonical field."""

    return field_path in _MASK_LAST_DIGITS_PATHS or field_path in _FULLY_REDACTED_PATHS


def redact_value(field_path: str, value: Any) -> Any:
    """Redact `value` if `field_path` is a known PII-bearing field.

    `None` is passed through unchanged (absence is not PII). Values for
    fields outside the known-sensitive set are also passed through
    unchanged -- this function only redacts, it never invents a value.
    """

    if value is None:
        return None
    if field_path in _MASK_LAST_DIGITS_PATHS and isinstance(value, str):
        return _mask_all_but_last_digits(value, keep=4)
    if field_path in _FULLY_REDACTED_PATHS:
        return REDACTED_PLACEHOLDER
    return value


def _mask_all_but_last_digits(value: str, *, keep: int) -> str:
    """Replace all but the last `keep` digits with `*`, preserving separators."""

    digit_indexes = [index for index, char in enumerate(value) if char.isdigit()]
    mask_indexes = set(digit_indexes[:-keep]) if len(digit_indexes) > keep else set()
    return "".join("*" if index in mask_indexes else char for index, char in enumerate(value))
