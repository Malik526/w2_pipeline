"""Deterministic semantic comparison for canonical W-2 documents."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.models import (
    DocumentEvaluation,
    EvaluationFailureKind,
    EvaluationIssue,
    FieldEvaluation,
)

DEFAULT_EXCLUDED_PATHS = frozenset(
    {
        "metadata.document_id",
        "metadata.source_filename",
        "metadata.source_file_type",
    }
)
DEFAULT_EXCLUDED_PREFIXES = ("field_observations",)


def flatten_w2_document(
    document: W2Document,
    *,
    excluded_paths: frozenset[str] = DEFAULT_EXCLUDED_PATHS,
    excluded_prefixes: tuple[str, ...] = DEFAULT_EXCLUDED_PREFIXES,
) -> dict[str, Any]:
    """Flatten a canonical W-2 into stable semantic field paths.

    Repeated fields are compared by index. The canonical contract currently
    preserves repeated visual lines as ordered lists, and Phase 3 keeps that
    strategy explicit rather than introducing fuzzy matching before extractors
    exist.
    """

    flattened: dict[str, Any] = {}
    payload = document.model_dump(mode="python")
    _flatten_value(
        payload,
        prefix="",
        flattened=flattened,
        excluded_paths=excluded_paths,
        excluded_prefixes=excluded_prefixes,
    )
    return flattened


def compare_w2_documents(
    *,
    expected: W2Document,
    predicted: W2Document,
    sample_id: str,
    variant_id: str,
    pipeline_id: str | None = None,
) -> DocumentEvaluation:
    """Compare two canonical W-2 documents and calculate field accuracy."""

    expected_fields = flatten_w2_document(expected)
    predicted_fields = flatten_w2_document(predicted)
    field_paths = sorted(set(expected_fields) | set(predicted_fields))

    field_evaluations: list[FieldEvaluation] = []
    failures: list[EvaluationIssue] = []

    for field_path in field_paths:
        expected_has_value = field_path in expected_fields
        predicted_has_value = field_path in predicted_fields
        expected_value = expected_fields.get(field_path)
        predicted_value = predicted_fields.get(field_path)
        failure_kind = _failure_kind(
            expected_has_value=expected_has_value,
            predicted_has_value=predicted_has_value,
            expected_value=expected_value,
            predicted_value=predicted_value,
        )

        correct = failure_kind is None
        field_evaluation = FieldEvaluation(
            field_path=field_path,
            expected=expected_value,
            predicted=predicted_value,
            correct=correct,
            failure_kind=failure_kind,
        )
        field_evaluations.append(field_evaluation)

        if failure_kind is not None:
            failures.append(
                EvaluationIssue(
                    kind=failure_kind,
                    field_path=field_path,
                    expected=expected_value,
                    predicted=predicted_value,
                )
            )

    total_fields = len(field_evaluations)
    correct_fields = sum(field.correct for field in field_evaluations)
    field_accuracy = correct_fields / total_fields if total_fields else 0.0

    return DocumentEvaluation(
        sample_id=sample_id,
        variant_id=variant_id,
        tax_year=expected.metadata.tax_year,
        pipeline_id=pipeline_id,
        total_fields=total_fields,
        correct_fields=correct_fields,
        field_accuracy=field_accuracy,
        field_evaluations=field_evaluations,
        failures=failures,
    )


def _flatten_value(
    value: Any,
    *,
    prefix: str,
    flattened: dict[str, Any],
    excluded_paths: frozenset[str],
    excluded_prefixes: tuple[str, ...],
) -> None:
    if prefix and _is_excluded(prefix, excluded_paths, excluded_prefixes):
        return

    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python")

    if isinstance(value, Mapping):
        for key in sorted(value):
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            _flatten_value(
                value[key],
                prefix=next_prefix,
                flattened=flattened,
                excluded_paths=excluded_paths,
                excluded_prefixes=excluded_prefixes,
            )
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            _flatten_value(
                item,
                prefix=f"{prefix}[{index}]",
                flattened=flattened,
                excluded_paths=excluded_paths,
                excluded_prefixes=excluded_prefixes,
            )
        return

    if not prefix:
        return
    flattened[prefix] = _normalize_value(value)


def _is_excluded(
    path: str,
    excluded_paths: frozenset[str],
    excluded_prefixes: tuple[str, ...],
) -> bool:
    return path in excluded_paths or any(
        path == prefix or path.startswith(f"{prefix}.") or path.startswith(f"{prefix}[")
        for prefix in excluded_prefixes
    )


def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Decimal):
        return value.normalize()
    if isinstance(value, Enum):
        return value.value
    return value


def _failure_kind(
    *,
    expected_has_value: bool,
    predicted_has_value: bool,
    expected_value: Any,
    predicted_value: Any,
) -> EvaluationFailureKind | None:
    if not expected_has_value:
        return EvaluationFailureKind.UNEXPECTED
    if not predicted_has_value:
        return EvaluationFailureKind.MISSING
    if expected_value is not None and predicted_value is None:
        return EvaluationFailureKind.MISSING
    if expected_value != predicted_value:
        return EvaluationFailureKind.MISMATCH
    return None
