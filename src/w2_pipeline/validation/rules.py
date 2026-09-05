"""Phase 6 deterministic validation rules over a canonical W2Document.

Each `_check_*` function is one independent, named rule: it always runs
(given a non-`None` document) and returns zero or more `ValidationIssue`
values. Rules never mutate the document and never require ground truth --
only the canonical `W2Document` contract and the small set of already-
documented W-2 semantics referenced inline below.

Required-field decisions are evidence-based from two sources already in
this repository: `docs/contracts/canonical-w2-schema.md` (which fields
exist and what nullability means) and
`src/w2_pipeline/evaluation/synthetic.py` (the project's own reference
generator, which deliberately leaves `employee.middle_initial`,
`employee.suffix`, `employer.control_number`, and federal Boxes 3/4/7/8/10/11
`None` on various samples -- confirming those are legitimately optional --
while always populating `employee.ssn`/`first_name`/`last_name`,
`employer.ein`/`name`, and federal Boxes 1/2/5/6). See
`docs/contracts/validation-and-routing.md` for the full rationale and the
complete list of rules this module implements.

Format rules (SSN/EIN shape, Box 12 code shape, money sign/precision) use
only structural patterns already documented for Form W-2 (SSN
`XXX-XX-XXXX`, EIN `XX-XXXXXXX`, Box 12 codes are 1-2 uppercase letters,
money is never negative and has at most 2 decimal places). No tax-law
numeric relationship (e.g. a required ratio between boxes) is invented;
none is implemented here.
"""

from __future__ import annotations

from decimal import Decimal
import re

from w2_pipeline.contracts.w2 import Box12Entry, StateLocalEntry, W2Document
from w2_pipeline.validation.models import (
    ExtractionOutcome,
    ExtractionSignals,
    ValidationIssue,
    ValidationSeverity,
)
from w2_pipeline.validation.redaction import redact_value

SUPPORTED_TAX_YEAR = 2026
SUPPORTED_SCHEMA_VERSION = 2026
SUPPORTED_DOCUMENT_TYPE = "W-2"

_SSN_RE = re.compile(r"^\d{3}-\d{2}-\d{4}$")
_EIN_RE = re.compile(r"^\d{2}-\d{7}$")
_BOX_12_CODE_RE = re.compile(r"^[A-Z]{1,2}$")

# Ordered so `checks_run` (== len(ALL_RULES)) reads top-to-bottom the same
# way the module docstring and docs/contracts/validation-and-routing.md
# describe the categories: signals, then required fields, then format,
# then domain/structural checks.
ALL_RULE_NAMES = (
    "extraction_signals",
    "supported_metadata",
    "employee_identity_required_fields",
    "ssn_format",
    "employer_identity_required_fields",
    "ein_format",
    "core_wage_tax_fields_required",
    "monetary_fields_valid",
    "box_12_code_format",
    "no_empty_state_local_entries",
)


def run_all_rules(document: W2Document, signals: ExtractionSignals) -> list[ValidationIssue]:
    """Run every Phase 6 rule and return the combined issue list.

    `len(ALL_RULE_NAMES)` is the canonical `checks_run` count for this path
    (the document-is-`None` short-circuit in `validator.py` reports its own
    count of 1 instead, since none of these rules can run without a
    document).
    """

    issues: list[ValidationIssue] = []
    issues.extend(_check_extraction_signals(signals))
    issues.extend(_check_supported_metadata(document))
    issues.extend(_check_employee_identity_required_fields(document))
    issues.extend(_check_ssn_format(document))
    issues.extend(_check_employer_identity_required_fields(document))
    issues.extend(_check_ein_format(document))
    issues.extend(_check_core_wage_tax_fields_required(document))
    issues.extend(_check_monetary_fields_valid(document))
    issues.extend(_check_box_12_code_format(document))
    issues.extend(_check_no_empty_state_local_entries(document))
    return issues


def _check_extraction_signals(signals: ExtractionSignals) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if signals.outcome != ExtractionOutcome.SUCCEEDED:
        issues.append(
            ValidationIssue(
                code="extraction_failure",
                severity=ValidationSeverity.ERROR,
                message=f"Extraction reported outcome {signals.outcome.value!r} instead of success.",
                metadata={"pipeline_id": signals.pipeline_id} if signals.pipeline_id else {},
            )
        )
    for warning in signals.warnings:
        issues.append(
            ValidationIssue(
                code="extraction_warning",
                severity=ValidationSeverity.WARNING,
                message=warning,
            )
        )
    return issues


def _check_supported_metadata(document: W2Document) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    metadata = document.metadata
    if metadata.document_type != SUPPORTED_DOCUMENT_TYPE:
        issues.append(
            ValidationIssue(
                code="unsupported_document_type",
                field_path="metadata.document_type",
                severity=ValidationSeverity.ERROR,
                message=(
                    f"Document type {metadata.document_type!r} is not the supported "
                    f"{SUPPORTED_DOCUMENT_TYPE!r} type."
                ),
                observed_value=metadata.document_type,
            )
        )
    if metadata.tax_year != SUPPORTED_TAX_YEAR:
        issues.append(
            ValidationIssue(
                code="tax_year_mismatch",
                field_path="metadata.tax_year",
                severity=ValidationSeverity.ERROR,
                message=(
                    f"Tax year {metadata.tax_year} is not the supported "
                    f"{SUPPORTED_TAX_YEAR} production target."
                ),
                observed_value=metadata.tax_year,
            )
        )
    if metadata.schema_version != SUPPORTED_SCHEMA_VERSION:
        issues.append(
            ValidationIssue(
                code="unsupported_schema_version",
                field_path="metadata.schema_version",
                severity=ValidationSeverity.ERROR,
                message=(
                    f"Schema version {metadata.schema_version} is not the supported "
                    f"{SUPPORTED_SCHEMA_VERSION} contract."
                ),
                observed_value=metadata.schema_version,
            )
        )
    return issues


def _check_employee_identity_required_fields(document: W2Document) -> list[ValidationIssue]:
    employee = document.employee
    required = {
        "employee.ssn": employee.ssn,
        "employee.first_name": employee.first_name,
        "employee.last_name": employee.last_name,
    }
    return [
        _missing_field_issue(field_path)
        for field_path, value in required.items()
        if _is_blank(value)
    ]


def _check_ssn_format(document: W2Document) -> list[ValidationIssue]:
    ssn = document.employee.ssn
    if _is_blank(ssn) or _SSN_RE.match(ssn):
        return []
    return [
        ValidationIssue(
            code="invalid_ssn_format",
            field_path="employee.ssn",
            severity=ValidationSeverity.ERROR,
            message="Employee SSN does not match the expected XXX-XX-XXXX format.",
            observed_value=redact_value("employee.ssn", ssn),
        )
    ]


def _check_employer_identity_required_fields(document: W2Document) -> list[ValidationIssue]:
    employer = document.employer
    required = {
        "employer.ein": employer.ein,
        "employer.name": employer.name,
    }
    return [
        _missing_field_issue(field_path)
        for field_path, value in required.items()
        if _is_blank(value)
    ]


def _check_ein_format(document: W2Document) -> list[ValidationIssue]:
    ein = document.employer.ein
    if _is_blank(ein) or _EIN_RE.match(ein):
        return []
    return [
        ValidationIssue(
            code="invalid_ein_format",
            field_path="employer.ein",
            severity=ValidationSeverity.ERROR,
            message="Employer EIN does not match the expected XX-XXXXXXX format.",
            observed_value=redact_value("employer.ein", ein),
        )
    ]


def _check_core_wage_tax_fields_required(document: W2Document) -> list[ValidationIssue]:
    federal = document.federal_wages_and_taxes
    required = {
        "federal_wages_and_taxes.box_1_wages_tips_other_compensation": federal.box_1_wages_tips_other_compensation,
        "federal_wages_and_taxes.box_2_federal_income_tax_withheld": federal.box_2_federal_income_tax_withheld,
        "federal_wages_and_taxes.box_5_medicare_wages_and_tips": federal.box_5_medicare_wages_and_tips,
        "federal_wages_and_taxes.box_6_medicare_tax_withheld": federal.box_6_medicare_tax_withheld,
    }
    return [
        _missing_field_issue(field_path)
        for field_path, value in required.items()
        if value is None
    ]


def _check_monetary_fields_valid(document: W2Document) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    federal = document.federal_wages_and_taxes
    federal_money_fields = (
        "box_1_wages_tips_other_compensation",
        "box_2_federal_income_tax_withheld",
        "box_3_social_security_wages",
        "box_4_social_security_tax_withheld",
        "box_5_medicare_wages_and_tips",
        "box_6_medicare_tax_withheld",
        "box_7_social_security_tips",
        "box_8_allocated_tips",
        "box_10_dependent_care_benefits",
        "box_11_nonqualified_plans",
    )
    for name in federal_money_fields:
        issues.extend(
            _money_issues(f"federal_wages_and_taxes.{name}", getattr(federal, name))
        )

    for index, entry in enumerate(document.box_12_entries):
        issues.extend(_money_issues(f"box_12_entries[{index}].amount", entry.amount))

    for index, entry in enumerate(document.box_14_entries):
        issues.extend(_money_issues(f"box_14_entries[{index}].amount", entry.amount))

    state_local_money_fields = (
        "box_16_state_wages_tips_etc",
        "box_17_state_income_tax",
        "box_18_local_wages_tips_etc",
        "box_19_local_income_tax",
    )
    for index, entry in enumerate(document.state_local_entries):
        for name in state_local_money_fields:
            issues.extend(
                _money_issues(
                    f"state_local_entries[{index}].{name}", getattr(entry, name)
                )
            )
    return issues


def _check_box_12_code_format(document: W2Document) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for index, entry in enumerate(document.box_12_entries):
        issues.extend(_box_12_code_issues(index, entry))
    return issues


def _box_12_code_issues(index: int, entry: Box12Entry) -> list[ValidationIssue]:
    if _BOX_12_CODE_RE.match(entry.code):
        return []
    return [
        ValidationIssue(
            code="invalid_box12_code_format",
            field_path=f"box_12_entries[{index}].code",
            severity=ValidationSeverity.ERROR,
            message=(
                f"Box 12 code {entry.code!r} is not 1-2 uppercase letters. Real IRS "
                "Box 12 codes are always 1-2 uppercase letters, so this is almost "
                "certainly an extraction artifact rather than a real code."
            ),
            observed_value=entry.code,
        )
    ]


def _check_no_empty_state_local_entries(document: W2Document) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for index, entry in enumerate(document.state_local_entries):
        if _is_entirely_blank_state_local_entry(entry):
            issues.append(
                ValidationIssue(
                    code="empty_entry",
                    field_path=f"state_local_entries[{index}]",
                    severity=ValidationSeverity.WARNING,
                    message=(
                        "State/local entry has no populated fields; this is likely a "
                        "spurious extraction artifact rather than a real row."
                    ),
                )
            )
    return issues


def _is_entirely_blank_state_local_entry(entry: StateLocalEntry) -> bool:
    return all(value is None for value in entry.model_dump(mode="python").values())


def _money_issues(field_path: str, value: Decimal | None) -> list[ValidationIssue]:
    if value is None:
        return []
    issues: list[ValidationIssue] = []
    if value < 0:
        issues.append(
            ValidationIssue(
                code="invalid_money_value",
                field_path=field_path,
                severity=ValidationSeverity.ERROR,
                message="Monetary W-2 fields cannot be negative.",
                observed_value=str(value),
            )
        )
    exponent = value.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -2:
        issues.append(
            ValidationIssue(
                code="invalid_money_value",
                field_path=field_path,
                severity=ValidationSeverity.ERROR,
                message="Monetary W-2 fields cannot have more than 2 decimal places.",
                observed_value=str(value),
            )
        )
    return issues


def _missing_field_issue(field_path: str) -> ValidationIssue:
    return ValidationIssue(
        code="required_field_missing",
        field_path=field_path,
        severity=ValidationSeverity.ERROR,
        message=f"{field_path} is required but was not extracted.",
    )


def _is_blank(value: str | None) -> bool:
    return value is None or value.strip() == ""
