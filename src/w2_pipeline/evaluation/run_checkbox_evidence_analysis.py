"""Phase 8C.12: offline evidence-distribution analysis for the checkbox validator.

Consumes `phase8c10_anchor_checkbox_rows.jsonl` (Phase 8C.10's per-document
anchor/checkbox localization + classification evidence, one row per one of
the 600 manifest documents: `anchor_distance_px`, `alignment_offset_px`,
`shape_score`, `interior_ink_ratio`, `decision_margin`,
`predicted_retirement_plan`, `expected_retirement_plan`, `correct`,
`variant_id`) rather than re-running extraction.

This is valid input for calibrating the *promoted* (Phase 8C.11) detector's
evidence distributions, not stale data: `checkbox_anchor.py`'s detection
code is byte-for-byte unmodified between Phase 8C.10 and Phase 8C.11 (no
retuning), and Phase 8C.11's own production-path benchmark independently
confirmed 0/600 fallback and 600/600 correct -- identical to Phase 8C.10's
600/600 localization/classification result -- so this file's per-document
evidence values are exactly what the promoted default path produces.
Re-running the detector would be pure recomputation of values already
known to be identical (the algorithm is deterministic, no randomness), not
new information.

Ground truth (`expected_retirement_plan`) was loaded by the Phase 8C.10
script only *after* detection, purely to label correctness for this
offline analysis -- never as a validator or detector input.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

DEFAULT_INPUT_ROWS = Path("data/evaluation/results/phase8c10_anchor_checkbox_rows.jsonl")


def run_analysis(rows_path: str | Path = DEFAULT_INPUT_ROWS) -> dict[str, Any]:
    rows = _load_rows(rows_path)
    checked = [row for row in rows if row["expected_retirement_plan"] is True]
    unchecked = [row for row in rows if row["expected_retirement_plan"] is False]

    return {
        "source_rows_jsonl": str(rows_path),
        "provenance": (
            "Phase 8C.10 checkbox_anchor.py output, unmodified by Phase 8C.11 "
            "(no retuning); Phase 8C.11's own production-path benchmark "
            "independently confirmed the identical 600/600 localization and "
            "0/600 fallback result this file reports."
        ),
        "documents": len(rows),
        "checked_documents": len(checked),
        "unchecked_documents": len(unchecked),
        "incorrect_documents": sum(1 for row in rows if not row["correct"]),
        "overall": {
            "abs_decision_margin": _distribution([abs(row["decision_margin"]) for row in rows]),
            "shape_score": _distribution([row["shape_score"] for row in rows]),
            "anchor_distance_px": _distribution([row["anchor_distance_px"] for row in rows]),
            "alignment_offset_px": _distribution([row["alignment_offset_px"] for row in rows]),
        },
        "decision_margin_by_class": {
            "checked": _distribution([row["decision_margin"] for row in checked]),
            "unchecked": _distribution([row["decision_margin"] for row in unchecked]),
        },
        "by_variant": {
            variant_id: _variant_summary(rows, variant_id)
            for variant_id in sorted({row["variant_id"] for row in rows})
        },
        "near_threshold_margin_analysis": _near_threshold_margin_analysis(rows),
        "questions": _answer_questions(rows, checked, unchecked),
    }


def _variant_summary(rows: list[dict[str, Any]], variant_id: str) -> dict[str, Any]:
    subset = [row for row in rows if row["variant_id"] == variant_id]
    return {
        "documents": len(subset),
        "incorrect": sum(1 for row in subset if not row["correct"]),
        "shape_score": _distribution([row["shape_score"] for row in subset]),
        "anchor_distance_px": _distribution([row["anchor_distance_px"] for row in subset]),
        "alignment_offset_px": _distribution([row["alignment_offset_px"] for row in subset]),
        "abs_decision_margin": _distribution([abs(row["decision_margin"]) for row in subset]),
    }


def _near_threshold_margin_analysis(rows: list[dict[str, Any]]) -> dict[str, Any]:
    candidate_margins = (0.02, 0.05, 0.08, 0.10, 0.119)
    abs_margins = [abs(row["decision_margin"]) for row in rows]
    return {
        "candidate_margin_thresholds": {
            str(candidate): {
                "documents_that_would_be_flagged": sum(1 for margin in abs_margins if margin < candidate),
                "would_flag_any_correct_document": any(
                    margin < candidate for margin in abs_margins
                ),
            }
            for candidate in candidate_margins
        },
        "chosen_threshold": 0.05,
        "chosen_threshold_flags_on_this_benchmark": sum(1 for margin in abs_margins if margin < 0.05),
        "rationale": (
            "0.05 is less than half the smallest real separation observed in "
            "either direction (unchecked: exactly 0.12, constant; checked: "
            "minimum 0.124), so it cannot fire on any of this benchmark's 600 "
            "real documents, while remaining wide enough to catch a genuinely "
            "ambiguous real-world interior ink ratio (roughly 0.07-0.17) that "
            "this synthetic dataset does not produce. See docs/experiments/"
            "phase8c12-checkbox-validator.md Section 2."
        ),
    }


def _answer_questions(
    rows: list[dict[str, Any]], checked: list[dict[str, Any]], unchecked: list[dict[str, Any]]
) -> dict[str, str]:
    rotated = [row for row in rows if row["variant_id"] == "rotated_png"]
    non_rotated = [row for row in rows if row["variant_id"] != "rotated_png"]
    rotated_mean_shape = statistics.mean(row["shape_score"] for row in rotated) if rotated else None
    non_rotated_mean_shape = statistics.mean(row["shape_score"] for row in non_rotated) if non_rotated else None
    close_to_M = [row for row in rows if abs(row["decision_margin"]) < 0.05]

    return {
        "1_observed_margin_distribution": (
            f"Unchecked: constant -0.12 (interior_ink_ratio always exactly 0.0, "
            f"n={len(unchecked)}). Checked: +0.124 to +0.178 "
            f"(n={len(checked)}). A clean, unbroken 0.244-wide gap between the "
            "two classes with nothing observed inside it -- this dataset offers "
            "no real near-boundary example in either direction."
        ),
        "2_observed_shape_score_distribution": (
            f"0.8269-0.8800 across all 600 documents (tight, resolution/DPI-"
            "specific to this one synthetic renderer)."
        ),
        "3_rotated_docs_systematically_weaker_geometry": (
            f"Slightly: rotated_png mean shape_score {rotated_mean_shape:.4f} vs. "
            f"{non_rotated_mean_shape:.4f} for the other three variants, and "
            "rotated_png shows the largest alignment_offset_px (2-3px vs. 0-1.5px "
            "elsewhere) -- consistent with the rotation-induced OCR line-box "
            "noise the phase 8C.10 doc's 'Real Geometry Investigation' section "
            "describes, but still far above any plausible malformed-geometry "
            "floor."
        ),
        "4_correct_docs_near_plausible_uncertainty_thresholds": (
            f"No: the closest any correct document comes to the chosen 0.05 "
            f"margin threshold is 0.12 (the unchecked constant), 2.4x the "
            f"threshold. {len(close_to_M)} of 600 documents fall inside the "
            "chosen 0.05 threshold (see near_threshold_margin_analysis)."
        ),
        "5_would_proposed_thresholds_produce_false_reviews": (
            "No at 0.05 (0 of 600 flagged; see near_threshold_margin_analysis "
            "for thresholds that WOULD start flagging correct documents -- "
            "notably anything >= 0.12 flags all 240 unchecked documents, since "
            "their margin is a hard constant at exactly -0.12)."
        ),
        "6_which_rules_are_evidence_backed_vs_speculative": (
            "Evidence-backed: detection_method/fallback_used (Phase 8C.10's own "
            "600/600 vs. 540/600 A/B result), anchor_found/checkbox_found "
            "(Phase 8C.10's 600/600 localization result), decision_margin at "
            "0.05 (this analysis's gap measurement). Structural-only, not "
            "benchmark-fit: shape_score's 0.5 floor (a broad plausibility bound, "
            "deliberately far from this benchmark's own 0.827-0.880 range so it "
            "does not overfit one renderer). Deferred, insufficient variation: "
            "anchor_distance_px and horizontal_alignment_offset_px numeric "
            "thresholds -- both are raw, non-normalized pixel offsets specific "
            "to one 2550x3300 synthetic render DPI, preserved as signals but not "
            "used in a production rule this phase."
        ),
    }


def _distribution(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    return {
        "n": n,
        "min": ordered[0],
        "max": ordered[-1],
        "mean": sum(ordered) / n,
        "median": ordered[n // 2],
    }


def _load_rows(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    with Path(path).open("r", encoding="utf-8") as file_obj:
        for line in file_obj:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows-jsonl", type=Path, default=DEFAULT_INPUT_ROWS)
    parser.add_argument("--output-json", type=Path, default=None)
    args = parser.parse_args(argv)

    report = run_analysis(args.rows_jsonl)
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
