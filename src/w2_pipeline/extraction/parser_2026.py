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
    box_13 = _parse_box_13(lines, observations, observation_set.box_13_visual_marks)
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
    if _has_ocr_observations(observations) and employer.ein is None:
        employer = employer.model_copy(update={"ein": _first_ein_from_ocr_layout(observations)})
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
    return employee.model_copy(update=updates)


def _first_ein_from_ocr_layout(observations: list[TextObservation]) -> str | None:
    return _first_regex_text_in_zone(observations, _EIN_RE, (0.20, 0.42, 0.16, 0.24))


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
