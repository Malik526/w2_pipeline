"""Phase 8: measure how well Phase 6 validation detects real extraction errors.

This is an EVALUATION-side analysis, not a validation-side one: it lives
under `w2_pipeline.evaluation` (which is allowed to know about ground
truth) and calls into `w2_pipeline.validation.validate_w2_document` as an
ordinary one-way consumer -- the validation package itself still never
imports anything from here or from `w2_pipeline.evaluation` generally
(`tests/validation/test_isolation.py` continues to enforce that).

Critical ordering, enforced by this module's structure and covered by
`tests/evaluation/test_validator_effectiveness.py`:

    reconstructed PREDICTED document
        -> validate_w2_document()      <- ground truth never passed in here
        -> accepted / needs_review
        -> THEN, and only then, compared against ground truth-derived
           "was this document actually erroneous?" to score the decision

Ground truth is used exclusively for that final scoring step. It is never
an input to `validate_w2_document`.

Since no full predicted `W2Document` was ever persisted from a historical
Pipeline A benchmark run (only the field-level failures were, in each
committed `data/evaluation/results/*.json` artifact), this module
reconstructs an equivalent predicted document from ground truth plus the
benchmark's own recorded `field_failures`: every field path NOT mentioned
in `field_failures` is, by construction, exactly equal to ground truth
(the evaluator only ever records a failure where predicted != expected),
so overlaying just the recorded failures onto a copy of ground truth
reproduces the real prediction exactly for every field the original
`compare_w2_documents` call scored. No OCR/VLM inference is re-run.

## The `employer.name` confound

Running this analysis for the first time immediately reproduced the
Phase 6B finding at scale: the Symage external ground truth has
`employer.name = null` for every record (never authoritatively mapped
from the FUNSD annotations -- `docs/experiments/phase6b-employer-name-investigation.md`),
and that field is required by Phase 6 (`docs/contracts/validation-and-routing.md`).
Since this module's reconstructed documents inherit `employer.name` from
ground truth for every document (that field is never in
`evaluated_field_paths`, so it never appears in `field_failures`, so the
reconstruction never overrides it), *every* reconstructed document trips
`required_field_missing` on `employer.name` regardless of whether the
rest of the document was extracted correctly -- a single already-
understood ground-truth mapping gap, not a signal about real extraction
quality or validator behavior. Reporting raw numbers without accounting
for this would make every benchmark's "false review rate" read as 100%,
which is not a meaningful measurement. This module therefore reports both
the raw numbers and an adjusted view that excludes exactly this one
known, already-documented field from the required-field check -- nothing
else -- so the analysis measures real error-detection behavior. This
adjustment is scoped to this evaluation-side script only; it does not
change the shipped Phase 6 `validate_w2_document` behavior at all.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.manifest import load_manifest_jsonl
from w2_pipeline.review.errors import CorrectionValidationError, InvalidFieldPathError
from w2_pipeline.review.field_paths import set_field_value
from w2_pipeline.validation.models import ValidationIssue, ValidationSeverity, ValidationStatus
from w2_pipeline.validation.validator import validate_w2_document

# The one known, already-documented Symage ground-truth mapping gap (see
# the module docstring). Excluded from the "adjusted" metrics only.
KNOWN_GROUND_TRUTH_GAPS: frozenset[str] = frozenset({"employer.name"})


def reconstruct_predicted_document(
    ground_truth: W2Document, field_failures: list[dict[str, Any]]
) -> tuple[W2Document, list[str]]:
    """Rebuild the real prediction from ground truth plus recorded failures.

    Returns `(predicted_document, skipped_field_paths)`. A field failure is
    skipped (and its path recorded) when it cannot be cleanly re-applied to
    a fixed-shape document -- `unexpected`-kind failures (a predicted field
    path with no corresponding ground-truth position, e.g. an extra
    repeated entry the prediction added) and any failure whose path or
    coerced value the canonical schema itself rejects. Skips are rare and
    are surfaced rather than silently dropped so a caller can audit how
    much of a given benchmark run is exactly reconstructable.
    """

    document = ground_truth
    skipped: list[str] = []
    for failure in field_failures:
        if failure.get("failure_kind") == "unexpected":
            skipped.append(failure["field_path"])
            continue
        try:
            document = set_field_value(document, failure["field_path"], failure.get("predicted"))
        except (InvalidFieldPathError, CorrectionValidationError):
            skipped.append(failure["field_path"])
    return document, skipped


def _status_excluding_known_gaps(
    issues: list[ValidationIssue], known_gaps: frozenset[str]
) -> str:
    remaining = [
        issue
        for issue in issues
        if not (issue.code == "required_field_missing" and issue.field_path in known_gaps)
    ]
    has_error = any(issue.severity == ValidationSeverity.ERROR for issue in remaining)
    return ValidationStatus.NEEDS_REVIEW.value if has_error else ValidationStatus.ACCEPTED.value


def measure_validator_effectiveness(
    *,
    result_json_path: str | Path,
    manifest_path: str | Path,
    variant_id: str | None = None,
    limit: int | None = None,
    known_ground_truth_gaps: frozenset[str] = KNOWN_GROUND_TRUTH_GAPS,
) -> dict[str, Any]:
    """Score Phase 6 validation's routing decisions against a real benchmark run.

    `result_json_path` is a committed Pipeline A/B benchmark summary (e.g.
    `data/evaluation/results/phase4e_tesseract_capital_e_fix_rotated_150.json`).
    `manifest_path` is the manifest that produced it -- used only to look
    up each document's `ground_truth_path`, never passed to the validator.
    `variant_id` narrows a multi-variant result (e.g. a 600-document
    all-variants run) to just one variant; omit it for a single-variant
    result, where the result's own `variant_scope` already names one.
    """

    result = json.loads(Path(result_json_path).read_text(encoding="utf-8"))
    manifest = load_manifest_jsonl(Path(manifest_path))
    base_dir = Path(manifest_path).parent

    variant_scope = set(result.get("benchmark_metadata", {}).get("variant_scope") or [])
    if variant_id is not None:
        variant_scope &= {variant_id}
    entries = [entry for entry in manifest.entries if entry.variant_id in variant_scope]
    if limit is not None:
        entries = entries[:limit]

    failures_by_document: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for failure in result.get("field_failures", []):
        if variant_id is not None and failure["variant_id"] != variant_id:
            continue
        failures_by_document[(failure["document_id"], failure["variant_id"])].append(failure)

    rows: list[dict[str, Any]] = []
    for entry in entries:
        key = (entry.sample_id, entry.variant_id)
        document_failures = failures_by_document.get(key, [])
        ground_truth = W2Document.model_validate_json(
            (base_dir / entry.ground_truth_path).read_text(encoding="utf-8")
        )
        predicted, skipped = reconstruct_predicted_document(ground_truth, document_failures)

        # The validator sees ONLY the reconstructed prediction.
        validation_result = validate_w2_document(predicted)

        # Ground truth is consulted here, after validation already ran,
        # purely to label whether this document was actually erroneous.
        has_error = len(document_failures) > 0

        rows.append(
            {
                "sample_id": entry.sample_id,
                "variant_id": entry.variant_id,
                "has_error": has_error,
                "error_field_count": len(document_failures),
                "validation_status_raw": validation_result.status.value,
                "validation_status_adjusted": _status_excluding_known_gaps(
                    validation_result.issues, known_ground_truth_gaps
                ),
                "validation_issue_codes": sorted({issue.code for issue in validation_result.issues}),
                "skipped_field_paths": skipped,
            }
        )

    return {
        "source_result_json": str(result_json_path),
        "known_ground_truth_gaps_excluded_in_adjusted_view": sorted(known_ground_truth_gaps),
        "raw": _summarize(rows, status_key="validation_status_raw"),
        "adjusted_for_known_ground_truth_gaps": _summarize(
            rows, status_key="validation_status_adjusted"
        ),
        "rows": rows,
    }


def _summarize(rows: list[dict[str, Any]], *, status_key: str) -> dict[str, Any]:
    total = len(rows)
    erroneous = [row for row in rows if row["has_error"]]
    correct = [row for row in rows if not row["has_error"]]
    caught = [row for row in erroneous if row[status_key] == "needs_review"]
    missed = [row for row in erroneous if row[status_key] == "accepted"]
    false_review = [row for row in correct if row[status_key] == "needs_review"]
    true_accept = [row for row in correct if row[status_key] == "accepted"]
    accepted_total = [row for row in rows if row[status_key] == "accepted"]

    return {
        "total_documents": total,
        "erroneous_documents": len(erroneous),
        "correct_documents": len(correct),
        "erroneous_caught_needs_review": len(caught),
        "erroneous_missed_accepted": len(missed),
        "correct_flagged_needs_review": len(false_review),
        "correct_accepted": len(true_accept),
        "error_detection_recall": _ratio(len(caught), len(erroneous)),
        "false_review_rate": _ratio(len(false_review), len(correct)),
        "automatic_acceptance_rate": _ratio(len(accepted_total), total),
        "missed_erroneous_document_ids": sorted({row["sample_id"] for row in missed}),
    }


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_json_path", type=Path)
    parser.add_argument("manifest_path", type=Path)
    parser.add_argument("--variant-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument(
        "--no-rows",
        action="store_true",
        help="Omit the per-document row detail from the printed/saved summary.",
    )
    args = parser.parse_args(argv)

    summary = measure_validator_effectiveness(
        result_json_path=args.result_json_path,
        manifest_path=args.manifest_path,
        variant_id=args.variant_id,
        limit=args.limit,
    )
    if args.no_rows:
        summary = {key: value for key, value in summary.items() if key != "rows"}

    text = json.dumps(summary, indent=2, sort_keys=True)
    print(text)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
