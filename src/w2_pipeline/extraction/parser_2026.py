"""Deterministic 2026 W-2 parser over common text/layout observations."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
import re
from pathlib import Path

from w2_pipeline.contracts.w2 import (
    Address,
    Box12Entry,
    Box13Flags,
    Box14Entry,
    Employee,
    Employer,
    FederalWagesAndTaxes,
    SourceFileType,
    StateLocalEntry,
    TippedOccupationCode,
    W2Document,
    W2Metadata,
)
from w2_pipeline.contracts.employee_name import (
    parse_employee_name,
    split_first_name_and_initial,
)
from w2_pipeline.extraction.models import (
    AcquisitionRoute,
    ExtractionWarning,
    ObservationSet,
    ObservationSource,
    TextObservation,
)
from w2_pipeline.ingestion.models import SourceDocumentType

_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_EIN_RE = re.compile(r"\b\d{2}-\d{7}\b")
_MONEY_RE = re.compile(r"^\$?\s*-?\d{1,3}(?:,\d{3})*(?:\.\d{2})?$|^\$?\s*-?\d+(?:\.\d{2})?$")
_BOX_RE = re.compile(r"^(?P<number>\d{1,2})\s+(?P<label>[^:]+):\s*(?P<value>.*)$")
_BOX_12_RE = re.compile(r"^12\s+(?P<code>[A-Z]{1,2}):\s*(?P<value>.*)$")
_BOX_14A_RE = re.compile(r"^14a\s+(?P<label>[^:]+):\s*(?P<value>.*)$")
_BOX_14B_RE = re.compile(r"^14b\s+code\s+\d+:\s*(?P<value>.*)$", re.IGNORECASE)
_STATE_LOCAL_RE = re.compile(
    r"^(?P<number>1[5-9]|20)\.(?P<row>\d+)\s+(?P<label>[^:]+):\s*(?P<value>.*)$"
)

# Named (not inline-literal) so `compute_employer_name_observation_count`
# (used by `PipelineAExtractor` to produce a validator-facing layout
# signal, Phase 8C.8) can reuse the exact same zone the employer.name
# fallback below uses, rather than risk drifting out of sync with a
# duplicated literal.
EMPLOYER_NAME_ZONE: tuple[float, float, float, float] = (0.04, 0.35, 0.25, 0.33)

# Phase 8D.1A: Box c's combined block is name + street + "City, ST ZIP",
# three lines -- `EMPLOYER_NAME_ZONE` above only needs to stretch far
# enough to catch the topmost (name) line, but address recovery needs all
# three. `_row_texts_in_zone`'s address-only callers use this taller
# zone instead of widening `EMPLOYER_NAME_ZONE` itself (which is also
# reused as-is by earlier phases' employer.name path and 8C.8's
# `compute_employer_name_observation_count` -- touching its bounds would
# risk perturbing already-benchmarked behavior for a field this phase
# does not need to change). Calibrated against a rotated real document,
# where the block's ratio position shifts measurably (0.29-0.37 vs.
# 0.25-0.34 on the clean render) yet stays well clear of Box d ("Control
# number", ratio ~0.46) either way.
EMPLOYER_ADDRESS_ZONE: tuple[float, float, float, float] = (0.04, 0.35, 0.25, 0.39)

# The real 2026 W-2 form's Box f ("Employee's address and ZIP code") is
# the same kind of unlabeled, position-only block as Box c -- street
# address on one line, "City, ST ZIP" on the next -- calibrated the same
# way (against `_layout_extent`, not raw image pixels) from real
# PaddleOCR observations on the external Symage clean render. Box e's
# name row sits close enough above this zone that a small rotation-
# induced ratio shift can pull the name row inside it too (observed
# directly: "Steven D" at ratio y 0.527-0.552 under this dataset's 2deg
# rotation vs. this zone's y0=0.53) -- `_looks_like_employee_name_row`
# below guards against that specifically, since tightening the zone
# boundary further would just move the same collision to a different
# rotation angle.
EMPLOYEE_ADDRESS_ZONE: tuple[float, float, float, float] = (0.04, 0.30, 0.53, 0.61)

# Box 12's four code/amount slots (12a-12d): the code letter and its
# amount sit in two distinct columns, calibrated the same way. Paired by
# nearest row (vertical center), not list position -- a blank code slot
# prints no OCR observation at all (unlike a blank amount slot, which
# still prints "$0.00"), so index-based zipping would misalign slots
# once any code is missing.
BOX_12_CODE_ZONE: tuple[float, float, float, float] = (0.78, 0.87, 0.44, 0.76)
BOX_12_AMOUNT_ZONE: tuple[float, float, float, float] = (0.90, 1.00, 0.44, 0.76)
_BOX_12_CODE_TOKEN_RE = re.compile(r"^[A-Z]{1,2}$")
_STATE_CODE_RE = re.compile(r"^[A-Z]{2}$")
_STATE_ID_RE = re.compile(r"^\d+(?:[/-]\d+)+$")

# Boxes 15-20 print their own box-number label directly in OCR text
# ("15 State", "16 State wages, tips, etc.", ...), unlike Box c/f -- so
# each value sits in its own fixed zone the same way Boxes 1-11 already
# do in `_apply_ocr_federal_layout_fallbacks`, rather than needing
# row-grouping. Local wages/tax/locality (18-20) are calibrated from the
# same real document even though this dataset never populates them
# (0/150 in the annotation-coverage audit), so a real-world document that
# does populate them is still handled.
_STATE_LOCAL_VALUE_ZONES: dict[str, tuple[float, float, float, float]] = {
    "box_15_state": (0.055, 0.125, 0.77, 0.83),
    "box_15_employer_state_id_number": (0.155, 0.285, 0.77, 0.83),
    "box_16_state_wages_tips_etc": (0.365, 0.50, 0.77, 0.83),
    "box_17_state_income_tax": (0.53, 0.635, 0.77, 0.83),
    "box_18_local_wages_tips_etc": (0.615, 0.79, 0.77, 0.835),
    "box_19_local_income_tax": (0.765, 0.91, 0.77, 0.835),
    "box_20_locality_name": (0.90, 1.00, 0.77, 0.835),
}
_STATE_LOCAL_MONEY_FIELDS = frozenset(
    {
        "box_16_state_wages_tips_etc",
        "box_17_state_income_tax",
        "box_18_local_wages_tips_etc",
        "box_19_local_income_tax",
    }
)

_FEDERAL_MONEY_FIELDS = {
    1: "box_1_wages_tips_other_compensation",
    2: "box_2_federal_income_tax_withheld",
    3: "box_3_social_security_wages",
    4: "box_4_social_security_tax_withheld",
    5: "box_5_medicare_wages_and_tips",
    6: "box_6_medicare_tax_withheld",
    7: "box_7_social_security_tips",
    8: "box_8_allocated_tips",
    10: "box_10_dependent_care_benefits",
    11: "box_11_nonqualified_plans",
}


def parse_w2_2026_observations(
    observation_set: ObservationSet,
    *,
    document_id: str,
    source_filename: str | None,
    source_type: SourceDocumentType,
) -> tuple[W2Document, list[ExtractionWarning]]:
    """Parse text observations into the canonical 2026 W-2 contract."""

    observations = sorted(
        observation_set.observations,
        key=lambda observation: (observation.page, observation.bbox.y0, observation.bbox.x0),
    )
    # Primary row/line reconstruction only ever sees the main OCR pass: a
    # targeted supplemental pass (e.g. PSM 11's box-3/5/6 recovery) shares
    # physical page regions with primary-path box lines, so merging it into
    # row grouping could duplicate or corrupt an already-correct line. It
    # still reaches every OCR fallback below via the full `observations`
    # list, which is exactly where a targeted pass is meant to help: those
    # fallbacks only ever fire when the primary path left a field empty.
    primary_observations = [
        observation for observation in observations if not observation.is_supplemental
    ]
    group_word_rows = observation_set.route in {AcquisitionRoute.OCR, AcquisitionRoute.MIXED}
    lines = _line_texts(primary_observations, group_word_rows=group_word_rows)
    warnings: list[ExtractionWarning] = []
    employee = _parse_employee(observations, warnings)
    employer = _parse_employer(observations, warnings)
    federal = _parse_federal(lines, warnings)
    if _has_ocr_observations(observations):
        federal = _apply_ocr_federal_layout_fallbacks(federal, observations, warnings)
    box_12_entries = _parse_box_12(lines, warnings)
    if not box_12_entries and _has_ocr_observations(observations):
        box_12_entries = _apply_ocr_box_12_layout_fallback(observations, warnings)
    box_13 = _parse_box_13(lines, observations, observation_set.box_13_visual_marks)
    box_14_entries, tipped_codes = _parse_box_14(lines, warnings)
    state_local_entries = _parse_state_local(lines, warnings)
    if not state_local_entries and _has_ocr_observations(observations):
        state_local_entries = _apply_ocr_state_local_layout_fallback(observations, warnings)

    document = W2Document(
        metadata=W2Metadata(
            document_type="W-2",
            tax_year=2026,
            schema_version=2026,
            document_id=document_id,
            source_filename=source_filename,
            source_file_type=_source_file_type(source_type),
        ),
        employee=employee,
        employer=employer,
        federal_wages_and_taxes=federal,
        box_12_entries=box_12_entries,
        box_13=box_13,
        box_14_entries=box_14_entries,
        tipped_occupation_codes=tipped_codes,
        state_local_entries=state_local_entries,
    )
    return document, warnings


def parse_money(value: str, *, field_path: str) -> Decimal | None:
    """Parse W-2 money text into Decimal without float conversion."""

    stripped = value.strip()
    if not stripped:
        return None
    if not _MONEY_RE.match(stripped):
        raise ValueError(f"Invalid monetary value for {field_path}: {value!r}")
    try:
        return Decimal(stripped.replace("$", "").replace(",", "").strip())
    except InvalidOperation as exc:
        raise ValueError(f"Invalid monetary value for {field_path}: {value!r}") from exc


def _line_texts(
    observations: list[TextObservation],
    *,
    group_word_rows: bool,
) -> list[str]:
    if not group_word_rows:
        return [observation.text.strip() for observation in observations if observation.text.strip()]

    return [
        " ".join(observation.text.strip() for observation in row if observation.text.strip())
        for row in _group_observation_rows(observations)
    ]


def _group_observation_rows(observations: list[TextObservation]) -> list[list[TextObservation]]:
    sorted_observations = sorted(
        observations,
        key=lambda observation: (
            observation.page,
            _vertical_center(observation),
            observation.bbox.x0,
        ),
    )
    rows: list[tuple[int, float, list[TextObservation]]] = []
    for observation in sorted_observations:
        center = _vertical_center(observation)
        tolerance = max(6.0, (observation.bbox.y1 - observation.bbox.y0) * 0.65)
        for row_index, (page, row_center, row_observations) in enumerate(rows):
            if page == observation.page and abs(row_center - center) <= tolerance:
                row_observations.append(observation)
                new_center = (
                    row_center * (len(row_observations) - 1) + center
                ) / len(row_observations)
                rows[row_index] = (page, new_center, row_observations)
                break
        else:
            rows.append((observation.page, center, [observation]))

    return [
        sorted(row_observations, key=lambda observation: observation.bbox.x0)
        for _, _, row_observations in rows
    ]


def _vertical_center(observation: TextObservation) -> float:
    return (observation.bbox.y0 + observation.bbox.y1) / 2


def _parse_employee(
    observations: list[TextObservation],
    warnings: list[ExtractionWarning],
) -> Employee:
    left_lines = _observations_in_x_range(observations, max_x=300)
    name_value = _value_after_label(left_lines, "Name")
    parsed_name = parse_employee_name(name_value)
    city, state, postal_code = _parse_city_state_zip(_value_after_label(left_lines, "City/State/ZIP"))
    employee = Employee(
        ssn=_first_match(_value_after_label(left_lines, "SSN"), _SSN_RE),
        first_name=parsed_name.first_name,
        middle_initial=parsed_name.middle_initial,
        last_name=parsed_name.last_name,
        suffix=parsed_name.suffix,
        address=Address(
            address_line_1=_empty_to_none(_value_after_label(left_lines, "Address 1")),
            address_line_2=_empty_to_none(_value_after_label(left_lines, "Address 2")),
            city=city,
            state=state,
            postal_code=postal_code,
            country="US" if city or state or postal_code else None,
        ),
    )
    if _has_ocr_observations(observations):
        employee = _apply_ocr_employee_layout_fallbacks(employee, observations)
    return employee


def _parse_employer(
    observations: list[TextObservation],
    warnings: list[ExtractionWarning],
) -> Employer:
    right_lines = _observations_in_x_range(observations, min_x=300)
    city, state, postal_code = _parse_city_state_zip(_value_after_label(right_lines, "City/State/ZIP"))
    employer = Employer(
        ein=_first_match(_value_after_label(right_lines, "EIN"), _EIN_RE),
        name=_empty_to_none(_value_after_label(right_lines, "Name")),
        address=Address(
            address_line_1=_empty_to_none(_value_after_label(right_lines, "Address 1")),
            address_line_2=_empty_to_none(_value_after_label(right_lines, "Address 2")),
            city=city,
            state=state,
            postal_code=postal_code,
            country="US" if city or state or postal_code else None,
        ),
        control_number=_empty_to_none(_value_after_label(right_lines, "Control")),
    )
    if _has_ocr_observations(observations):
        employer = _apply_ocr_employer_layout_fallbacks(employer, observations)
    return employer


def _parse_federal(lines: list[str], warnings: list[ExtractionWarning]) -> FederalWagesAndTaxes:
    federal = FederalWagesAndTaxes()
    for line in lines:
        match = _BOX_RE.match(line)
        if not match:
            continue
        number = int(match.group("number"))
        field_name = _FEDERAL_MONEY_FIELDS.get(number)
        if field_name is None:
            continue
        field_path = f"federal_wages_and_taxes.{field_name}"
        try:
            value = parse_money(match.group("value"), field_path=field_path)
        except ValueError as exc:
            warnings.append(ExtractionWarning(field_path=field_path, message=str(exc)))
            value = None
        setattr(federal, field_name, value)
    return federal


def _apply_ocr_federal_layout_fallbacks(
    federal: FederalWagesAndTaxes,
    observations: list[TextObservation],
    warnings: list[ExtractionWarning],
) -> FederalWagesAndTaxes:
    if not _looks_like_full_page_ocr_form(observations):
        return federal

    zones = {
        1: (0.55, 0.80, 0.185, 0.230),
        2: (0.80, 1.00, 0.185, 0.230),
        3: (0.55, 0.80, 0.245, 0.290),
        4: (0.80, 1.00, 0.245, 0.290),
        5: (0.55, 0.80, 0.300, 0.345),
        6: (0.80, 1.00, 0.300, 0.350),
        7: (0.55, 0.80, 0.355, 0.415),
        8: (0.80, 1.00, 0.355, 0.415),
        10: (0.80, 1.00, 0.405, 0.470),
        11: (0.55, 0.80, 0.450, 0.500),
    }
    for box_number, zone in zones.items():
        field_name = _FEDERAL_MONEY_FIELDS.get(box_number)
        if field_name is None or getattr(federal, field_name) is not None:
            continue
        value_text = _first_money_text_in_zone(observations, zone)
        if value_text is None:
            continue
        field_path = f"federal_wages_and_taxes.{field_name}"
        try:
            setattr(federal, field_name, parse_money(value_text, field_path=field_path))
        except ValueError as exc:
            warnings.append(ExtractionWarning(field_path=field_path, message=str(exc)))

    return federal


def _parse_box_12(lines: list[str], warnings: list[ExtractionWarning]) -> list[Box12Entry]:
    entries: list[Box12Entry] = []
    for line in lines:
        match = _BOX_12_RE.match(line)
        if not match:
            continue
        try:
            amount = parse_money(match.group("value"), field_path="box_12_entries.amount")
        except ValueError as exc:
            warnings.append(ExtractionWarning(field_path="box_12_entries.amount", message=str(exc)))
            continue
        if amount is None:
            continue
        entries.append(Box12Entry(code=match.group("code"), amount=amount))
    return entries


def _parse_box_13(
    lines: list[str],
    observations: list[TextObservation],
    box_13_visual_marks: dict[str, bool],
) -> Box13Flags:
    box_13 = Box13Flags(
        statutory_employee=_checkbox_value(_value_after_prefix(lines, "13 Statutory employee")),
        retirement_plan=_checkbox_value(_value_after_prefix(lines, "13 Retirement plan")),
        third_party_sick_pay=_checkbox_value(_value_after_prefix(lines, "13 Third-party sick pay")),
    )
    if _has_ocr_observations(observations):
        box_13 = _apply_ocr_box_13_layout_fallbacks(box_13, observations, box_13_visual_marks)
    return box_13


def _apply_ocr_employee_layout_fallbacks(
    employee: Employee,
    observations: list[TextObservation],
) -> Employee:
    if not _looks_like_full_page_ocr_form(observations):
        return employee

    updates: dict[str, object] = {}
    if employee.ssn is None:
        updates["ssn"] = _first_regex_text_in_zone(observations, _SSN_RE, (0.25, 0.55, 0.10, 0.17))
    if employee.first_name is None:
        first_name, middle_initial = split_first_name_and_initial(
            _zone_text(
                observations,
                (0.04, 0.28, 0.505, 0.550),
                discard_tiny_artifacts=True,
            )
            or ""
        )
        updates["first_name"] = first_name
        if employee.middle_initial is None:
            updates["middle_initial"] = middle_initial
    if employee.last_name is None:
        updates["last_name"] = _zone_text(
            observations,
            (0.28, 0.50, 0.505, 0.555),
            discard_tiny_artifacts=True,
        )
    if employee.suffix is None:
        updates["suffix"] = _zone_text(
            observations,
            (0.50, 0.58, 0.505, 0.555),
            discard_tiny_artifacts=True,
        )
    if employee.address.address_line_1 is None:
        skip_name_row = _make_employee_name_row_filter(
            first_name=updates.get("first_name", employee.first_name),
            middle_initial=updates.get("middle_initial", employee.middle_initial),
            last_name=updates.get("last_name", employee.last_name),
            suffix=updates.get("suffix", employee.suffix),
        )
        address_update = _address_from_two_line_block(
            _row_texts_in_zone(observations, EMPLOYEE_ADDRESS_ZONE, skip_row=skip_name_row),
            employee.address,
        )
        if address_update is not None:
            updates["address"] = address_update
    return employee.model_copy(update=updates)


def _make_employee_name_row_filter(
    *,
    first_name: str | None,
    middle_initial: str | None,
    last_name: str | None,
    suffix: str | None,
) -> Callable[[str], bool]:
    """Build a `skip_row` predicate excluding rows that are the employee's
    own name, not their address (Phase 8D.1A).

    Box e's name row sits close enough above `EMPLOYEE_ADDRESS_ZONE` that
    a small rotation-induced ratio shift can pull it inside that zone
    too (see the zone's own docstring) -- filtering by the name value
    already resolved elsewhere in this same function is more robust
    than trying to tighten a zone boundary that is already this tight in
    the non-rotated case.
    """

    name_rows = {
        normalized
        for normalized in (
            " ".join(part for part in (first_name, middle_initial) if part),
            last_name,
            suffix,
        )
        if normalized
    }
    normalized_name_rows = {value.strip().casefold() for value in name_rows}

    def skip_row(row_text: str) -> bool:
        return row_text.strip().casefold() in normalized_name_rows

    return skip_row


def _address_from_two_line_block(rows: list[str], existing: Address) -> Address | None:
    """Build an `Address` update from a street-line + "City, ST ZIP"-line
    block (Phase 8D.1A) -- the shape Box f (employee) always uses, and
    Box c (employer) uses starting from its second line. `None` when the
    block has fewer than two rows (nothing safely parseable), never a
    partially-fabricated address."""

    if len(rows) < 2:
        return None
    street, city_state_zip = rows[0], rows[1]
    city, state, postal_code = _parse_city_state_zip(city_state_zip)
    return existing.model_copy(
        update={
            "address_line_1": _empty_to_none(street),
            "city": city,
            "state": state,
            "postal_code": postal_code,
            "country": "US" if (city or state or postal_code) else existing.country,
        }
    )


def _apply_ocr_employer_layout_fallbacks(
    employer: Employer,
    observations: list[TextObservation],
) -> Employer:
    """OCR full-page zone fallbacks for employer fields the label-based
    primary path cannot reach.

    The real 2026 W-2 form (and the external Symage renders that
    replicate it) presents Box c as one combined, unlabeled multi-line
    block: "Employer's name, address, and ZIP code" with the employer's
    name as its first printed line and street/city-state-ZIP as
    subsequent lines -- there is no literal "Name:" text for
    `_value_after_label` to match, unlike the internal synthetic
    generator's own rendering convention. `employer.name` therefore had
    no OCR recovery path at all until this fallback was added (unlike
    `_apply_ocr_employee_layout_fallbacks`, which already covers
    SSN/first/last/suffix); see
    docs/experiments/phase6b-employer-name-investigation.md for the
    original diagnosis and
    docs/experiments/phase8c1-employer-name-rotation-remediation.md for
    the rotation-specific label-row skip added afterward.
    """

    if not _looks_like_full_page_ocr_form(observations):
        return employer

    updates: dict[str, object] = {}
    if employer.ein is None:
        updates["ein"] = _first_regex_text_in_zone(observations, _EIN_RE, (0.20, 0.42, 0.16, 0.24))
    if employer.name is None:
        updates["name"] = _first_row_text_in_zone(
            observations,
            EMPLOYER_NAME_ZONE,
            skip_row=_looks_like_employer_name_label_row,
        )
    if employer.address.address_line_1 is None:
        # `EMPLOYER_ADDRESS_ZONE` (taller than `EMPLOYER_NAME_ZONE`) to
        # reliably catch all three Box c lines -- see its own docstring
        # for why this is a separate zone rather than widening
        # `EMPLOYER_NAME_ZONE` itself.
        rows = _row_texts_in_zone(
            observations, EMPLOYER_ADDRESS_ZONE, skip_row=_looks_like_employer_name_label_row
        )
        address_update = _address_from_two_line_block(rows[1:], employer.address)
        if address_update is not None:
            updates["address"] = address_update
    return employer.model_copy(update=updates) if updates else employer


def compute_employer_name_observation_count(
    document: W2Document, observations: list[TextObservation]
) -> int | None:
    """How many OCR observations contributed to `employer.name`'s value.

    Production layout-provenance signal (Phase 8C.8), read-only: it never
    influences `employer.name`'s value (computed above, already decided
    by the time this runs) -- it only reports, for the validator's
    benefit via `ExtractionSignals.employer_name_observation_count`, the
    size of the zone-restricted row-group whose joined text matches the
    already-decided value. Reuses `_observations_in_zone` and
    `_group_observation_rows` with `EMPLOYER_NAME_ZONE` -- the exact same
    zone and grouping the fallback above uses -- so this measures the
    real decision path, not an independent reconstruction. Originated as
    an evaluation-only measurement
    (`w2_pipeline.evaluation.employer_name_layout_signals`, Phase 8C.6);
    promoted here as the smallest production surface `validation/rules.py`
    needs, per `docs/experiments/phase8c8-promote-employer-name-validator-signals.md`.
    Returns `None` when `employer.name` itself is `None` or no matching
    row-group is found (never fabricated).
    """

    name = document.employer.name
    if name is None:
        return None
    zone_observations = _observations_in_zone(observations, EMPLOYER_NAME_ZONE)
    if not zone_observations:
        return None
    target = name.strip()
    for row in _group_observation_rows(zone_observations):
        joined = " ".join(observation.text.strip() for observation in row)
        if joined == target:
            return len(row)
    return None


def _apply_ocr_box_13_layout_fallbacks(
    box_13: Box13Flags,
    observations: list[TextObservation],
    box_13_visual_marks: dict[str, bool],
) -> Box13Flags:
    if not _looks_like_full_page_ocr_form(observations):
        return box_13

    return box_13.model_copy(
        update={
            "statutory_employee": box_13.statutory_employee
            or _has_checkbox_mark(observations, (0.605, 0.650, 0.535, 0.585)),
            "retirement_plan": box_13.retirement_plan
            or box_13_visual_marks.get("retirement_plan", False)
            or _has_checkbox_mark(observations, (0.655, 0.705, 0.535, 0.585)),
            "third_party_sick_pay": box_13.third_party_sick_pay
            or _has_checkbox_mark(observations, (0.715, 0.770, 0.535, 0.585)),
        }
    )


def _apply_ocr_box_12_layout_fallback(
    observations: list[TextObservation],
    warnings: list[ExtractionWarning],
) -> list[Box12Entry]:
    """OCR full-page zone fallback for Box 12 (Phase 8D.1A).

    The real 2026 W-2 form (and external Symage renders) print Box 12's
    code and amount in two separate columns with no literal "12 D: ..."
    text for the label-based primary path (`_parse_box_12`) to match --
    the same "positional block, not literal label text" shape as Box c/f.
    Each of the four slots (12a-12d) prints its amount even when empty
    ("$0.00"), but prints no code observation at all when the slot has no
    code -- so slots are paired by nearest row (vertical center), not by
    list position, and a slot is only emitted when a real code is found:
    an amount with no matching code is a blank-slot artifact, not a Box
    12 entry (the canonical schema requires a code).
    """

    if not _looks_like_full_page_ocr_form(observations):
        return []

    _, max_y = _layout_extent(observations)
    row_tolerance = 0.05 * max_y
    code_observations = [
        observation
        for observation in _observations_in_zone(observations, BOX_12_CODE_ZONE)
        if _BOX_12_CODE_TOKEN_RE.match(observation.text.strip())
    ]
    amount_observations = _observations_in_zone(observations, BOX_12_AMOUNT_ZONE)

    entries: list[Box12Entry] = []
    for code_observation in sorted(code_observations, key=_vertical_center):
        code_center = _vertical_center(code_observation)
        candidate_amounts = [
            observation
            for observation in amount_observations
            if abs(_vertical_center(observation) - code_center) <= row_tolerance
        ]
        if not candidate_amounts:
            continue
        amount_observation = min(
            candidate_amounts, key=lambda observation: abs(_vertical_center(observation) - code_center)
        )
        amount_text = amount_observation.text.strip()
        if not (any(separator in amount_text for separator in ("$", ",", ".")) and _MONEY_RE.match(amount_text)):
            continue
        try:
            amount = parse_money(amount_text, field_path="box_12_entries.amount")
        except ValueError as exc:
            warnings.append(ExtractionWarning(field_path="box_12_entries.amount", message=str(exc)))
            continue
        if amount is None:
            continue
        entries.append(Box12Entry(code=code_observation.text.strip(), amount=amount))
    return entries


def _apply_ocr_state_local_layout_fallback(
    observations: list[TextObservation],
    warnings: list[ExtractionWarning],
) -> list[StateLocalEntry]:
    """OCR full-page zone fallback for Boxes 15-20 (Phase 8D.1A).

    Unlike Box c/f/12, Boxes 15-20 print their own box-number label
    directly in OCR text ("15 State", "16 State wages, tips, etc.", ...),
    so each value sits in one fixed zone -- the same pattern
    `_apply_ocr_federal_layout_fallbacks` already uses for Boxes 1-11,
    just with a hardcoded per-box zone instead of a label lookup, since
    the label and value are two distinct printed elements here (unlike
    boxes 1-11's single "N label: value"-shaped internal-format line).
    This dataset's own annotation-coverage audit found exactly one
    state/local row per document (never more), so this always emits at
    most one `StateLocalEntry`.
    """

    if not _looks_like_full_page_ocr_form(observations):
        return []

    fields: dict[str, object] = {}
    for field_name, zone in _STATE_LOCAL_VALUE_ZONES.items():
        if field_name in _STATE_LOCAL_MONEY_FIELDS:
            value_text = _first_money_text_in_zone(observations, zone)
            if value_text is None:
                continue
            field_path = f"state_local_entries.{field_name}"
            try:
                fields[field_name] = parse_money(value_text, field_path=field_path)
            except ValueError as exc:
                warnings.append(ExtractionWarning(field_path=field_path, message=str(exc)))
        elif field_name == "box_15_state":
            # Box 15's own printed label ("15 State") sits close enough
            # above its value that a small rotation-induced ratio shift
            # can pull the label into this zone alongside the real value
            # (the same collision class as `EMPLOYEE_ADDRESS_ZONE`'s,
            # observed directly under this dataset's 2deg rotation) -- a
            # positive shape match (a bare 2-letter state code) sidesteps
            # it entirely rather than fighting over the zone boundary.
            fields[field_name] = _first_regex_text_in_zone(observations, _STATE_CODE_RE, zone)
        elif field_name == "box_15_employer_state_id_number":
            # Same collision class as box_15_state. A state employer ID
            # is NOT reliably EIN-shaped -- an initial implementation
            # assumed `_EIN_RE` from a handful of spot-checked samples,
            # but the annotation-coverage audit's full sweep of all 114
            # non-blank values across the 150 base documents found real
            # state-specific formats `_EIN_RE` misses entirely
            # (`\d{3}-\d{6}`, `\d{3}-\d{4}-\d{1}`, even
            # `\d{3}/\d{3}-\d{3}-\d{3}`) -- caught as a 180/600 "missing"
            # gap in this phase's own expanded 600-document benchmark
            # before being fixed here, not assumed correct. `_STATE_ID_RE`
            # matches all 114 real values with no false-positive risk
            # against nearby label/dollar text (neither contains only
            # digits/dashes/slashes).
            fields[field_name] = _first_regex_text_in_zone(observations, _STATE_ID_RE, zone)
        else:
            value_text = _zone_text(observations, zone)
            if value_text is not None:
                fields[field_name] = value_text

    if not any(value is not None for value in fields.values()):
        return []
    return [StateLocalEntry(**fields)]


def _has_ocr_observations(observations: list[TextObservation]) -> bool:
    return any(observation.source == ObservationSource.OCR for observation in observations)


def _looks_like_full_page_ocr_form(observations: list[TextObservation]) -> bool:
    if not observations:
        return False
    max_x, max_y = _layout_extent(observations)
    return max_x > 1000 and max_y > 1000


def _layout_extent(observations: list[TextObservation]) -> tuple[float, float]:
    # Extent reflects the main OCR pass's full-page coverage. A targeted
    # supplemental pass only ever scans a few narrow zones, so including it
    # here could skew every zone-ratio calculation on the page, not just the
    # field(s) the supplemental pass targets.
    primary_observations = [
        observation for observation in observations if not observation.is_supplemental
    ] or observations
    return (
        max((observation.bbox.x1 for observation in primary_observations), default=1.0),
        max((observation.bbox.y1 for observation in primary_observations), default=1.0),
    )


def _observations_in_zone(
    observations: list[TextObservation],
    zone: tuple[float, float, float, float],
) -> list[TextObservation]:
    max_x, max_y = _layout_extent(observations)
    x0_ratio, x1_ratio, y0_ratio, y1_ratio = zone
    return [
        observation
        for observation in observations
        if x0_ratio * max_x <= (observation.bbox.x0 + observation.bbox.x1) / 2 <= x1_ratio * max_x
        and y0_ratio * max_y <= (observation.bbox.y0 + observation.bbox.y1) / 2 <= y1_ratio * max_y
    ]


def _zone_text(
    observations: list[TextObservation],
    zone: tuple[float, float, float, float],
    *,
    discard_tiny_artifacts: bool = False,
) -> str | None:
    zone_observations = sorted(
        _observations_in_zone(observations, zone),
        key=lambda observation: observation.bbox.x0,
    )
    if discard_tiny_artifacts:
        zone_observations = _discard_tiny_artifacts(zone_observations)
    tokens = [
        cleaned
        for observation in zone_observations
        if (cleaned := _clean_layout_token(observation.text)) is not None
    ]
    return " ".join(tokens) or None


def _first_row_text_in_zone(
    observations: list[TextObservation],
    zone: tuple[float, float, float, float],
    *,
    skip_row: Callable[[str], bool] | None = None,
) -> str | None:
    """Return the topmost printed line within a zone, tokens joined left-to-right.

    Unlike `_zone_text` (which joins every observation found anywhere in
    the zone, appropriate for a zone that holds exactly one line), this
    isolates only one row via `_group_observation_rows` so a zone that
    spans a multi-line answer -- e.g. Box c's combined employer
    name/address/ZIP block -- returns only one line rather than
    concatenating every line together. Deliberately does not use
    `_clean_layout_token`: that filter's Box e label-word denylist
    (`"and"`, `"name"`, ...) is specific to guarding the employee-name zone
    against the rotated Box e label-bleed bug and would risk stripping a
    legitimate word from an unrelated field (e.g. "and" in a real employer
    name like "Smith and Sons Inc.").

    `skip_row`, when given, is checked against each row's joined text in
    top-to-bottom order; the first row for which it returns `False` (or
    that has no `skip_row` at all) is returned, rather than always the
    single topmost row. Needed because rotation can shift a field's own
    printed *label* into the same calibrated zone as its answer, ahead of
    it -- see `_looks_like_employer_name_label_row` and
    docs/experiments/phase8c1-employer-name-rotation-remediation.md.
    """

    for row_text in _row_texts_in_zone(observations, zone, skip_row=skip_row):
        return row_text
    return None


def _row_texts_in_zone(
    observations: list[TextObservation],
    zone: tuple[float, float, float, float],
    *,
    skip_row: Callable[[str], bool] | None = None,
) -> list[str]:
    """Every printed line within a zone, top-to-bottom, tokens joined
    left-to-right -- the multi-row generalization of `_first_row_text_in_zone`
    (Phase 8D.1A), for zones whose answer spans several lines the caller
    needs individually (e.g. Box c's name/street/city-state-ZIP block),
    rather than only the first."""

    zone_observations = _observations_in_zone(observations, zone)
    if not zone_observations:
        return []
    ordered_rows = sorted(
        _group_observation_rows(zone_observations),
        key=lambda row: min(_vertical_center(observation) for observation in row),
    )
    row_texts: list[str] = []
    for row in ordered_rows:
        tokens = [text for observation in row if (text := observation.text.strip())]
        row_text = " ".join(tokens)
        if row_text and (skip_row is None or not skip_row(row_text)):
            row_texts.append(row_text)
    return row_texts


_EMPLOYER_NAME_LABEL_MARKERS = ("employer", "zip code")


def _looks_like_employer_name_label_row(row_text: str) -> bool:
    """Detect Box c's own printed label row, not the employer's actual name.

    Under rotation, the printed label ("...Employer's name, address, and
    ZIP code") can drift into the same calibrated zone as the answer,
    positioned ahead of it -- the same root-cause class as the earlier-
    fixed Box e rotation label-bleed bug (confirmed by direct diagnosis:
    `docs/experiments/phase8c1-employer-name-rotation-remediation.md`).
    Checking for both markers together (rather than a single word like
    "employer") keeps a false positive on a real employer name
    effectively impossible -- no real company name is going to contain
    both "employer" and "zip code".

    Also skips a row whose entire text is a single letter, e.g. `"c"`.
    Tesseract reports the printed box-letter marker ("c") as its own
    word-level observation, and under rotation skew the row-grouping
    tolerance in `_group_observation_rows` can accumulate enough drift
    across the label's other, taller word tokens that "c" no longer
    falls within tolerance of them -- landing in its own row, positioned
    between the (now correctly skipped) label row and the real answer
    row. A single bare letter is never a legitimate `employer.name`
    fallback answer on its own, so skipping it here is safe.
    """

    normalized = row_text.strip().lower()
    if len(normalized) == 1 and normalized.isalpha():
        return True
    return all(marker in normalized for marker in _EMPLOYER_NAME_LABEL_MARKERS)


def _discard_tiny_artifacts(observations: list[TextObservation]) -> list[TextObservation]:
    if not observations:
        return []
    max_height = max(observation.bbox.y1 - observation.bbox.y0 for observation in observations)
    return [
        observation
        for observation in observations
        if not _looks_like_tiny_artifact(observation, max_height=max_height)
    ]


def _looks_like_tiny_artifact(observation: TextObservation, *, max_height: float) -> bool:
    text = observation.text.strip()
    height = observation.bbox.y1 - observation.bbox.y0
    width = observation.bbox.x1 - observation.bbox.x0
    return len(text) <= 3 and height < 0.4 * max_height and width < 0.4 * max_height


# Box e's static printed label ("e Employee's first name and initial"),
# lowercased with apostrophes normalized. Under rotation this label's
# normalized zone position can drift into the employee-name OCR fallback
# zone alongside the actual name (see
# docs/experiments/phase4e-paddle-rotation-name-investigation.md); this
# denylist strips it back out regardless of whether an OCR backend
# recognizes it as one merged observation (PaddleOCR's line-level
# recognition) or as separate word tokens interleaved with the name
# (Tesseract's word-level recognition). Deliberately excludes the "e"
# box-letter marker itself: that case is already handled by the
# case-SENSITIVE _SINGLE_CHAR_JUNK check below (both for a standalone "e"
# observation and, via the per-word membership check in the multi-word
# branch, for "e" as one word inside a longer merged label string).
# Matching "e" here too via case-INSENSITIVE comparison previously caused
# a real bug: a legitimate capital "E" middle initial was normalized to
# lowercase and incorrectly discarded as if it were the marker.
_SINGLE_CHAR_JUNK = {"-", "—", "–", "°", "¢", ";", "=", "Cc", "c", "e", "f"}
_BOX_E_LABEL_WORDS = {"employee's", "employees", "first", "name", "and", "initial"}
_APOSTROPHE_RE = re.compile(r"[‘’ʼ`]")


def _is_box_e_label_word(word: str) -> bool:
    normalized = _APOSTROPHE_RE.sub("'", word).strip(".,:;").lower()
    return normalized in _BOX_E_LABEL_WORDS


def _clean_layout_token(text: str) -> str | None:
    cleaned = text.strip().strip("|[]_~`\"'“”")
    if not cleaned:
        return None
    if cleaned in _SINGLE_CHAR_JUNK:
        return None
    if cleaned.isdigit():
        return None
    words = cleaned.split()
    if len(words) == 1:
        if _is_box_e_label_word(cleaned):
            return None
        return cleaned
    survivors = [
        word for word in words if word not in _SINGLE_CHAR_JUNK and not _is_box_e_label_word(word)
    ]
    if not survivors:
        return None
    return " ".join(survivors)


def _first_regex_text_in_zone(
    observations: list[TextObservation],
    pattern: re.Pattern[str],
    zone: tuple[float, float, float, float],
) -> str | None:
    for observation in sorted(
        _observations_in_zone(observations, zone),
        key=lambda observation: (observation.bbox.y0, observation.bbox.x0),
    ):
        match = pattern.search(observation.text)
        if match:
            return match.group(0)
    return None


def _first_money_text_in_zone(
    observations: list[TextObservation],
    zone: tuple[float, float, float, float],
) -> str | None:
    for observation in sorted(
        _observations_in_zone(observations, zone),
        key=lambda observation: (observation.bbox.y0, observation.bbox.x0),
    ):
        text = observation.text.strip()
        if any(separator in text for separator in ("$", ",", ".")) and _MONEY_RE.match(text):
            return text
    return None


def _has_checkbox_mark(
    observations: list[TextObservation],
    zone: tuple[float, float, float, float],
) -> bool:
    mark_tokens = {"x", "v", "✓", "✔", "[v", "v]", "[x", "x]", "4"}
    for observation in _observations_in_zone(observations, zone):
        normalized = observation.text.strip().lower().replace("|", "").replace("\\", "")
        if normalized in mark_tokens:
            return True
    return False


def _parse_box_14(
    lines: list[str],
    warnings: list[ExtractionWarning],
) -> tuple[list[Box14Entry], list[TippedOccupationCode]]:
    entries: list[Box14Entry] = []
    tipped_codes: list[TippedOccupationCode] = []
    for line in lines:
        if match := _BOX_14A_RE.match(line):
            label = match.group("label").strip()
            raw_value = match.group("value").strip()
            if not label or not raw_value:
                continue
            try:
                amount = parse_money(raw_value, field_path="box_14_entries.amount")
            except ValueError:
                entries.append(Box14Entry(label=label, value=raw_value))
            else:
                entries.append(Box14Entry(label=label, amount=amount))
        elif match := _BOX_14B_RE.match(line):
            value = match.group("value").strip()
            if value:
                tipped_codes.append(TippedOccupationCode(code=value))
    return entries, tipped_codes


def _parse_state_local(
    lines: list[str],
    warnings: list[ExtractionWarning],
) -> list[StateLocalEntry]:
    rows: dict[int, dict[str, object]] = defaultdict(dict)
    for line in lines:
        match = _STATE_LOCAL_RE.match(line)
        if not match:
            continue
        box_number = int(match.group("number"))
        row_number = int(match.group("row"))
        label = match.group("label")
        raw_value = match.group("value").strip()
        field_name = _state_local_field_name(box_number, label)
        if field_name is None:
            continue
        if box_number in {16, 17, 18, 19}:
            try:
                rows[row_number][field_name] = parse_money(
                    raw_value,
                    field_path=f"state_local_entries.{field_name}",
                )
            except ValueError as exc:
                warnings.append(
                    ExtractionWarning(
                        field_path=f"state_local_entries.{field_name}",
                        message=str(exc),
                    )
                )
        else:
            rows[row_number][field_name] = _empty_to_none(raw_value)

    return [
        StateLocalEntry(**rows[row_number])
        for row_number in sorted(rows)
        if any(value is not None for value in rows[row_number].values())
    ]


def _state_local_field_name(box_number: int, label: str) -> str | None:
    if box_number == 15:
        normalized = label.lower()
        if "employer state id" in normalized:
            return "box_15_employer_state_id_number"
        return "box_15_state"
    return {
        16: "box_16_state_wages_tips_etc",
        17: "box_17_state_income_tax",
        18: "box_18_local_wages_tips_etc",
        19: "box_19_local_income_tax",
        20: "box_20_locality_name",
    }.get(box_number)


def _observations_in_x_range(
    observations: list[TextObservation],
    *,
    min_x: float | None = None,
    max_x: float | None = None,
) -> list[str]:
    lines = []
    for observation in observations:
        if min_x is not None and observation.bbox.x0 < min_x:
            continue
        if max_x is not None and observation.bbox.x0 >= max_x:
            continue
        lines.append(observation.text.strip())
    return lines


def _value_after_label(lines: list[str], label: str) -> str:
    prefix = f"{label}:"
    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def _value_after_prefix(lines: list[str], prefix: str) -> str:
    label = f"{prefix}:"
    for line in lines:
        if line.startswith(label):
            return line[len(label) :].strip()
    return ""


def _parse_city_state_zip(value: str) -> tuple[str | None, str | None, str | None]:
    parts = value.split()
    if len(parts) < 3:
        return None, None, None
    postal_code = parts[-1]
    state = parts[-2]
    # The internal synthetic generator's "City/State/ZIP" line has no
    # comma ("Springfield IL 62704"); the real W-2 form (and the external
    # Symage renders replicating it) prints "City, ST ZIP" -- strip a
    # trailing comma from the city so both formats parse the same way.
    city = " ".join(parts[:-2]).rstrip(",")
    return city or None, state or None, postal_code or None


def _first_match(value: str, pattern: re.Pattern[str]) -> str | None:
    match = pattern.search(value)
    return match.group(0) if match else None


def _checkbox_value(value: str) -> bool:
    return value.strip().lower() in {"x", "checked", "true", "yes", "1"}


def _empty_to_none(value: str) -> str | None:
    return value.strip() or None


def _source_file_type(source_type: SourceDocumentType) -> SourceFileType:
    if source_type == SourceDocumentType.PDF:
        return SourceFileType.PDF
    if source_type == SourceDocumentType.JPEG:
        return SourceFileType.JPEG
    return SourceFileType.PNG
