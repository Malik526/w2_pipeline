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
    assert len(ALL_RULE_NAMES) == 10
