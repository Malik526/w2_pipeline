"""Deterministic 2026 W-2 parser over common text/layout observations."""

from __future__ import annotations

from collections import defaultdict
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
from w2_pipeline.extraction.models import ExtractionWarning, ObservationSet, TextObservation
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
    lines = _line_texts(observations)
    warnings: list[ExtractionWarning] = []
    employee = _parse_employee(observations, warnings)
    employer = _parse_employer(observations, warnings)
    federal = _parse_federal(lines, warnings)
    box_12_entries = _parse_box_12(lines, warnings)
    box_13 = _parse_box_13(lines)
    box_14_entries, tipped_codes = _parse_box_14(lines, warnings)
    state_local_entries = _parse_state_local(lines, warnings)

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


def _line_texts(observations: list[TextObservation]) -> list[str]:
    return [observation.text.strip() for observation in observations if observation.text.strip()]


def _parse_employee(
    observations: list[TextObservation],
    warnings: list[ExtractionWarning],
) -> Employee:
    left_lines = _observations_in_x_range(observations, max_x=300)
    name_value = _value_after_label(left_lines, "Name")
    first_name, middle_initial, last_name, suffix = _parse_person_name(name_value)
    city, state, postal_code = _parse_city_state_zip(_value_after_label(left_lines, "City/State/ZIP"))
    return Employee(
        ssn=_first_match(_value_after_label(left_lines, "SSN"), _SSN_RE),
        first_name=first_name,
        middle_initial=middle_initial,
        last_name=last_name,
        suffix=suffix,
        address=Address(
            address_line_1=_empty_to_none(_value_after_label(left_lines, "Address 1")),
            address_line_2=_empty_to_none(_value_after_label(left_lines, "Address 2")),
            city=city,
            state=state,
            postal_code=postal_code,
            country="US" if city or state or postal_code else None,
        ),
    )


def _parse_employer(
    observations: list[TextObservation],
    warnings: list[ExtractionWarning],
) -> Employer:
    right_lines = _observations_in_x_range(observations, min_x=300)
    city, state, postal_code = _parse_city_state_zip(_value_after_label(right_lines, "City/State/ZIP"))
    return Employer(
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


def _parse_box_13(lines: list[str]) -> Box13Flags:
    return Box13Flags(
        statutory_employee=_checkbox_value(_value_after_prefix(lines, "13 Statutory employee")),
        retirement_plan=_checkbox_value(_value_after_prefix(lines, "13 Retirement plan")),
        third_party_sick_pay=_checkbox_value(_value_after_prefix(lines, "13 Third-party sick pay")),
    )


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


def _parse_person_name(value: str) -> tuple[str | None, str | None, str | None, str | None]:
    parts = value.split()
    if not parts:
        return None, None, None, None
    if len(parts) == 1:
        return parts[0], None, None, None
    if len(parts) == 2:
        return parts[0], None, parts[1], None
    if len(parts[-1]) <= 4 and parts[-1].rstrip(".").upper() in {"JR", "SR", "II", "III", "IV"}:
        suffix = parts[-1]
        name_parts = parts[:-1]
    else:
        suffix = None
        name_parts = parts
    first_name = name_parts[0]
    middle_initial = name_parts[1] if len(name_parts[1]) == 1 else None
    last_name = " ".join(name_parts[2:] if middle_initial else name_parts[1:])
    return first_name, middle_initial, last_name or None, suffix


def _parse_city_state_zip(value: str) -> tuple[str | None, str | None, str | None]:
    parts = value.split()
    if len(parts) < 3:
        return None, None, None
    postal_code = parts[-1]
    state = parts[-2]
    city = " ".join(parts[:-2])
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
