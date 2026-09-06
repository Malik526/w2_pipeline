"""Phase 8C.7: combine the Phase 8C.5 and 8C.6 `employer.name` signals.

Offline evaluation only -- nothing here is wired into
`w2_pipeline.validation`. This module contains pure combination logic
over two already-computed booleans; it does not itself compute either
signal (that remains Phase 8C.5's `employer_name_heuristics.py` and
Phase 8C.6's `employer_name_layout_signals.py`, unmodified) and it takes
no ground truth as input anywhere, by construction -- every function here
accepts only the two signal booleans (or a list of already-classified
rows), never a predicted/expected value pair.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class AgreementState(str, Enum):
    """Which of the two independent signals fired for one document."""

    NEITHER = "neither"
    ADDRESS_ONLY = "address_only"
    LAYOUT_ONLY = "layout_only"
    BOTH = "both"


def classify_agreement(address_signal: bool, layout_signal: bool) -> AgreementState:
    if address_signal and layout_signal:
        return AgreementState.BOTH
    if address_signal:
        return AgreementState.ADDRESS_ONLY
    if layout_signal:
        return AgreementState.LAYOUT_ONLY
    return AgreementState.NEITHER


def combine_or(address_signal: bool, layout_signal: bool) -> bool:
    return address_signal or layout_signal


def combine_and(address_signal: bool, layout_signal: bool) -> bool:
    return address_signal and layout_signal


@dataclass(frozen=True)
class SignalRow:
    """One document's already-computed signals and correctness label.

    `correct` is consulted only by `_confusion_matrix` below, and only
    ever to score a flag decision that has already been made -- it is
    never an input to `classify_agreement`, `combine_or`, or
    `combine_and`.
    """

    document_id: str
    variant_id: str
    address_signal: bool
    layout_signal: bool
    correct: bool


def confusion_matrix(rows: list[SignalRow], *, flag_key: str) -> dict[str, Any]:
    """Score one flagging strategy (`"address"`, `"layout"`, `"or"`, `"and"`) against correctness."""

    flag_fn = {
        "address": lambda row: row.address_signal,
        "layout": lambda row: row.layout_signal,
        "or": lambda row: combine_or(row.address_signal, row.layout_signal),
        "and": lambda row: combine_and(row.address_signal, row.layout_signal),
    }[flag_key]

    true_positive = [row for row in rows if not row.correct and flag_fn(row)]
    false_negative = [row for row in rows if not row.correct and not flag_fn(row)]
    false_positive = [row for row in rows if row.correct and flag_fn(row)]
    true_negative = [row for row in rows if row.correct and not flag_fn(row)]

    erroneous_total = len(true_positive) + len(false_negative)
    correct_total = len(false_positive) + len(true_negative)
    flagged_total = len(true_positive) + len(false_positive)

    return {
        "true_positives": len(true_positive),
        "false_negatives": len(false_negative),
        "false_positives": len(false_positive),
        "true_negatives": len(true_negative),
        "recall": _ratio(len(true_positive), erroneous_total),
        "precision": _ratio(len(true_positive), flagged_total),
        "false_review_rate": _ratio(len(false_positive), correct_total),
        "specificity": _ratio(len(true_negative), correct_total),
        "false_positive_document_ids": sorted(f"{row.document_id}::{row.variant_id}" for row in false_positive),
        "false_negative_document_ids": sorted(f"{row.document_id}::{row.variant_id}" for row in false_negative),
    }


def agreement_state_counts(rows: list[SignalRow]) -> dict[str, int]:
    counts = {state.value: 0 for state in AgreementState}
    for row in rows:
        counts[classify_agreement(row.address_signal, row.layout_signal).value] += 1
    return counts


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None
