from decimal import Decimal

from w2_pipeline.contracts.w2 import Box12Entry, StateLocalEntry, W2Document
from w2_pipeline.validation.models import ExtractionSignals, ValidationSeverity
from w2_pipeline.validation.rules import ALL_RULE_NAMES, run_all_rules


def _issue_codes(document: W2Document) -> list[str]:
    return [issue.code for issue in run_all_rules(document, ExtractionSignals())]


def test_happy_path_document_has_no_error_issues(happy_path_document: W2Document) -> None:
    issues = run_all_rules(happy_path_document, ExtractionSignals())

    errors = [issue for issue in issues if issue.severity == ValidationSeverity.ERROR]
    assert errors == []


def test_missing_ssn_reported_as_required_field_missing(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={"employee": happy_path_document.employee.model_copy(update={"ssn": None})}
    )

    issues = run_all_rules(document, ExtractionSignals())

    matching = [issue for issue in issues if issue.field_path == "employee.ssn"]
    assert len(matching) == 1
    assert matching[0].code == "required_field_missing"
    assert matching[0].severity == ValidationSeverity.ERROR


def test_invalid_ssn_format_detected(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={"employee": happy_path_document.employee.model_copy(update={"ssn": "0000005"})}
    )

    issues = run_all_rules(document, ExtractionSignals())

    matching = [issue for issue in issues if issue.code == "invalid_ssn_format"]
    assert len(matching) == 1
    assert matching[0].severity == ValidationSeverity.ERROR
    assert matching[0].field_path == "employee.ssn"
    # The malformed value must never appear unredacted in the issue.
    assert matching[0].observed_value != "0000005"


def test_invalid_ein_format_detected(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={"employer": happy_path_document.employer.model_copy(update={"ein": "123456789"})}
    )

    issues = run_all_rules(document, ExtractionSignals())

    matching = [issue for issue in issues if issue.code == "invalid_ein_format"]
    assert len(matching) == 1
    assert matching[0].severity == ValidationSeverity.ERROR


def test_missing_employer_name_and_ein_both_reported(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={
            "employer": happy_path_document.employer.model_copy(
                update={"ein": None, "name": None}
            )
        }
    )

    codes = _issue_codes(document)

    assert codes.count("required_field_missing") >= 2


def test_optional_blank_fields_do_not_trigger_issues(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={
            "employee": happy_path_document.employee.model_copy(
                update={"suffix": None, "middle_initial": None}
            ),
            "employer": happy_path_document.employer.model_copy(update={"control_number": None}),
            "federal_wages_and_taxes": happy_path_document.federal_wages_and_taxes.model_copy(
                update={
                    "box_3_social_security_wages": None,
                    "box_4_social_security_tax_withheld": None,
                    "box_7_social_security_tips": None,
                    "box_8_allocated_tips": None,
                    "box_10_dependent_care_benefits": None,
                    "box_11_nonqualified_plans": None,
                }
            ),
            "box_12_entries": [],
            "box_14_entries": [],
            "state_local_entries": [],
        }
    )

    issues = run_all_rules(document, ExtractionSignals())

    errors = [issue for issue in issues if issue.severity == ValidationSeverity.ERROR]
    assert errors == []


def test_missing_core_wage_box_reported(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={
            "federal_wages_and_taxes": happy_path_document.federal_wages_and_taxes.model_copy(
                update={"box_1_wages_tips_other_compensation": None}
            )
        }
    )

    matching = [
        issue
        for issue in run_all_rules(document, ExtractionSignals())
        if issue.field_path == "federal_wages_and_taxes.box_1_wages_tips_other_compensation"
    ]
    assert len(matching) == 1
    assert matching[0].code == "required_field_missing"


def test_unsupported_tax_year_detected(happy_path_document: W2Document) -> None:
    # `model_copy` does not re-run validators, so this can carry a value
    # the `Literal[2026]` schema constraint would otherwise reject --
    # exactly the "detect an incompatible year value" case this rule is for.
    document = happy_path_document.model_copy(
        update={"metadata": happy_path_document.metadata.model_copy(update={"tax_year": 2025})}
    )

    codes = _issue_codes(document)

    assert "tax_year_mismatch" in codes


def test_negative_money_value_detected(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={
            "federal_wages_and_taxes": happy_path_document.federal_wages_and_taxes.model_copy(
                update={"box_1_wages_tips_other_compensation": Decimal("-100.00")}
            )
        }
    )

    matching = [issue for issue in run_all_rules(document, ExtractionSignals()) if issue.code == "invalid_money_value"]
    assert len(matching) == 1
    assert matching[0].severity == ValidationSeverity.ERROR


def test_excess_decimal_precision_detected(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={
            "federal_wages_and_taxes": happy_path_document.federal_wages_and_taxes.model_copy(
                update={"box_2_federal_income_tax_withheld": Decimal("100.001")}
            )
        }
    )

    matching = [issue for issue in run_all_rules(document, ExtractionSignals()) if issue.code == "invalid_money_value"]
    assert len(matching) == 1


def test_malformed_box_12_code_detected(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={"box_12_entries": [Box12Entry(code="d", amount=Decimal("10.00"))]}
    )

    matching = [
        issue
        for issue in run_all_rules(document, ExtractionSignals())
        if issue.code == "invalid_box12_code_format"
    ]
    assert len(matching) == 1
    assert matching[0].severity == ValidationSeverity.ERROR


def test_valid_box_12_code_not_flagged(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={"box_12_entries": [Box12Entry(code="DD", amount=Decimal("10.00"))]}
    )

    codes = _issue_codes(document)

    assert "invalid_box12_code_format" not in codes


def test_entirely_blank_state_local_entry_flagged_as_warning(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={"state_local_entries": [StateLocalEntry()]}
    )

    matching = [issue for issue in run_all_rules(document, ExtractionSignals()) if issue.code == "empty_entry"]
    assert len(matching) == 1
    assert matching[0].severity == ValidationSeverity.WARNING


def test_populated_state_local_entry_not_flagged_empty(happy_path_document: W2Document) -> None:
    codes = _issue_codes(happy_path_document)

    assert "empty_entry" not in codes


# --- Phase 8D.1A: employer/employee address format ------------------------


def test_valid_address_not_flagged(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={
            "employer": happy_path_document.employer.model_copy(
                update={
                    "address": happy_path_document.employer.address.model_copy(
                        update={"state": "NC", "postal_code": "28906"}
                    )
                }
            )
        }
    )

    codes = _issue_codes(document)

    assert "invalid_address_state_format" not in codes
    assert "invalid_address_postal_code_format" not in codes


def test_valid_zip_plus_4_not_flagged(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={
            "employee": happy_path_document.employee.model_copy(
                update={
                    "address": happy_path_document.employee.address.model_copy(
                        update={"state": "NY", "postal_code": "10001-1234"}
                    )
                }
            )
        }
    )

    assert "invalid_address_postal_code_format" not in _issue_codes(document)


def test_invalid_address_state_code_detected(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={
            "employer": happy_path_document.employer.model_copy(
                update={
                    "address": happy_path_document.employer.address.model_copy(update={"state": "ZZ"})
                }
            )
        }
    )

    matching = [
        issue for issue in run_all_rules(document, ExtractionSignals()) if issue.code == "invalid_address_state_format"
    ]
    assert len(matching) == 1
    assert matching[0].severity == ValidationSeverity.ERROR
    assert matching[0].field_path == "employer.address.state"


def test_invalid_address_postal_code_detected(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={
            "employee": happy_path_document.employee.model_copy(
                update={
                    "address": happy_path_document.employee.address.model_copy(
                        update={"postal_code": "ABCDE"}
                    )
                }
            )
        }
    )

    matching = [
        issue
        for issue in run_all_rules(document, ExtractionSignals())
        if issue.code == "invalid_address_postal_code_format"
    ]
    assert len(matching) == 1
    assert matching[0].field_path == "employee.address.postal_code"


def test_address_with_no_state_or_postal_code_not_flagged(happy_path_document: W2Document) -> None:
    """A wholly-null address (this dataset's own default, before Phase
    8D.1A's OCR recovery ran) must never be treated as malformed."""

    codes = _issue_codes(happy_path_document)

    assert "invalid_address_state_format" not in codes
    assert "invalid_address_postal_code_format" not in codes


# --- Phase 8D.1B: address extraction evidence ----------------------------


def test_strong_employer_address_evidence_not_flagged(happy_path_document: W2Document) -> None:
    signals = ExtractionSignals(
        route="ocr",
        employer_address_evidence_region_observation_count=4,
        employer_address_evidence_usable_row_count=3,
        employer_address_evidence_parse_complete=True,
    )

    codes = [issue.code for issue in run_all_rules(happy_path_document, signals)]

    assert "employer_address_extraction_incomplete" not in codes


def test_strong_employee_address_evidence_not_flagged(happy_path_document: W2Document) -> None:
    signals = ExtractionSignals(
        route="ocr",
        employee_address_evidence_region_observation_count=3,
        employee_address_evidence_usable_row_count=2,
        employee_address_evidence_parse_complete=True,
    )

    codes = [issue.code for issue in run_all_rules(happy_path_document, signals)]

    assert "employee_address_extraction_incomplete" not in codes


def test_missing_employer_address_evidence_with_observations_is_flagged(
    happy_path_document: W2Document,
) -> None:
    """The exact evidence shape measured across all 13 real Phase 8D.1A
    unsafe-acceptance cases: OCR found observations in the region
    (`region_observation_count > 0`) but extraction never completed
    (`parse_complete=False`)."""

    signals = ExtractionSignals(
        route="ocr",
        employer_address_evidence_region_observation_count=4,
        employer_address_evidence_usable_row_count=2,
        employer_address_evidence_parse_complete=False,
    )

    issues = run_all_rules(happy_path_document, signals)

    matching = [issue for issue in issues if issue.code == "employer_address_extraction_incomplete"]
    assert len(matching) == 1
    assert matching[0].severity == ValidationSeverity.ERROR
    assert matching[0].field_path == "employer.address.address_line_1"


def test_missing_employee_address_evidence_with_observations_is_flagged(
    happy_path_document: W2Document,
) -> None:
    signals = ExtractionSignals(
        route="ocr",
        employee_address_evidence_region_observation_count=3,
        employee_address_evidence_usable_row_count=1,
        employee_address_evidence_parse_complete=False,
    )

    codes = [issue.code for issue in run_all_rules(happy_path_document, signals)]

    assert "employee_address_extraction_incomplete" in codes


def test_zero_region_observations_not_flagged(happy_path_document: W2Document) -> None:
    """A region with zero OCR observations at all is a route/document
    that never had this data to begin with, not an extraction failure --
    must not be conflated with the 13-real-case "found evidence but
    could not complete" pattern this rule targets."""

    signals = ExtractionSignals(
        route="ocr",
        employer_address_evidence_region_observation_count=0,
        employer_address_evidence_usable_row_count=0,
        employer_address_evidence_parse_complete=False,
    )

    codes = [issue.code for issue in run_all_rules(happy_path_document, signals)]

    assert "employer_address_extraction_incomplete" not in codes


def test_no_address_evidence_supplied_is_not_flagged(happy_path_document: W2Document) -> None:
    """Missing evidence (e.g. a caller/pipeline that never threaded it)
    must not be treated as a failure -- only real "found evidence, could
    not complete" evidence fires this rule."""

    signals = ExtractionSignals(route="ocr")

    codes = [issue.code for issue in run_all_rules(happy_path_document, signals)]

    assert "employer_address_extraction_incomplete" not in codes
    assert "employee_address_extraction_incomplete" not in codes


def test_address_extraction_evidence_route_scoped_to_ocr_and_mixed(happy_path_document: W2Document) -> None:
    incomplete_evidence = {
        "employer_address_evidence_region_observation_count": 4,
        "employer_address_evidence_usable_row_count": 2,
        "employer_address_evidence_parse_complete": False,
    }

    for route in (None, "vlm", "native_pdf"):
        signals = ExtractionSignals(route=route, **incomplete_evidence)
        codes = [issue.code for issue in run_all_rules(happy_path_document, signals)]
        assert "employer_address_extraction_incomplete" not in codes

    for route in ("ocr", "mixed"):
        signals = ExtractionSignals(route=route, **incomplete_evidence)
        codes = [issue.code for issue in run_all_rules(happy_path_document, signals)]
        assert "employer_address_extraction_incomplete" in codes


def test_employer_and_employee_address_issues_are_independent(happy_path_document: W2Document) -> None:
    signals = ExtractionSignals(
        route="ocr",
        employer_address_evidence_region_observation_count=4,
        employer_address_evidence_usable_row_count=2,
        employer_address_evidence_parse_complete=False,
        employee_address_evidence_region_observation_count=3,
        employee_address_evidence_usable_row_count=1,
        employee_address_evidence_parse_complete=False,
    )

    codes = {issue.code for issue in run_all_rules(happy_path_document, signals)}

    assert "employer_address_extraction_incomplete" in codes
    assert "employee_address_extraction_incomplete" in codes


def test_address_evidence_issue_does_not_suppress_employer_name_issues() -> None:
    document = generate_synthetic_w2_documents_for_name("Elan Consulting Corp 2861 Geneva Ponce De Leon Rd")
    signals = ExtractionSignals(
        route="ocr",
        employer_name_observation_count=2,
        employer_address_evidence_region_observation_count=4,
        employer_address_evidence_usable_row_count=2,
        employer_address_evidence_parse_complete=False,
    )

    codes = {issue.code for issue in run_all_rules(document, signals)}

    assert "employer_name_address_leak" in codes
    assert "employer_name_layout_anomaly" in codes
    assert "employer_address_extraction_incomplete" in codes


def test_optional_address_line_2_null_does_not_trigger_review(happy_path_document: W2Document) -> None:
    """Missing whole address (Section 9's evidence-based rule) is a
    distinct concept from an optional `address_line_2` that is
    legitimately null -- the latter must never be conflated with the
    former."""

    document = happy_path_document.model_copy(
        update={
            "employer": happy_path_document.employer.model_copy(
                update={
                    "address": happy_path_document.employer.address.model_copy(
                        update={
                            "address_line_1": "105 Penland St",
                            "address_line_2": None,
                            "city": "Murphy",
                            "state": "NC",
                            "postal_code": "28906",
                        }
                    )
                }
            )
        }
    )
    signals = ExtractionSignals(
        route="ocr",
        employer_address_evidence_region_observation_count=3,
        employer_address_evidence_usable_row_count=3,
        employer_address_evidence_parse_complete=True,
    )

    codes = [issue.code for issue in run_all_rules(document, signals)]

    assert "employer_address_extraction_incomplete" not in codes
    assert "invalid_address_postal_code_format" not in codes


# --- Phase 8D.1B: Box 12 amount-without-code -----------------------------


def test_box_12_amount_without_code_signal_routes_to_review(happy_path_document: W2Document) -> None:
    signals = ExtractionSignals(box_12_amount_without_code_found=True)

    issues = run_all_rules(happy_path_document, signals)

    matching = [issue for issue in issues if issue.code == "box_12_amount_without_code"]
    assert len(matching) == 1
    assert matching[0].severity == ValidationSeverity.ERROR
    assert matching[0].field_path == "box_12_entries"


def test_box_12_amount_without_code_absent_signal_not_flagged(happy_path_document: W2Document) -> None:
    codes = _issue_codes(happy_path_document)

    assert "box_12_amount_without_code" not in codes


def test_checkbox_rules_unaffected_by_address_and_box12_signals(happy_path_document: W2Document) -> None:
    signals = ExtractionSignals(
        route="ocr",
        checkbox_evidence_detection_method="anchor_relative",
        checkbox_evidence_fallback_used=False,
        checkbox_evidence_anchor_found=True,
        checkbox_evidence_checkbox_found=True,
        checkbox_evidence_shape_score=0.86,
        checkbox_evidence_interior_ink_ratio=0.27,
        checkbox_evidence_decision_margin=0.15,
        employer_address_evidence_region_observation_count=4,
        employer_address_evidence_usable_row_count=2,
        employer_address_evidence_parse_complete=False,
        box_12_amount_without_code_found=True,
    )

    codes = {issue.code for issue in run_all_rules(happy_path_document, signals)}

    checkbox_codes = {
        "retirement_plan_checkbox_evidence_missing",
        "retirement_plan_checkbox_fallback_used",
        "retirement_plan_checkbox_anchor_missing",
        "retirement_plan_checkbox_not_found",
        "retirement_plan_checkbox_low_decision_margin",
        "retirement_plan_checkbox_geometry_anomaly",
    }
    assert not (codes & checkbox_codes)
    assert "employer_address_extraction_incomplete" in codes
    assert "box_12_amount_without_code" in codes


def test_extraction_failed_signal_reported_as_error(happy_path_document: W2Document) -> None:
    from w2_pipeline.validation.models import ExtractionOutcome

    signals = ExtractionSignals(outcome=ExtractionOutcome.EXTRACTION_FAILED)
    issues = run_all_rules(happy_path_document, signals)

    matching = [issue for issue in issues if issue.code == "extraction_failure"]
    assert len(matching) == 1
    assert matching[0].severity == ValidationSeverity.ERROR


def test_extraction_warnings_reported_as_warning_severity(happy_path_document: W2Document) -> None:
    signals = ExtractionSignals(warnings=["Box 13 visual checkbox detection failed: boom"])
    issues = run_all_rules(happy_path_document, signals)

    matching = [issue for issue in issues if issue.code == "extraction_warning"]
    assert len(matching) == 1
    assert matching[0].severity == ValidationSeverity.WARNING
    assert matching[0].message == "Box 13 visual checkbox detection failed: boom"


def test_multiple_issues_are_all_returned_not_short_circuited(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={
            "employee": happy_path_document.employee.model_copy(update={"ssn": None}),
            "employer": happy_path_document.employer.model_copy(update={"ein": "bad-ein"}),
        }
    )

    codes = _issue_codes(document)

    assert "required_field_missing" in codes
    assert "invalid_ein_format" in codes
    assert len(codes) >= 2


def test_all_rule_names_documents_the_checks_run_count() -> None:
    assert len(ALL_RULE_NAMES) == 16


# --- Phase 8C.8: employer.name address-leak rule -----------------------


def test_employer_name_address_leak_shape_is_flagged(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={
            "employer": happy_path_document.employer.model_copy(
                update={"name": "Elan Consulting Corp 2861 Geneva Ponce De Leon Rd"}
            )
        }
    )

    issues = run_all_rules(document, ExtractionSignals())

    matching = [issue for issue in issues if issue.code == "employer_name_address_leak"]
    assert len(matching) == 1
    assert matching[0].severity == ValidationSeverity.ERROR
    assert matching[0].field_path == "employer.name"


def test_normal_employer_name_not_flagged_by_address_leak_rule(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={"employer": happy_path_document.employer.model_copy(update={"name": "Timberline Trading Co."})}
    )

    codes = _issue_codes(document)

    assert "employer_name_address_leak" not in codes


def test_legitimate_numeric_company_name_not_flagged(happy_path_document: W2Document) -> None:
    """`3M Corporation` contains a bare number but no road-suffix word --
    the rule requires both together, exactly as measured in Phase 8C.5."""

    document = happy_path_document.model_copy(
        update={"employer": happy_path_document.employer.model_copy(update={"name": "3M Corporation"})}
    )

    codes = _issue_codes(document)

    assert "employer_name_address_leak" not in codes


def test_ambiguous_suffix_only_company_name_not_flagged(happy_path_document: W2Document) -> None:
    """`Infinite Loop Technologies` contains a road-suffix word ("Loop")
    but no street number -- a real false-positive case Phase 8C.5 found
    for the suffix-alone signal; the combined rule must not flag it."""

    document = happy_path_document.model_copy(
        update={"employer": happy_path_document.employer.model_copy(update={"name": "Infinite Loop Technologies"})}
    )

    codes = _issue_codes(document)

    assert "employer_name_address_leak" not in codes


def test_road_suffix_matching_uses_whole_word_boundaries_in_production() -> None:
    from w2_pipeline.validation.rules import _check_employer_name_address_leak

    document = generate_synthetic_w2_documents_for_name("123 Wayfair Inc")
    issues = _check_employer_name_address_leak(document)

    assert issues == []


def generate_synthetic_w2_documents_for_name(name: str) -> W2Document:
    from w2_pipeline.evaluation.synthetic import SyntheticGenerationConfig, generate_synthetic_w2_documents

    base = generate_synthetic_w2_documents(SyntheticGenerationConfig(sample_count=1))[0]
    return base.model_copy(update={"employer": base.employer.model_copy(update={"name": name})})


# --- Phase 8C.8: employer.name layout-anomaly rule ----------------------


def test_employer_name_from_single_observation_not_flagged(happy_path_document: W2Document) -> None:
    signals = ExtractionSignals(employer_name_observation_count=1)

    issues = run_all_rules(happy_path_document, signals)

    assert "employer_name_layout_anomaly" not in [issue.code for issue in issues]


def test_employer_name_from_multiple_observations_flagged(happy_path_document: W2Document) -> None:
    signals = ExtractionSignals(employer_name_observation_count=2)

    issues = run_all_rules(happy_path_document, signals)

    matching = [issue for issue in issues if issue.code == "employer_name_layout_anomaly"]
    assert len(matching) == 1
    assert matching[0].severity == ValidationSeverity.ERROR
    assert matching[0].field_path == "employer.name"
    assert matching[0].metadata == {"observation_count": 2}


def test_missing_layout_provenance_handled_safely(happy_path_document: W2Document) -> None:
    """No signal available (e.g. Pipeline B, or the count could not be
    derived) must never be treated as suspicious on its own."""

    signals = ExtractionSignals(employer_name_observation_count=None)

    issues = run_all_rules(happy_path_document, signals)

    assert "employer_name_layout_anomaly" not in [issue.code for issue in issues]


# --- Phase 8C.8: combined routing ----------------------------------------


def test_neither_signal_fires_existing_behavior_preserved(happy_path_document: W2Document) -> None:
    signals = ExtractionSignals(employer_name_observation_count=1)

    issues = run_all_rules(happy_path_document, signals)

    codes = {issue.code for issue in issues}
    assert "employer_name_address_leak" not in codes
    assert "employer_name_layout_anomaly" not in codes


def test_address_only_routes_needs_review() -> None:
    from w2_pipeline.validation.routing import decide_status

    document = generate_synthetic_w2_documents_for_name("Elan Consulting Corp 2861 Geneva Ponce De Leon Rd")
    signals = ExtractionSignals(employer_name_observation_count=1)

    issues = run_all_rules(document, signals)
    status = decide_status(issues)

    assert "employer_name_address_leak" in {issue.code for issue in issues}
    assert "employer_name_layout_anomaly" not in {issue.code for issue in issues}
    assert status.value == "needs_review"


def test_layout_only_routes_needs_review(happy_path_document: W2Document) -> None:
    from w2_pipeline.validation.routing import decide_status

    signals = ExtractionSignals(employer_name_observation_count=2)

    issues = run_all_rules(happy_path_document, signals)
    status = decide_status(issues)

    codes = {issue.code for issue in issues}
    assert "employer_name_layout_anomaly" in codes
    assert "employer_name_address_leak" not in codes
    assert status.value == "needs_review"


def test_both_signals_fire_and_both_issues_are_preserved() -> None:
    from w2_pipeline.validation.routing import decide_status

    document = generate_synthetic_w2_documents_for_name("Elan Consulting Corp 2861 Geneva Ponce De Leon Rd")
    signals = ExtractionSignals(employer_name_observation_count=2)

    issues = run_all_rules(document, signals)
    status = decide_status(issues)

    codes = {issue.code for issue in issues}
    assert "employer_name_address_leak" in codes
    assert "employer_name_layout_anomaly" in codes
    assert status.value == "needs_review"


# --- Phase 8C.12: box_13.retirement_plan checkbox-evidence rule ----------

_TRUSTED_CHECKED_EVIDENCE = ExtractionSignals(
    route="ocr",
    checkbox_evidence_detection_method="anchor_relative",
    checkbox_evidence_fallback_used=False,
    checkbox_evidence_anchor_found=True,
    checkbox_evidence_checkbox_found=True,
    checkbox_evidence_shape_score=0.86,
    checkbox_evidence_interior_ink_ratio=0.27,
    checkbox_evidence_decision_margin=0.15,
)

_TRUSTED_UNCHECKED_EVIDENCE = ExtractionSignals(
    route="ocr",
    checkbox_evidence_detection_method="anchor_relative",
    checkbox_evidence_fallback_used=False,
    checkbox_evidence_anchor_found=True,
    checkbox_evidence_checkbox_found=True,
    checkbox_evidence_shape_score=0.86,
    checkbox_evidence_interior_ink_ratio=0.0,
    checkbox_evidence_decision_margin=-0.12,
)

_CHECKBOX_CODES = frozenset(
    {
        "retirement_plan_checkbox_evidence_missing",
        "retirement_plan_checkbox_fallback_used",
        "retirement_plan_checkbox_anchor_missing",
        "retirement_plan_checkbox_not_found",
        "retirement_plan_checkbox_low_decision_margin",
        "retirement_plan_checkbox_geometry_anomaly",
    }
)


def _checkbox_codes(document: W2Document, signals: ExtractionSignals) -> set[str]:
    return {issue.code for issue in run_all_rules(document, signals)} & _CHECKBOX_CODES


def test_strong_checked_evidence_has_no_checkbox_issue(happy_path_document: W2Document) -> None:
    assert _checkbox_codes(happy_path_document, _TRUSTED_CHECKED_EVIDENCE) == set()


def test_strong_unchecked_evidence_has_no_checkbox_issue(happy_path_document: W2Document) -> None:
    """Symmetric: an unchecked box with equally strong evidence is just as
    trustworthy as a checked one -- the rule judges evidence, not class."""

    assert _checkbox_codes(happy_path_document, _TRUSTED_UNCHECKED_EVIDENCE) == set()


def test_no_route_no_checkbox_evidence_is_not_flagged(happy_path_document: W2Document) -> None:
    """A route this validator cannot positively identify as OCR/mixed
    (unset, Pipeline B's `vlm`, native_pdf) must not be penalized for
    lacking evidence it was never expected to carry."""

    for route in (None, "vlm", "native_pdf"):
        signals = ExtractionSignals(route=route)
        assert _checkbox_codes(happy_path_document, signals) == set()


def test_ocr_route_with_no_checkbox_evidence_at_all_is_flagged(happy_path_document: W2Document) -> None:
    signals = ExtractionSignals(route="ocr")

    issues = run_all_rules(happy_path_document, signals)

    matching = [issue for issue in issues if issue.code == "retirement_plan_checkbox_evidence_missing"]
    assert len(matching) == 1
    assert matching[0].severity == ValidationSeverity.ERROR
    assert matching[0].field_path == "box_13.retirement_plan"


def test_mixed_route_with_no_checkbox_evidence_at_all_is_flagged(happy_path_document: W2Document) -> None:
    signals = ExtractionSignals(route="mixed")

    assert "retirement_plan_checkbox_evidence_missing" in _checkbox_codes(happy_path_document, signals)


def test_fallback_used_is_flagged(happy_path_document: W2Document) -> None:
    signals = _TRUSTED_CHECKED_EVIDENCE.model_copy(
        update={
            "checkbox_evidence_detection_method": "fixed_zone_fallback",
            "checkbox_evidence_fallback_used": True,
        }
    )

    issues = run_all_rules(happy_path_document, signals)

    matching = [issue for issue in issues if issue.code == "retirement_plan_checkbox_fallback_used"]
    assert len(matching) == 1
    assert matching[0].observed_value == "fixed_zone_fallback"


def test_diagnostic_disabled_method_is_also_flagged_as_fallback(happy_path_document: W2Document) -> None:
    """`fixed_zone_disabled` (the diagnostic override) is neither the
    trusted anchor-relative detector nor a genuine fallback-on-failure, but
    it is still the legacy mechanism -- treated the same as a real
    fallback, since production callers should never see this method."""

    signals = _TRUSTED_CHECKED_EVIDENCE.model_copy(
        update={
            "checkbox_evidence_detection_method": "fixed_zone_disabled",
            "checkbox_evidence_fallback_used": False,
            "checkbox_evidence_anchor_found": None,
            "checkbox_evidence_checkbox_found": None,
        }
    )

    assert "retirement_plan_checkbox_fallback_used" in _checkbox_codes(happy_path_document, signals)


def test_anchor_missing_is_flagged(happy_path_document: W2Document) -> None:
    signals = _TRUSTED_CHECKED_EVIDENCE.model_copy(
        update={
            "checkbox_evidence_detection_method": "fixed_zone_fallback",
            "checkbox_evidence_fallback_used": True,
            "checkbox_evidence_anchor_found": False,
            "checkbox_evidence_checkbox_found": False,
        }
    )

    codes = _checkbox_codes(happy_path_document, signals)
    assert "retirement_plan_checkbox_anchor_missing" in codes


def test_checkbox_not_found_is_flagged(happy_path_document: W2Document) -> None:
    signals = _TRUSTED_CHECKED_EVIDENCE.model_copy(
        update={
            "checkbox_evidence_detection_method": "fixed_zone_fallback",
            "checkbox_evidence_fallback_used": True,
            "checkbox_evidence_anchor_found": True,
            "checkbox_evidence_checkbox_found": False,
        }
    )

    codes = _checkbox_codes(happy_path_document, signals)
    assert "retirement_plan_checkbox_not_found" in codes


def test_anchor_and_checkbox_missing_are_independent_issues(happy_path_document: W2Document) -> None:
    """Both root causes are preserved, not deduplicated -- matching how the
    employer-name signals never suppress one fired issue for another."""

    signals = _TRUSTED_CHECKED_EVIDENCE.model_copy(
        update={
            "checkbox_evidence_detection_method": "fixed_zone_fallback",
            "checkbox_evidence_fallback_used": True,
            "checkbox_evidence_anchor_found": False,
            "checkbox_evidence_checkbox_found": False,
        }
    )

    codes = _checkbox_codes(happy_path_document, signals)
    assert {
        "retirement_plan_checkbox_fallback_used",
        "retirement_plan_checkbox_anchor_missing",
        "retirement_plan_checkbox_not_found",
    } <= codes


def test_strong_positive_margin_passes(happy_path_document: W2Document) -> None:
    signals = _TRUSTED_CHECKED_EVIDENCE.model_copy(update={"checkbox_evidence_decision_margin": 0.15})

    assert _checkbox_codes(happy_path_document, signals) == set()


def test_strong_negative_margin_passes(happy_path_document: W2Document) -> None:
    signals = _TRUSTED_UNCHECKED_EVIDENCE.model_copy(update={"checkbox_evidence_decision_margin": -0.12})

    assert _checkbox_codes(happy_path_document, signals) == set()


def test_near_zero_positive_margin_is_flagged(happy_path_document: W2Document) -> None:
    signals = _TRUSTED_CHECKED_EVIDENCE.model_copy(update={"checkbox_evidence_decision_margin": 0.01})

    assert "retirement_plan_checkbox_low_decision_margin" in _checkbox_codes(happy_path_document, signals)


def test_near_zero_negative_margin_is_flagged(happy_path_document: W2Document) -> None:
    signals = _TRUSTED_UNCHECKED_EVIDENCE.model_copy(update={"checkbox_evidence_decision_margin": -0.01})

    assert "retirement_plan_checkbox_low_decision_margin" in _checkbox_codes(happy_path_document, signals)


def test_margin_boundary_is_deterministic_just_inside_and_outside(
    happy_path_document: W2Document,
) -> None:
    from w2_pipeline.validation.rules import _NEAR_THRESHOLD_DECISION_MARGIN

    just_inside = _TRUSTED_CHECKED_EVIDENCE.model_copy(
        update={"checkbox_evidence_decision_margin": _NEAR_THRESHOLD_DECISION_MARGIN - 0.001}
    )
    exactly_at = _TRUSTED_CHECKED_EVIDENCE.model_copy(
        update={"checkbox_evidence_decision_margin": _NEAR_THRESHOLD_DECISION_MARGIN}
    )
    just_outside = _TRUSTED_CHECKED_EVIDENCE.model_copy(
        update={"checkbox_evidence_decision_margin": _NEAR_THRESHOLD_DECISION_MARGIN + 0.001}
    )

    issues_inside = {issue.code for issue in run_all_rules(happy_path_document, just_inside)}
    issues_at = {issue.code for issue in run_all_rules(happy_path_document, exactly_at)}
    issues_outside = {issue.code for issue in run_all_rules(happy_path_document, just_outside)}

    assert "retirement_plan_checkbox_low_decision_margin" in issues_inside
    # `abs(margin) < threshold` is a strict inequality: exactly at the
    # threshold value does not fire, matching the module's own comparison.
    assert "retirement_plan_checkbox_low_decision_margin" not in issues_at
    assert "retirement_plan_checkbox_low_decision_margin" not in issues_outside


def test_malformed_shape_score_is_flagged(happy_path_document: W2Document) -> None:
    signals = _TRUSTED_CHECKED_EVIDENCE.model_copy(update={"checkbox_evidence_shape_score": 0.2})

    matching = [
        issue
        for issue in run_all_rules(happy_path_document, signals)
        if issue.code == "retirement_plan_checkbox_geometry_anomaly"
    ]
    assert len(matching) == 1
    assert matching[0].observed_value == 0.2


def test_normal_shape_score_not_flagged(happy_path_document: W2Document) -> None:
    assert _checkbox_codes(happy_path_document, _TRUSTED_CHECKED_EVIDENCE) == set()


def test_checkbox_issue_does_not_suppress_employer_name_issues() -> None:
    document = generate_synthetic_w2_documents_for_name("Elan Consulting Corp 2861 Geneva Ponce De Leon Rd")
    signals = ExtractionSignals(route="ocr", employer_name_observation_count=2)

    codes = {issue.code for issue in run_all_rules(document, signals)}

    assert "employer_name_address_leak" in codes
    assert "employer_name_layout_anomaly" in codes
    assert "retirement_plan_checkbox_evidence_missing" in codes


def test_true_and_false_checkbox_values_treated_symmetrically(happy_path_document: W2Document) -> None:
    """Validation must not encode a class prior -- both `True` and `False`
    pass under strong evidence and both review under weak evidence,
    regardless of what document.box_13.retirement_plan actually is."""

    checked_document = happy_path_document.model_copy(
        update={"box_13": happy_path_document.box_13.model_copy(update={"retirement_plan": True})}
    )
    unchecked_document = happy_path_document.model_copy(
        update={"box_13": happy_path_document.box_13.model_copy(update={"retirement_plan": False})}
    )

    weak_signals = ExtractionSignals(route="ocr")

    assert _checkbox_codes(checked_document, _TRUSTED_CHECKED_EVIDENCE) == set()
    assert _checkbox_codes(unchecked_document, _TRUSTED_UNCHECKED_EVIDENCE) == set()
    assert _checkbox_codes(checked_document, weak_signals) == _checkbox_codes(unchecked_document, weak_signals)
