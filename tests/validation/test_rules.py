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
    assert len(ALL_RULE_NAMES) == 12


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
