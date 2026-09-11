"""Phase 8D.8A: recognition-confidence residual error audit (evaluation-side).

Answers one narrow question: can native PaddleOCR recognition confidence
separate the two known residual OCR-substitution errors (`Ave` -> `Áve` on
`symage_900027`, `S` -> `Š` on `symage_900061`) from correct OCR-derived
fields well enough, composed with the *existing* production validator at
document-routing level, to justify a future promotion experiment?

This module is pure and read-only: no OCR, no parser, no validator, no
routing code is touched. It only consumes `field_confidence.FieldConfidenceMatch`
results (Phase 8C.4) and a document's real validator status, and reports
what a candidate confidence-based routing rule would do -- never applies one.

## `selected` confidence -- a strict definition, not a guess

`field_confidence_signal` reports four confidence views for a field:
`min`, `mean`, `max` (already provided by `field_confidence.summarize_confidences`)
and `selected`. `selected` is the confidence of *the exact contributing
observation* that became the field's value, and it is only ever populated
when exactly one observation contributed
(`contributing_observation_count == 1`) and that observation had a real
`ocr_confidence`. In every other case -- zero contributing observations
(unmatched), more than one (a merged/multi-run match, where no
sub-observation confidence exists to attribute), or a single observation
with no recorded OCR confidence (native PDF text) -- `selected` is `None`
and `selected_reason` records why. It never silently falls back to
min/mean/first of the window; a caller who wants an aggregate over an
ambiguous window uses `min`/`mean` explicitly, never `selected`.
"""

from __future__ import annotations

import math
from typing import Any, Literal

from w2_pipeline.evaluation.field_confidence import (
    CONFIDENCE_ANALYSIS_FIELD_PATHS,
    FieldConfidenceMatch,
    summarize_confidences,
)

Aggregation = Literal["selected", "min", "mean"]

# The canonical `Address` model (src/w2_pipeline/contracts/w2.py) has 6
# subfields per address block: address_line_1, address_line_2, city, state,
# postal_code, country. Only 5 are covered here for both employee and
# employer -- `address_line_2` is deliberately excluded for both: every
# manifest entry's `evaluated_field_paths` (confirmed by direct inspection
# of data/evaluation/external/symage-synthetic-us-forms-preview-final/manifest.jsonl)
# lists `{employee,employer}.address.{address_line_1,city,state,postal_code,country}`
# but never `address_line_2` -- no ground truth is evaluated for it in this
# benchmark, so a prediction there has no correct/incorrect label. `country`
# IS included (it is evaluated) even though it is rarely OCR-ambiguous, for
# completeness of the evaluated address surface.
ADDRESS_FIELD_PATHS: tuple[str, ...] = tuple(
    sorted(
        f"{party}.address.{subfield}"
        for party in ("employee", "employer")
        for subfield in ("address_line_1", "city", "state", "postal_code", "country")
    )
)

# Phase 8C.4's 12 fields + this phase's 10 address fields = 22.
# box_13.retirement_plan stays excluded: it is produced by the separate
# pixel-based checkbox detector, not OCR text recognition.
RESIDUAL_AUDIT_FIELD_PATHS: tuple[str, ...] = tuple(
    sorted({*CONFIDENCE_ANALYSIS_FIELD_PATHS, *ADDRESS_FIELD_PATHS})
)


def field_confidence_signal(match: FieldConfidenceMatch) -> dict[str, Any]:
    """Derive the reportable confidence signal for one field's match.

    See module docstring for `selected`'s strict definition.
    """

    summary = summarize_confidences(match.confidences)

    selected: float | None = None
    selected_reason = "ok"
    if not match.matched:
        selected_reason = "unmatched"
    elif match.contributing_observation_count != 1:
        selected_reason = "ambiguous_multi_observation"
    elif not match.confidences:
        selected_reason = "no_ocr_confidence"
    else:
        selected = match.confidences[0]

    return {
        "matched": match.matched,
        "field_value": match.field_value,
        "contributing_observation_count": match.contributing_observation_count,
        "min": summary["min"],
        "mean": summary["mean"],
        "max": summary["max"],
        "count": summary["count"],
        "selected": selected,
        "selected_reason": selected_reason,
    }


def field_would_flag(signal: dict[str, Any], threshold: float, aggregation: Aggregation = "selected") -> bool:
    """Whether one field's confidence would route its document to review.

    A missing confidence value (`None`, for any reason -- unmatched,
    ambiguous, or genuinely absent) never fabricates a routing signal: it
    is reported as not-flagging, never as flagging or passing.
    """

    value = signal.get(aggregation)
    if value is None:
        return False
    return value < threshold


def document_confidence_flag(
    field_signals: dict[str, dict[str, Any]],
    field_paths: tuple[str, ...],
    threshold: float,
    aggregation: Aggregation = "selected",
) -> bool:
    """Whether any in-scope field's confidence would route this document to review."""

    return any(
        field_would_flag(field_signals[field_path], threshold, aggregation)
        for field_path in field_paths
        if field_path in field_signals
    )


def triggering_fields(
    field_signals: dict[str, dict[str, Any]],
    field_paths: tuple[str, ...],
    threshold: float,
    aggregation: Aggregation = "selected",
) -> list[dict[str, Any]]:
    """Every in-scope field whose confidence would flag this document, with its value/confidence.

    Used to explain *why* a document was newly routed to review by the
    candidate rule (Section 13's false-review audit) -- never used to
    decide the routing itself, only to report it.
    """

    triggers = []
    for field_path in field_paths:
        signal = field_signals.get(field_path)
        if signal is None or not field_would_flag(signal, threshold, aggregation):
            continue
        triggers.append(
            {
                "field_path": field_path,
                "field_value": signal.get("field_value"),
                "confidence": signal.get(aggregation),
            }
        )
    return triggers


def compose_route(validator_status: str, confidence_flag: bool) -> str:
    """OR-compose the real validator's decision with a candidate confidence rule."""

    if validator_status == "needs_review" or confidence_flag:
        return "needs_review"
    return "accepted"


def summarize_routing(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Document-level routing metrics for a list of `{has_error, route}` rows.

    Field names and computation deliberately match
    `run_expanded_validator_effectiveness._summarize` so this phase's
    numbers are directly comparable to the Phase 8D.1B baseline.
    """

    total = len(rows)
    erroneous = [row for row in rows if row["has_error"]]
    correct = [row for row in rows if not row["has_error"]]
    needs_review = [row for row in rows if row["route"] == "needs_review"]
    accepted = [row for row in rows if row["route"] != "needs_review"]

    erroneous_reviewed = [row for row in erroneous if row["route"] == "needs_review"]
    erroneous_accepted = [row for row in erroneous if row["route"] != "needs_review"]
    correct_reviewed = [row for row in correct if row["route"] == "needs_review"]
    correct_accepted = [row for row in correct if row["route"] != "needs_review"]

    return {
        "total_documents": total,
        "correct_documents": len(correct),
        "erroneous_documents": len(erroneous),
        "accepted_documents": len(accepted),
        "needs_review_documents": len(needs_review),
        "correct_accepted": len(correct_accepted),
        "correct_routed_needs_review": len(correct_reviewed),
        "erroneous_accepted": len(erroneous_accepted),
        "erroneous_routed_needs_review": len(erroneous_reviewed),
        "error_detection_recall": _ratio(len(erroneous_reviewed), len(erroneous)),
        "false_review_rate": _ratio(len(correct_reviewed), len(correct)),
        "automatic_acceptance_rate": _ratio(len(accepted), total),
        "unsafe_acceptance_rate": _ratio(len(erroneous_accepted), total),
        "review_queue_precision": _ratio(len(erroneous_reviewed), len(needs_review)),
    }


def sweep_thresholds(
    rows: list[dict[str, Any]],
    thresholds: list[float],
    field_paths: tuple[str, ...] = RESIDUAL_AUDIT_FIELD_PATHS,
    aggregation: Aggregation = "selected",
) -> dict[str, Any]:
    """Run a threshold sweep, composing the candidate rule with the real validator.

    Each row must carry: `document_id`, `variant_id`, `has_error`,
    `validator_status` (`"accepted"` or `"needs_review"`), and
    `field_signals` (field_path -> `field_confidence_signal` output).

    Returns the validator-only baseline plus, per threshold, composed
    routing metrics and the specific documents newly routed *only* because
    of the confidence rule (never double-counting documents the validator
    already routed on its own).
    """

    baseline_rows = [{**row, "route": row["validator_status"]} for row in rows]
    baseline_metrics = summarize_routing(baseline_rows)
    baseline_unsafe_accepted = {
        (row["document_id"], row["variant_id"])
        for row in rows
        if row["has_error"] and row["validator_status"] != "needs_review"
    }
    already_routed_by_validator_count = sum(1 for row in rows if row["validator_status"] == "needs_review")

    results = []
    for threshold in thresholds:
        composed_rows = []
        newly_routed_only_by_confidence = []
        for row in rows:
            flag = document_confidence_flag(row["field_signals"], field_paths, threshold, aggregation)
            route = compose_route(row["validator_status"], flag)
            composed_rows.append({**row, "route": route})
            if row["validator_status"] != "needs_review" and flag:
                newly_routed_only_by_confidence.append(
                    {
                        "document_id": row["document_id"],
                        "variant_id": row["variant_id"],
                        "has_error": row["has_error"],
                        "triggering_fields": triggering_fields(
                            row["field_signals"], field_paths, threshold, aggregation
                        ),
                    }
                )

        caught = {
            (row["document_id"], row["variant_id"])
            for row in composed_rows
            if row["has_error"]
            and row["route"] == "needs_review"
            and (row["document_id"], row["variant_id"]) in baseline_unsafe_accepted
        }

        results.append(
            {
                "threshold": threshold,
                "aggregation": aggregation,
                "metrics": summarize_routing(composed_rows),
                "residual_errors_caught": len(caught),
                "residual_error_ids_caught": sorted(f"{doc}::{variant}" for doc, variant in caught),
                "newly_routed_only_by_confidence_count": len(newly_routed_only_by_confidence),
                "newly_routed_only_by_confidence": newly_routed_only_by_confidence,
                "already_routed_by_validator_count": already_routed_by_validator_count,
            }
        )

    return {
        "field_paths": list(field_paths),
        "aggregation": aggregation,
        "baseline_validator_only": baseline_metrics,
        "baseline_unsafe_accepted_count": len(baseline_unsafe_accepted),
        "thresholds": results,
    }


def non_ascii_field_values(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Section 14: OCR-derived field values containing non-ASCII characters.

    Reports both correct and incorrect occurrences (a caller filters by
    `correct` downstream) -- purpose is understanding whether a future
    confidence rule would disproportionately route legitimate accented
    text, not producing a routing decision itself.
    """

    results = []
    for row in rows:
        failing = set(row.get("failing_field_paths", []))
        for field_path, signal in row["field_signals"].items():
            value = signal.get("field_value")
            if not value or value.isascii():
                continue
            results.append(
                {
                    "document_id": row["document_id"],
                    "variant_id": row["variant_id"],
                    "field_path": field_path,
                    "field_value": value,
                    "correct": field_path not in failing,
                    "selected": signal.get("selected"),
                    "min": signal.get("min"),
                    "mean": signal.get("mean"),
                }
            )
    return results


def percentile(values: list[float], pct: float) -> float | None:
    """Linear-interpolation percentile (`pct` in `[0, 100]`); `None` if empty."""

    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (pct / 100)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[int(rank)]
    return ordered[lower] * (upper - rank) + ordered[upper] * (rank - lower)


def distribution_summary(values: list[float]) -> dict[str, Any]:
    """N/min/p1/p5/median/mean/max over a list of confidence values."""

    if not values:
        return {"n": 0, "min": None, "p1": None, "p5": None, "median": None, "mean": None, "max": None}
    return {
        "n": len(values),
        "min": min(values),
        "p1": percentile(values, 1),
        "p5": percentile(values, 5),
        "median": percentile(values, 50),
        "mean": sum(values) / len(values),
        "max": max(values),
    }


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None
