import pytest

from w2_pipeline.evaluation.field_confidence import FieldConfidenceMatch
from w2_pipeline.evaluation.recognition_confidence_residual_audit import (
    ADDRESS_FIELD_PATHS,
    RESIDUAL_AUDIT_FIELD_PATHS,
    compose_route,
    distribution_summary,
    document_confidence_flag,
    field_confidence_signal,
    field_would_flag,
    non_ascii_field_values,
    percentile,
    summarize_routing,
    sweep_thresholds,
    triggering_fields,
)


def _match(
    field_path: str = "employer.address.address_line_1",
    *,
    matched: bool = True,
    count: int = 1,
    confidences: list[float] | None = None,
    value: str | None = "369 Pennsylvania Ave N",
) -> FieldConfidenceMatch:
    return FieldConfidenceMatch(
        field_path=field_path,
        field_value=value,
        matched=matched,
        contributing_observation_count=count,
        confidences=confidences if confidences is not None else [],
    )


# --- field_confidence_signal / `selected` strictness ---


def test_selected_populated_only_for_single_unambiguous_observation() -> None:
    signal = field_confidence_signal(_match(count=1, confidences=[0.87]))
    assert signal["selected"] == 0.87
    assert signal["selected_reason"] == "ok"


def test_selected_none_when_unmatched() -> None:
    signal = field_confidence_signal(_match(matched=False, count=0, confidences=[], value=None))
    assert signal["selected"] is None
    assert signal["selected_reason"] == "unmatched"


def test_selected_none_when_multi_observation_window() -> None:
    signal = field_confidence_signal(_match(count=2, confidences=[0.91, 0.95]))
    assert signal["selected"] is None
    assert signal["selected_reason"] == "ambiguous_multi_observation"
    # The aggregate views remain available even though `selected` is not.
    assert signal["min"] == 0.91
    assert signal["mean"] == pytest.approx(0.93)


def test_selected_none_when_single_observation_has_no_ocr_confidence() -> None:
    signal = field_confidence_signal(_match(count=1, confidences=[]))
    assert signal["selected"] is None
    assert signal["selected_reason"] == "no_ocr_confidence"


def test_selected_never_silently_falls_back_to_min() -> None:
    # A 3-observation window's min happens to be a real number, but
    # `selected` must stay None -- it is not a synonym for `min`.
    signal = field_confidence_signal(_match(count=3, confidences=[0.80, 0.90, 0.99]))
    assert signal["min"] == 0.80
    assert signal["selected"] is None


# --- field_would_flag ---


def test_field_would_flag_below_threshold() -> None:
    signal = field_confidence_signal(_match(count=1, confidences=[0.80]))
    assert field_would_flag(signal, threshold=0.90) is True


def test_field_would_flag_boundary_equal_does_not_flag() -> None:
    signal = field_confidence_signal(_match(count=1, confidences=[0.90]))
    assert field_would_flag(signal, threshold=0.90) is False


def test_field_would_flag_above_threshold_does_not_flag() -> None:
    signal = field_confidence_signal(_match(count=1, confidences=[0.95]))
    assert field_would_flag(signal, threshold=0.90) is False


def test_missing_confidence_never_flags() -> None:
    signal = field_confidence_signal(_match(matched=False, count=0, confidences=[], value=None))
    assert field_would_flag(signal, threshold=0.999) is False


def test_field_would_flag_respects_aggregation_choice() -> None:
    signal = field_confidence_signal(_match(count=2, confidences=[0.80, 0.99]))
    assert signal["selected"] is None
    # "selected" aggregation: no signal, never flags.
    assert field_would_flag(signal, threshold=0.90, aggregation="selected") is False
    # "min" aggregation: 0.80 < 0.90, flags.
    assert field_would_flag(signal, threshold=0.90, aggregation="min") is True
    # "mean" aggregation: 0.895 < 0.90, flags.
    assert field_would_flag(signal, threshold=0.90, aggregation="mean") is True


# --- document_confidence_flag ---


def test_document_confidence_flag_true_if_any_field_flags() -> None:
    field_signals = {
        "employer.name": field_confidence_signal(_match(count=1, confidences=[0.999])),
        "employer.address.address_line_1": field_confidence_signal(_match(count=1, confidences=[0.80])),
    }
    assert document_confidence_flag(field_signals, ("employer.name", "employer.address.address_line_1"), threshold=0.90) is True


def test_document_confidence_flag_false_if_no_field_flags() -> None:
    field_signals = {
        "employer.name": field_confidence_signal(_match(count=1, confidences=[0.999])),
        "employer.address.address_line_1": field_confidence_signal(_match(count=1, confidences=[0.95])),
    }
    assert document_confidence_flag(field_signals, ("employer.name", "employer.address.address_line_1"), threshold=0.90) is False


def test_document_confidence_flag_ignores_out_of_scope_fields() -> None:
    field_signals = {
        "some.other.field": field_confidence_signal(_match(count=1, confidences=[0.01])),
    }
    assert document_confidence_flag(field_signals, ("employer.name",), threshold=0.90) is False


# --- compose_route ---


def test_compose_route_needs_review_when_validator_flags() -> None:
    assert compose_route("needs_review", confidence_flag=False) == "needs_review"


def test_compose_route_needs_review_when_confidence_flags() -> None:
    assert compose_route("accepted", confidence_flag=True) == "needs_review"


def test_compose_route_accepted_when_neither_flags() -> None:
    assert compose_route("accepted", confidence_flag=False) == "accepted"


# --- summarize_routing ---


def test_summarize_routing_basic_arithmetic() -> None:
    rows = [
        {"has_error": True, "route": "needs_review"},  # erroneous, caught
        {"has_error": True, "route": "accepted"},  # erroneous, unsafe-accepted
        {"has_error": False, "route": "needs_review"},  # correct, false review
        {"has_error": False, "route": "accepted"},  # correct, accepted
    ]
    metrics = summarize_routing(rows)
    assert metrics["total_documents"] == 4
    assert metrics["erroneous_documents"] == 2
    assert metrics["correct_documents"] == 2
    assert metrics["erroneous_routed_needs_review"] == 1
    assert metrics["erroneous_accepted"] == 1
    assert metrics["correct_routed_needs_review"] == 1
    assert metrics["error_detection_recall"] == 0.5
    assert metrics["false_review_rate"] == 0.5
    assert metrics["unsafe_acceptance_rate"] == 0.25
    assert metrics["review_queue_precision"] == 0.5


def test_summarize_routing_handles_empty_denominators() -> None:
    rows = [{"has_error": False, "route": "accepted"}]
    metrics = summarize_routing(rows)
    assert metrics["error_detection_recall"] is None  # no erroneous docs
    assert metrics["review_queue_precision"] is None  # no needs_review docs


# --- sweep_thresholds: no double-counting ---


def _row(document_id: str, variant_id: str, *, has_error: bool, validator_status: str, confidence: float | None) -> dict:
    signal = (
        field_confidence_signal(_match(count=1, confidences=[confidence]))
        if confidence is not None
        else field_confidence_signal(_match(matched=False, count=0, confidences=[], value=None))
    )
    return {
        "document_id": document_id,
        "variant_id": variant_id,
        "has_error": has_error,
        "validator_status": validator_status,
        "field_signals": {"employer.address.address_line_1": signal},
        "failing_field_paths": ["employer.address.address_line_1"] if has_error else [],
    }


def test_sweep_thresholds_separates_already_routed_from_newly_routed() -> None:
    rows = [
        # Already caught by the validator alone (structural failure) --
        # confidence must not double-count this as its own win.
        _row("doc_a", "rotated_png", has_error=True, validator_status="needs_review", confidence=0.99),
        # Unsafe-accepted by the validator; low confidence should newly catch it.
        _row("doc_b", "blurred_png", has_error=True, validator_status="accepted", confidence=0.80),
        # Correct document with low confidence -> false review under this threshold.
        _row("doc_c", "compressed_jpeg", has_error=False, validator_status="accepted", confidence=0.85),
        # Correct, high confidence, untouched.
        _row("doc_d", "external_clean_render", has_error=False, validator_status="accepted", confidence=0.999),
    ]

    report = sweep_thresholds(
        rows,
        thresholds=[0.90],
        field_paths=("employer.address.address_line_1",),
        aggregation="selected",
    )
    entry = report["thresholds"][0]

    assert report["baseline_unsafe_accepted_count"] == 1  # doc_b only
    assert entry["already_routed_by_validator_count"] == 1  # doc_a only
    assert entry["residual_errors_caught"] == 1  # doc_b, from the unsafe-accepted set
    assert entry["newly_routed_only_by_confidence_count"] == 2  # doc_b and doc_c
    newly_routed_ids = {row["document_id"] for row in entry["newly_routed_only_by_confidence"]}
    assert newly_routed_ids == {"doc_b", "doc_c"}
    # doc_a must not appear in "newly routed only by confidence" -- it was
    # already routed by the validator.
    assert "doc_a" not in newly_routed_ids

    metrics = entry["metrics"]
    assert metrics["erroneous_routed_needs_review"] == 2  # doc_a + doc_b
    assert metrics["unsafe_acceptance_rate"] == 0.0
    assert metrics["correct_routed_needs_review"] == 1  # doc_c


def test_sweep_thresholds_boundary_around_observed_confidence() -> None:
    rows = [
        _row("doc_a", "blurred_png", has_error=True, validator_status="accepted", confidence=0.99),
    ]
    # A threshold above the observed 0.99 confidence catches it.
    report_high = sweep_thresholds(rows, thresholds=[0.999999], field_paths=("employer.address.address_line_1",))
    entry_high = report_high["thresholds"][0]
    assert entry_high["residual_errors_caught"] == 1
    assert entry_high["newly_routed_only_by_confidence_count"] == 1
    # A threshold below the observed 0.99 confidence does not.
    report_low = sweep_thresholds(rows, thresholds=[0.50], field_paths=("employer.address.address_line_1",))
    entry_low = report_low["thresholds"][0]
    assert entry_low["residual_errors_caught"] == 0
    assert entry_low["newly_routed_only_by_confidence_count"] == 0


def test_sweep_thresholds_missing_confidence_never_newly_routes() -> None:
    rows = [
        _row("doc_a", "blurred_png", has_error=True, validator_status="accepted", confidence=None),
    ]
    report = sweep_thresholds(rows, thresholds=[0.999], field_paths=("employer.address.address_line_1",))
    entry = report["thresholds"][0]
    assert entry["newly_routed_only_by_confidence_count"] == 0
    assert entry["residual_errors_caught"] == 0


# --- triggering_fields ---


def test_triggering_fields_reports_culprit_field_and_confidence() -> None:
    field_signals = {
        "employer.name": field_confidence_signal(_match(count=1, confidences=[0.999], value="Acme Corp")),
        "employer.address.address_line_1": field_confidence_signal(
            _match(count=1, confidences=[0.80], value="1 Low Confidence St")
        ),
    }
    triggers = triggering_fields(
        field_signals, ("employer.name", "employer.address.address_line_1"), threshold=0.90
    )
    assert len(triggers) == 1
    assert triggers[0]["field_path"] == "employer.address.address_line_1"
    assert triggers[0]["field_value"] == "1 Low Confidence St"
    assert triggers[0]["confidence"] == 0.80


def test_triggering_fields_empty_when_nothing_flags() -> None:
    field_signals = {
        "employer.name": field_confidence_signal(_match(count=1, confidences=[0.999])),
    }
    assert triggering_fields(field_signals, ("employer.name",), threshold=0.90) == []


def test_sweep_thresholds_newly_routed_entries_include_triggering_fields() -> None:
    rows = [
        _row("doc_b", "blurred_png", has_error=True, validator_status="accepted", confidence=0.80),
    ]
    report = sweep_thresholds(rows, thresholds=[0.90], field_paths=("employer.address.address_line_1",))
    entry = report["thresholds"][0]["newly_routed_only_by_confidence"][0]
    assert entry["triggering_fields"][0]["field_path"] == "employer.address.address_line_1"
    assert entry["triggering_fields"][0]["confidence"] == 0.80


# --- non_ascii_field_values ---


def test_non_ascii_field_values_detects_accented_text() -> None:
    rows = [
        {
            "document_id": "symage_900027",
            "variant_id": "blurred_png",
            "failing_field_paths": ["employer.address.address_line_1"],
            "field_signals": {
                "employer.address.address_line_1": field_confidence_signal(
                    _match(count=1, confidences=[0.62], value="369 Pennsylvania Áve N")
                ),
                "employer.name": field_confidence_signal(_match(count=1, confidences=[0.99], value="Acme Corp")),
            },
        }
    ]
    hits = non_ascii_field_values(rows)
    assert len(hits) == 1
    assert hits[0]["field_path"] == "employer.address.address_line_1"
    assert hits[0]["correct"] is False


# --- checkbox exclusion ---


def test_box_13_retirement_plan_excluded_from_residual_audit_field_paths() -> None:
    assert "box_13.retirement_plan" not in RESIDUAL_AUDIT_FIELD_PATHS


def test_address_line_2_excluded_from_address_field_paths() -> None:
    assert "employer.address.address_line_2" not in ADDRESS_FIELD_PATHS
    assert "employee.address.address_line_2" not in ADDRESS_FIELD_PATHS
    assert "employer.address.country" in ADDRESS_FIELD_PATHS
    assert "employee.address.country" in ADDRESS_FIELD_PATHS
    assert len(ADDRESS_FIELD_PATHS) == 10


# --- percentile / distribution_summary ---


def test_percentile_median_of_odd_list() -> None:
    assert percentile([1.0, 2.0, 3.0], 50) == 2.0


def test_percentile_empty_list_is_none() -> None:
    assert percentile([], 50) is None


def test_distribution_summary_empty() -> None:
    summary = distribution_summary([])
    assert summary["n"] == 0
    assert summary["min"] is None


def test_distribution_summary_basic() -> None:
    summary = distribution_summary([0.9, 0.95, 1.0])
    assert summary["n"] == 3
    assert summary["min"] == 0.9
    assert summary["max"] == 1.0
    assert summary["median"] == 0.95
