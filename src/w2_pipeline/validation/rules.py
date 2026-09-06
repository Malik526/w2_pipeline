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

# Phase 8C.8: promotes the Phase 8C.5 address-leak heuristic's winning
# candidate (`contains_street_number AND contains_road_suffix`, expanded
# suffix list) into production, unchanged from its evaluation-side form
# in `w2_pipeline.evaluation.employer_name_heuristics` -- same regex,
# same suffix set, same whole-word matching, no tuning, no company-name
# dictionary, no document-specific logic. See
# docs/experiments/phase8c8-promote-employer-name-validator-signals.md.
_EMPLOYER_NAME_STREET_NUMBER_RE = re.compile(r"(?<!\d)\d{1,5}(?!\d)")
_EMPLOYER_NAME_ROAD_SUFFIXES: frozenset[str] = frozenset(
    {
        "st", "street", "ave", "avenue", "rd", "road", "blvd", "lane", "ln",
        "drive", "dr", "highway", "hwy", "court", "ct", "parkway", "pkwy",
        "terrace", "way", "brg", "bridge", "cor", "corridor", "cir", "circle",
        "trl", "trail", "pl", "place", "sq", "square", "loop", "xing",
        "crossing", "aly", "alley", "byp", "bypass", "cswy", "causeway",
        "expy", "expressway", "frwy", "freeway", "tpke", "turnpike", "walk",
        "path", "run", "pass", "trce", "trace", "vw", "view", "holw",
        "hollow", "grn", "green", "mnr", "manor", "spur", "rte", "route",
    }
)
_EMPLOYER_NAME_WORD_RE = re.compile(r"[A-Za-z]+")

# Phase 8C.12: checkbox evidence-quality thresholds for box_13.retirement_plan.
#
# `_NEAR_THRESHOLD_DECISION_MARGIN`: the 600-document Phase 8C.10/8C.11
# benchmark has NO real near-boundary examples to fit a threshold from --
# every unchecked document has interior_ink_ratio exactly 0.0 (decision_margin
# exactly -0.12, a hard floor, not a distribution near the boundary) and
# every checked document is at least 0.124 above the 0.12 threshold (ratio
# 0.244-0.298). There is a clean, unbroken 0.244-wide gap with nothing
# observed inside it. 0.05 is chosen as a conservative buffer that is (a)
# less than half the smallest real separation observed in either direction
# (0.12 unchecked, 0.124 checked), so it provably cannot fire on any of this
# benchmark's 600 real documents, while (b) still being wide enough to catch
# a genuinely ambiguous real-world case this synthetic dataset cannot
# produce -- e.g. print/scan artifacts or a faint partial mark landing
# between roughly 0.07 and 0.17 interior ink ratio. See
# docs/experiments/phase8c12-checkbox-validator.md Section 2 for the full
# distribution analysis this is derived from.
_NEAR_THRESHOLD_DECISION_MARGIN = 0.05

# `_MIN_PLAUSIBLE_SHAPE_SCORE`: shape_score = 1.0 - min(abs(aspect_ratio -
# 1.0), 1.0), so 0.5 means the located candidate's aspect ratio is at least
# 2:1 (or 1:2) -- a shape no square W-2 checkbox glyph can plausibly have.
# This is a broad structural sanity floor, not fit to the benchmark: the
# benchmark's own observed range (0.827-0.880 across all 600 documents,
# tight and resolution/DPI-specific to this one synthetic rendering
# pipeline) is far above 0.5 and is deliberately NOT used as the floor,
# since doing so would overfit this dataset's specific renderer rather than
# reflect a genuine structural implausibility check.
_MIN_PLAUSIBLE_SHAPE_SCORE = 0.5

# `anchor_distance_px` and `horizontal_alignment_offset_px` are preserved on
# `ExtractionSignals` but deliberately have NO numeric rule here: both are
# raw pixel offsets (not normalized by the anchor's own line height, which
# validation does not receive), and the benchmark's observed range (-2 to
# 0px anchor distance, 0-3px alignment offset) is specific to one fixed
# 2550x3300 synthetic render DPI. A raw-pixel threshold calibrated on that
# single resolution would not generalize to a differently-scanned/DPI real
# document -- there is not enough variation in this dataset to justify a
# production threshold for either signal. Both remain available on
# `ExtractionSignals` for the next phase once real-world DPI variation
# exists to calibrate against.

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
    "employer_name_address_leak",
    "employer_name_layout_anomaly",
    "retirement_plan_checkbox_evidence",
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
    issues.extend(_check_employer_name_address_leak(document))
    issues.extend(_check_employer_name_layout_anomaly(document, signals))
    issues.extend(_check_retirement_plan_checkbox_evidence(signals))
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


def _check_employer_name_address_leak(document: W2Document) -> list[ValidationIssue]:
    """Flag `employer.name` values that look like a name with a street
    address appended (Phase 8C.5/8C.8): both a bare street-number-shaped
    digit run AND a whole-word road-suffix abbreviation must be present.
    Requiring both together (never either alone) is what keeps this safe
    against real company names containing a number (`3M Corporation`) or
    an ordinary word that also happens to be a road-suffix abbreviation
    (`Infinite Loop Technologies`) -- see the phase doc for the measured
    false-positive analysis behind this design.
    """

    name = document.employer.name
    if _is_blank(name):
        return []
    has_street_number = bool(_EMPLOYER_NAME_STREET_NUMBER_RE.search(name))
    tokens = {token.lower() for token in _EMPLOYER_NAME_WORD_RE.findall(name)}
    has_road_suffix = not tokens.isdisjoint(_EMPLOYER_NAME_ROAD_SUFFIXES)
    if has_street_number and has_road_suffix:
        return [
            ValidationIssue(
                code="employer_name_address_leak",
                field_path="employer.name",
                severity=ValidationSeverity.ERROR,
                message=(
                    "Employer name contains both a street-number-shaped digit "
                    "and a road-suffix word, consistent with a merged address "
                    "line rather than a company name."
                ),
                observed_value=name,
            )
        ]
    return []


def _check_employer_name_layout_anomaly(
    document: W2Document, signals: ExtractionSignals
) -> list[ValidationIssue]:
    """Flag an `employer.name` whose value was produced from more than one
    OCR observation (Phase 8C.6/8C.8) -- a normal single-line employer
    name always comes from exactly one. Purely geometric: this never
    inspects `employer.name`'s text content, only the layout-provenance
    count the extraction path already computed
    (`ExtractionSignals.employer_name_observation_count`)."""

    count = signals.employer_name_observation_count
    if count is None or count <= 1:
        return []
    return [
        ValidationIssue(
            code="employer_name_layout_anomaly",
            field_path="employer.name",
            severity=ValidationSeverity.ERROR,
            message=(
                f"Employer name was assembled from {count} OCR observations "
                "instead of the normal single line, consistent with a "
                "merged/split extraction artifact."
            ),
            metadata={"observation_count": count},
        )
    ]


def _check_retirement_plan_checkbox_evidence(signals: ExtractionSignals) -> list[ValidationIssue]:
    """Judge `box_13.retirement_plan`'s checkbox-detector evidence quality
    (Phase 8C.12), not the extracted boolean's validity -- a boolean is
    structurally valid even when wrong, which is exactly why the pre-8C.12
    validator silently accepted all 60 Phase 8C.2 checkbox errors. This
    rule is symmetric: `True` and `False` are judged identically, purely
    on whether the evidence behind either value is trustworthy.

    Never re-opens the source image, re-runs OCR, or re-runs checkbox
    localization/classification -- every value here was already computed
    by extraction and threaded through `ExtractionSignals` (Phase 8C.11's
    `Box13CheckboxEvidence`, duplicated as primitives; see that field's
    docstring for why validation does not import the extraction type
    directly).
    """

    method = signals.checkbox_evidence_detection_method
    if method is None:
        # Only Pipeline A's OCR-driven routes ("ocr", image-only PDF pages;
        # "mixed", partially-OCR PDFs) are within Phase 8C.10/8C.11's scope
        # and expected to carry this evidence. Two categories are
        # deliberately exempt, not merely unhandled:
        #   - Pipeline A's `native_pdf` route never runs any image-based
        #     checkbox detector at all -- box_13.retirement_plan comes from
        #     embedded-text-prefix reconstruction instead (see
        #     acquisition.py's `PdfTextMode.EMBEDDED_TEXT` branch, which
        #     never touches checkbox_anchor.py or checkbox_vision.py) -- so
        #     "no evidence" there is a genuinely different mechanism, not a
        #     gap.
        #   - Pipeline B (`route="vlm"` by this project's convention) is an
        #     entirely different, generative pipeline that never produces
        #     this OCR-anchor evidence and is out of this phase's scope --
        #     validate_w2_document is explicitly backend-neutral (see
        #     validator.py's module docstring) and must not penalize a
        #     pipeline this signal was never built for.
        # This is a positive allow-list of the two routes Phase 8C.10/8C.11
        # actually instrument, not a default-deny list: an unset/unknown
        # `route` is exempt too, the same as `native_pdf`/`vlm`, since a
        # route this validator cannot positively identify as
        # anchor-relative-eligible must not be penalized for lacking
        # evidence it was never promised to carry.
        if signals.route not in ("ocr", "mixed"):
            return []
        return [
            ValidationIssue(
                code="retirement_plan_checkbox_evidence_missing",
                field_path="box_13.retirement_plan",
                severity=ValidationSeverity.ERROR,
                message=(
                    "No box_13.retirement_plan checkbox-detector evidence was supplied "
                    "for this extraction route, so the extracted value cannot be "
                    "verified as coming from the trusted anchor-relative detector."
                ),
                metadata={"route": signals.route} if signals.route is not None else {},
            )
        ]

    issues: list[ValidationIssue] = []

    # Rule 1: anything other than the promoted anchor-relative detector --
    # whether an explicit fallback (fixed_zone_fallback) or a deliberate
    # diagnostic override (fixed_zone_disabled, never expected in
    # production per Phase 8C.11) -- used the legacy fixed-zone mechanism,
    # which has a known historical rotation defect (Phase 8C.2: 60/600
    # box_13.retirement_plan failures, all fixed-zone).
    if signals.checkbox_evidence_fallback_used or method != "anchor_relative":
        issues.append(
            ValidationIssue(
                code="retirement_plan_checkbox_fallback_used",
                field_path="box_13.retirement_plan",
                severity=ValidationSeverity.ERROR,
                message=(
                    f"box_13.retirement_plan was produced by {method!r}, not the "
                    "promoted anchor-relative detector; the legacy fixed-zone "
                    "mechanism has a known historical rotation defect and is not "
                    "safe for automatic acceptance."
                ),
                observed_value=method,
            )
        )

    # Rule 2: localization failures. Independent of Rule 1 and of each
    # other by design -- a document can be missing both the anchor and the
    # checkbox candidate, and each is its own root cause worth preserving.
    if signals.checkbox_evidence_anchor_found is False:
        issues.append(
            ValidationIssue(
                code="retirement_plan_checkbox_anchor_missing",
                field_path="box_13.retirement_plan",
                severity=ValidationSeverity.ERROR,
                message='The "Retirement plan" label anchor could not be localized in OCR output.',
            )
        )
    if signals.checkbox_evidence_checkbox_found is False:
        issues.append(
            ValidationIssue(
                code="retirement_plan_checkbox_not_found",
                field_path="box_13.retirement_plan",
                severity=ValidationSeverity.ERROR,
                message="No checkbox border candidate could be localized near the anchor.",
            )
        )

    # Rule 3: decision-margin quality -- see _NEAR_THRESHOLD_DECISION_MARGIN
    # above for the full derivation. Symmetric: fires the same way whether
    # the ambiguous ratio would classify as checked or unchecked.
    margin = signals.checkbox_evidence_decision_margin
    if margin is not None and abs(margin) < _NEAR_THRESHOLD_DECISION_MARGIN:
        issues.append(
            ValidationIssue(
                code="retirement_plan_checkbox_low_decision_margin",
                field_path="box_13.retirement_plan",
                severity=ValidationSeverity.ERROR,
                message=(
                    f"Checkbox interior ink ratio is within {_NEAR_THRESHOLD_DECISION_MARGIN} "
                    "of the calibrated checked/unchecked threshold, an ambiguous "
                    "classification margin."
                ),
                observed_value=margin,
            )
        )

    # Rule 4: geometry sanity -- see _MIN_PLAUSIBLE_SHAPE_SCORE above for
    # why only this one broad structural bound is implemented.
    shape_score = signals.checkbox_evidence_shape_score
    if shape_score is not None and shape_score < _MIN_PLAUSIBLE_SHAPE_SCORE:
        issues.append(
            ValidationIssue(
                code="retirement_plan_checkbox_geometry_anomaly",
                field_path="box_13.retirement_plan",
                severity=ValidationSeverity.ERROR,
                message=(
                    f"Checkbox candidate shape_score {shape_score:.3f} is far from "
                    f"square (below the {_MIN_PLAUSIBLE_SHAPE_SCORE} structural sanity "
                    "floor), consistent with a malformed localization rather than a "
                    "real checkbox."
                ),
                observed_value=shape_score,
            )
        )

    return issues


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
