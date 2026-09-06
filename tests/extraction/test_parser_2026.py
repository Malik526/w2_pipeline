from decimal import Decimal

import pytest

from w2_pipeline.extraction.models import (
    AcquisitionRoute,
    BoundingBox,
    ObservationSet,
    ObservationSource,
    TextObservation,
)
from w2_pipeline.extraction.parser_2026 import (
    _clean_layout_token,
    _first_row_text_in_zone,
    _looks_like_employer_name_label_row,
    parse_money,
    parse_w2_2026_observations,
)
from w2_pipeline.ingestion.models import SourceDocumentType


def obs(text: str, x0: float, y0: float) -> TextObservation:
    return TextObservation(
        text=text,
        page=1,
        bbox=BoundingBox(x0=x0, y0=y0, x1=x0 + 200, y1=y0 + 10),
        source=ObservationSource.NATIVE_PDF,
    )


def ocr_obs(text: str, x0: float, y0: float, width: float = 80, height: float = 24) -> TextObservation:
    return TextObservation(
        text=text,
        page=1,
        bbox=BoundingBox(x0=x0, y0=y0, x1=x0 + width, y1=y0 + height),
        source=ObservationSource.OCR,
    )


def supplemental_ocr_obs(
    text: str, x0: float, y0: float, width: float = 80, height: float = 24
) -> TextObservation:
    return ocr_obs(text, x0, y0, width, height).model_copy(update={"is_supplemental": True})


def fixture_observations() -> ObservationSet:
    return ObservationSet(
        route=AcquisitionRoute.NATIVE_PDF,
        observations=[
            obs("SSN: 000-00-0005", 40, 100),
            obs("Name: SyntheticFirst0005 F SyntheticLast0005", 40, 115),
            obs("Address 1: 1005 Synthetic Test Ave", 40, 130),
            obs("Address 2: Unit 5", 40, 145),
            obs("City/State/ZIP: Faketown NJ 00005", 40, 160),
            obs("EIN: 00-0000005", 330, 100),
            obs("Name: Synthetic Payroll Fixture 0005 LLC", 330, 115),
            obs("Control: CTRL-5", 330, 130),
            obs("Address 1: 2005 Fixture Payroll Plaza", 330, 145),
            obs("City/State/ZIP: Example City NJ 10005", 330, 160),
            obs("1 Wages, tips, other comp.: $28,425.27", 40, 240),
            obs("2 Federal income tax withheld: 3325.76", 300, 240),
            obs("3 Social security wages: 28425.27", 40, 255),
            obs("4 Social security tax withheld: 1762.37", 300, 255),
            obs("5 Medicare wages and tips: 30035.36", 40, 270),
            obs("6 Medicare tax withheld: 435.51", 300, 270),
            obs("7 Social security tips: ", 40, 285),
            obs("8 Allocated tips: 25.00", 300, 285),
            obs("10 Dependent care benefits: 423.22", 40, 300),
            obs("11 Nonqualified plans: ", 300, 300),
            obs("12 DD: 2422.31", 40, 440),
            obs("12 W: 6123.86", 40, 455),
            obs("13 Statutory employee: ", 40, 470),
            obs("13 Retirement plan: X", 40, 485),
            obs("13 Third-party sick pay: ", 40, 500),
            obs("14a SYNUNION: 138.51", 330, 440),
            obs("14a SYNMEMO: Informational", 330, 455),
            obs("14b code 1: SYN-TIP-005", 330, 470),
            obs("15.1 State: NJ", 40, 620),
            obs("15.1 Employer state ID: NJ-SYN-000005", 300, 620),
            obs("16.1 State wages: 28425.27", 40, 635),
            obs("17.1 State tax: 1335.99", 300, 635),
            obs("18.1 Local wages: 7106.32", 40, 650),
            obs("19.1 Local tax: ", 300, 650),
            obs("20.1 Locality: SYNLOCAL", 40, 665),
        ],
    )


def test_parse_money_handles_common_w2_formats() -> None:
    assert parse_money("47,985.00", field_path="box") == Decimal("47985.00")
    assert parse_money("47985.00", field_path="box") == Decimal("47985.00")
    assert parse_money("$47,985.00", field_path="box") == Decimal("47985.00")


def test_parse_money_rejects_invalid_amounts() -> None:
    with pytest.raises(ValueError):
        parse_money("not money", field_path="box")


def test_parser_extracts_core_2026_w2_fields() -> None:
    document, warnings = parse_w2_2026_observations(
        fixture_observations(),
        document_id="doc",
        source_filename="fixture.pdf",
        source_type=SourceDocumentType.PDF,
    )

    assert warnings == []
    assert document.employee.ssn == "000-00-0005"
    assert document.employee.first_name == "SyntheticFirst0005"
    assert document.employee.middle_initial == "F"
    assert document.employee.last_name == "SyntheticLast0005"
    assert document.employee.address.address_line_2 == "Unit 5"
    assert document.employer.ein == "00-0000005"
    assert document.employer.name == "Synthetic Payroll Fixture 0005 LLC"
    assert document.federal_wages_and_taxes.box_1_wages_tips_other_compensation == Decimal("28425.27")
    assert document.federal_wages_and_taxes.box_7_social_security_tips is None
    assert document.federal_wages_and_taxes.box_8_allocated_tips == Decimal("25.00")
    assert document.federal_wages_and_taxes.box_9_verification_code is None
    assert [entry.code for entry in document.box_12_entries] == ["DD", "W"]
    assert document.box_13.retirement_plan is True
    assert document.box_14_entries[0].amount == Decimal("138.51")
    assert document.box_14_entries[1].value == "Informational"
    assert document.tipped_occupation_codes[0].code == "SYN-TIP-005"
    assert document.state_local_entries[0].box_15_state == "NJ"
    assert document.state_local_entries[0].box_15_employer_state_id_number == "NJ-SYN-000005"
    assert document.state_local_entries[0].box_16_state_wages_tips_etc == Decimal("28425.27")


def test_parser_records_field_warning_for_invalid_money() -> None:
    observation_set = fixture_observations()
    observation_set.observations[10] = obs("1 Wages, tips, other comp.: nope", 40, 240)

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="doc",
        source_filename="fixture.pdf",
        source_type=SourceDocumentType.PDF,
    )

    assert document.federal_wages_and_taxes.box_1_wages_tips_other_compensation is None
    assert warnings
    assert warnings[0].field_path == "federal_wages_and_taxes.box_1_wages_tips_other_compensation"


def test_parser_extracts_external_style_ocr_word_observations() -> None:
    observation_set = ObservationSet(
        route=AcquisitionRoute.OCR,
        observations=[
            ocr_obs("a", 650, 165, 15),
            ocr_obs("Employee’s", 690, 162, 150),
            ocr_obs("social", 850, 162, 75),
            ocr_obs("security", 935, 162, 100),
            ocr_obs("number", 1045, 162, 100),
            ocr_obs("242-48-4959", 805, 210, 190),
            ocr_obs("b", 175, 262, 15),
            ocr_obs("Employer", 210, 262, 122),
            ocr_obs("identification", 342, 262, 164),
            ocr_obs("number", 517, 262, 98),
            ocr_obs("(EIN)", 624, 262, 60),
            ocr_obs("1", 1413, 263, 10),
            ocr_obs("Wages,", 1449, 262, 88),
            ocr_obs("tips,", 1546, 262, 50),
            ocr_obs("other", 1605, 262, 62),
            ocr_obs("compensation", 1675, 262, 168),
            ocr_obs("2", 1922, 262, 15),
            ocr_obs("Federal", 1964, 262, 93),
            ocr_obs("income", 2069, 262, 93),
            ocr_obs("tax", 2171, 263, 39),
            ocr_obs("withheld", 2220, 262, 107),
            ocr_obs("75-5696876", 679, 310, 178),
            ocr_obs("$114,858.00", 1689, 309, 186, 30),
            ocr_obs("$21,930.26", 2218, 309, 167, 30),
            ocr_obs("3", 1412, 374, 12),
            ocr_obs("Social", 1453, 374, 88),
            ocr_obs("security", 1541, 374, 100),
            ocr_obs("wages", 1651, 374, 85),
            ocr_obs("4", 1922, 374, 15),
            ocr_obs("Social", 1963, 374, 88),
            ocr_obs("security", 2051, 374, 100),
            ocr_obs("tax", 2160, 374, 39),
            ocr_obs("withheld", 2209, 374, 107),
            ocr_obs("$122,000.00", 1693, 405, 184, 30),
            ocr_obs("$7,564.00", 2236, 409, 147, 30),
            ocr_obs("5", 1412, 473, 12),
            ocr_obs("Medicare", 1454, 473, 128),
            ocr_obs("wages", 1582, 473, 85),
            ocr_obs("and", 1676, 473, 45),
            ocr_obs("tips", 1732, 473, 50),
            ocr_obs("6", 1922, 473, 15),
            ocr_obs("Medicare", 1964, 473, 128),
            ocr_obs("tax", 2092, 473, 39),
            ocr_obs("withheld", 2140, 473, 107),
            ocr_obs("$122,000.00", 1693, 492, 184, 30),
            ocr_obs("$1,769.00", 2236, 509, 147, 30),
            ocr_obs("e", 176, 767, 15),
            ocr_obs("Employee’s", 210, 762, 150),
            ocr_obs("first", 368, 762, 50),
            ocr_obs("name", 426, 768, 72),
            ocr_obs("and", 506, 762, 49),
            ocr_obs("initial", 564, 762, 67),
            ocr_obs("Last", 739, 762, 55),
            ocr_obs("name", 802, 768, 72),
            ocr_obs("Steven", 168, 810, 100),
            ocr_obs("D", 282, 811, 20),
            ocr_obs("Armstrong", 733, 806, 151, 40),
            ocr_obs("13", 1399, 812, 30),
            ocr_obs("Retirement", 1592, 804, 112),
            ocr_obs("plan", 1595, 825, 46),
            ocr_obs("[V", 1601, 850, 36, 44),
            ocr_obs("Copy", 151, 1535, 50),
            ocr_obs("Return.", 993, 1535, 80),
        ],
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="external-style",
        source_filename="external.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.employee.ssn == "242-48-4959"
    assert document.employee.first_name == "Steven"
    assert document.employee.middle_initial == "D"
    assert document.employee.last_name == "Armstrong"
    assert document.employer.ein == "75-5696876"
    assert document.federal_wages_and_taxes.box_1_wages_tips_other_compensation == Decimal("114858.00")
    assert document.federal_wages_and_taxes.box_2_federal_income_tax_withheld == Decimal("21930.26")
    assert document.federal_wages_and_taxes.box_3_social_security_wages == Decimal("122000.00")
    assert document.federal_wages_and_taxes.box_4_social_security_tax_withheld == Decimal("7564.00")
    assert document.federal_wages_and_taxes.box_5_medicare_wages_and_tips == Decimal("122000.00")
    assert document.federal_wages_and_taxes.box_6_medicare_tax_withheld == Decimal("1769.00")
    assert document.box_13.retirement_plan is True


def _paddle_style_observations_without_checkbox_mark() -> list[TextObservation]:
    """Same layout as the external-style OCR fixture, but with no observation
    at all for the retirement-plan checkbox mark, matching PaddleOCR's actual
    behavior (its text detector never emits a region for the glyph, unlike
    Tesseract's garbled "[V"/"4" misreads)."""

    return [
        ocr_obs("Steven D", 168, 810, 130),
        ocr_obs("Armstrong", 733, 806, 151, 40),
        ocr_obs("13", 1399, 812, 30),
        ocr_obs("Statutory", 1453, 804, 90),
        ocr_obs("employee", 1453, 825, 90),
        ocr_obs("Retirement", 1592, 804, 112),
        ocr_obs("plan", 1595, 825, 46),
        # No observation for the checkbox mark itself.
        ocr_obs("Copy", 151, 1535, 50),
        ocr_obs("Return.", 993, 1535, 80),
    ]


def test_parser_uses_visual_signal_when_ocr_never_detects_the_checkbox_mark() -> None:
    observation_set = ObservationSet(
        route=AcquisitionRoute.OCR,
        observations=_paddle_style_observations_without_checkbox_mark(),
        box_13_visual_marks={"retirement_plan": True},
    )

    document, _ = parse_w2_2026_observations(
        observation_set,
        document_id="paddle-style",
        source_filename="external.png",
        source_type=SourceDocumentType.PNG,
    )

    assert document.box_13.retirement_plan is True


def test_parser_does_not_infer_checkbox_mark_without_any_signal() -> None:
    observation_set = ObservationSet(
        route=AcquisitionRoute.OCR,
        observations=_paddle_style_observations_without_checkbox_mark(),
        box_13_visual_marks={"retirement_plan": False},
    )

    document, _ = parse_w2_2026_observations(
        observation_set,
        document_id="paddle-style",
        source_filename="external.png",
        source_type=SourceDocumentType.PNG,
    )

    assert document.box_13.retirement_plan is False


def test_parser_reads_ocr_box_e_left_to_right_when_initial_is_slightly_higher() -> None:
    observation_set = ObservationSet(
        route=AcquisitionRoute.OCR,
        observations=[
            ocr_obs("G", 282, 810, 20, 24),
            ocr_obs("David", 168, 811, 100, 24),
            ocr_obs("Rodriguez", 733, 806, 151, 40),
            ocr_obs("Copy", 151, 1535, 50),
            ocr_obs("Return.", 2400, 1535, 80),
        ],
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="external-style",
        source_filename="external.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.employee.first_name == "David"
    assert document.employee.middle_initial == "G"
    assert document.employee.last_name == "Rodriguez"


def test_parser_keeps_ocr_box_e_first_name_without_middle_initial() -> None:
    observation_set = ObservationSet(
        route=AcquisitionRoute.OCR,
        observations=[
            ocr_obs("Robert", 168, 811, 100, 24),
            ocr_obs("Hernandez", 733, 806, 151, 40),
            ocr_obs("Copy", 151, 1535, 50),
            ocr_obs("Return.", 2400, 1535, 80),
        ],
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="external-style",
        source_filename="external.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.employee.first_name == "Robert"
    assert document.employee.middle_initial is None
    assert document.employee.last_name == "Hernandez"


def test_parser_filters_tiny_ocr_artifacts_in_employee_name_zones() -> None:
    observation_set = ObservationSet(
        route=AcquisitionRoute.OCR,
        observations=[
            ocr_obs("Nicole", 168, 811, 100, 24),
            ocr_obs("i", 276, 823, 3, 4),
            ocr_obs("H", 282, 811, 20, 24),
            ocr_obs("Phillips", 733, 806, 151, 40),
            ocr_obs("ill", 889, 824, 4, 5),
            ocr_obs("Jr", 1280, 808, 40, 24),
            ocr_obs("Copy", 151, 1535, 50),
            ocr_obs("Return.", 2400, 1535, 80),
        ],
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="external-style",
        source_filename="external.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.employee.first_name == "Nicole"
    assert document.employee.middle_initial == "H"
    assert document.employee.last_name == "Phillips"
    assert document.employee.suffix == "Jr"


def test_parser_preserves_accented_ocr_employee_name_text() -> None:
    observation_set = ObservationSet(
        route=AcquisitionRoute.OCR,
        observations=[
            ocr_obs("Jesús", 168, 811, 100, 24),
            ocr_obs("D", 282, 811, 20, 24),
            ocr_obs("García", 733, 806, 151, 40),
            ocr_obs("Copy", 151, 1535, 50),
            ocr_obs("Return.", 2400, 1535, 80),
        ],
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="external-style",
        source_filename="external.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.employee.first_name == "Jesús"
    assert document.employee.middle_initial == "D"
    assert document.employee.last_name == "García"


def test_parser_excludes_supplemental_observations_from_primary_row_grouping() -> None:
    """A targeted supplemental pass (e.g. PSM 11's box-3/5/6 recovery) shares
    physical page regions with primary box lines. Even when a supplemental
    observation lands at the exact same position as an already-correct
    primary value with a *different* (wrong) reading, it must never be
    merged into that primary row and corrupt or override the result."""

    observation_set = ObservationSet(
        route=AcquisitionRoute.OCR,
        observations=[
            ocr_obs("5", 1412, 473, 12),
            ocr_obs("Medicare", 1454, 473, 128),
            ocr_obs("wages", 1582, 473, 85),
            ocr_obs("and", 1676, 473, 45),
            ocr_obs("tips", 1732, 473, 50),
            ocr_obs("$122,000.00", 1693, 492, 184, 30),
            supplemental_ocr_obs("$999,999.99", 1693, 492, 184, 30),
            ocr_obs("Copy", 151, 1535, 50),
            ocr_obs("Return.", 2400, 1535, 80),
        ],
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="external-style",
        source_filename="external.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.federal_wages_and_taxes.box_5_medicare_wages_and_tips == Decimal("122000.00")


def test_parser_recovers_targeted_field_from_supplemental_observation_when_primary_is_missing() -> None:
    """The other side of the same mechanism: when the main pass has no
    reading at all for a targeted field, a supplemental-tagged observation
    landing in that field's OCR fallback zone should still recover it."""

    observation_set = ObservationSet(
        route=AcquisitionRoute.OCR,
        observations=[
            supplemental_ocr_obs("$122,000.00", 1693, 405, 184, 30),
            ocr_obs("Copy", 151, 1535, 50),
            ocr_obs("Return.", 2400, 1535, 80),
        ],
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="external-style",
        source_filename="external.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.federal_wages_and_taxes.box_3_social_security_wages == Decimal("122000.00")


def _rotated_style_observations(*name_and_label_observations: TextObservation) -> ObservationSet:
    """Full-page-style OCR fixture (established >1000x1000 extent) with the
    given employee-name-zone observations, matching the coordinate
    convention already used for the employee-name fallback tests above."""

    return ObservationSet(
        route=AcquisitionRoute.OCR,
        observations=[
            *name_and_label_observations,
            ocr_obs("Copy", 151, 1535, 50),
            ocr_obs("Return.", 2400, 1535, 80),
        ],
    )


def test_parser_leaves_clean_employee_name_unchanged() -> None:
    """Box e label-word filtering must not affect a normal, uncorrupted
    name-zone reading (no label text present)."""

    observation_set = _rotated_style_observations(
        ocr_obs("Steven", 168, 811, 100, 24),
        ocr_obs("D", 282, 811, 20, 24),
        ocr_obs("Armstrong", 733, 806, 151, 40),
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="clean-name",
        source_filename="clean.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.employee.first_name == "Steven"
    assert document.employee.middle_initial == "D"
    assert document.employee.last_name == "Armstrong"


def test_parser_strips_paddle_style_merged_box_e_label_with_middle_initial() -> None:
    """PaddleOCR's line-level recognition: the name+initial arrive as one
    merged observation, and the printed Box e label arrives as a second,
    separate merged observation landing in the same rotated zone."""

    observation_set = _rotated_style_observations(
        ocr_obs("Steven D", 189, 815, 145, 24),
        ocr_obs("e Employee's first name and initial", 197, 800, 460, 24),
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="paddle-rotated-with-initial",
        source_filename="rotated.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.employee.first_name == "Steven"
    assert document.employee.middle_initial == "D"


def test_parser_strips_paddle_style_merged_box_e_label_first_name_only() -> None:
    """Same as above but with no middle initial in the name value."""

    observation_set = _rotated_style_observations(
        ocr_obs("Lori", 186, 815, 71, 24),
        ocr_obs("e Employee's first name and initial", 197, 800, 460, 24),
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="paddle-rotated-no-initial",
        source_filename="rotated.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.employee.first_name == "Lori"
    assert document.employee.middle_initial is None


def test_parser_strips_box_e_label_with_accented_name() -> None:
    """Accented characters in the name must survive the label-word filter
    (only exact, ASCII-normalized label vocabulary is stripped)."""

    observation_set = _rotated_style_observations(
        ocr_obs("Jesús D", 189, 815, 145, 24),
        ocr_obs("e Employee's first name and initial", 197, 800, 460, 24),
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="paddle-rotated-accented",
        source_filename="rotated.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.employee.first_name == "Jesús"
    assert document.employee.middle_initial == "D"


def test_parser_strips_tesseract_style_fragmented_box_e_label_tokens() -> None:
    """Tesseract's word-level recognition: the name, initial, and each word
    of the printed label arrive as separate observations, interleaved by
    x-position within the zone rather than appearing as a clean run —
    matching the real observed corruption shape ("Steven Employee's D
    first name and")."""

    observation_set = _rotated_style_observations(
        ocr_obs("Steven", 168, 822, 100, 24),
        ocr_obs("Employee’s", 280, 822, 130, 24),  # curly apostrophe, as Tesseract emits it
        ocr_obs("D", 420, 822, 20, 24),
        ocr_obs("first", 460, 822, 60, 24),
        ocr_obs("name", 530, 822, 65, 24),
        ocr_obs("and", 605, 822, 45, 24),
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="tesseract-rotated-fragmented",
        source_filename="rotated.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.employee.first_name == "Steven"
    assert document.employee.middle_initial == "D"


def test_parser_box_e_label_filter_does_not_regress_last_name_or_suffix() -> None:
    """The label-word filter is scoped to the shared name-zone cleaning
    helper; confirm last name and suffix zones still parse normally
    alongside a rotated-style label-bleed on the first-name zone."""

    observation_set = _rotated_style_observations(
        ocr_obs("Steven D", 189, 815, 145, 24),
        ocr_obs("e Employee's first name and initial", 197, 800, 460, 24),
        ocr_obs("Armstrong", 733, 806, 151, 40),
        ocr_obs("Jr", 1280, 808, 40, 24),
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="rotated-full-name",
        source_filename="rotated.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.employee.first_name == "Steven"
    assert document.employee.middle_initial == "D"
    assert document.employee.last_name == "Armstrong"
    assert document.employee.suffix == "Jr"


def test_clean_layout_token_preserves_capital_e_middle_initial() -> None:
    """Regression test for the capital-E bug: _is_box_e_label_word must not
    lowercase-match a legitimate "E" middle initial against the "e"
    box-letter marker."""

    assert _clean_layout_token("E") == "E"


def test_clean_layout_token_still_filters_lowercase_e_marker() -> None:
    """The lowercase Box e marker itself must remain filtered, standalone
    and as one word inside a longer merged label string."""

    assert _clean_layout_token("e") is None
    assert (
        _clean_layout_token("e Employee's first name and initial") is None
    )


def test_parser_recovers_capital_e_middle_initial_from_paddle_style_merged_label() -> None:
    """End-to-end: a rotated-style Paddle merge with a capital E initial
    must recover both first_name and middle_initial correctly."""

    observation_set = _rotated_style_observations(
        ocr_obs("Steven E", 189, 815, 145, 24),
        ocr_obs("e Employee's first name and initial", 197, 800, 460, 24),
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="paddle-rotated-capital-e-initial",
        source_filename="rotated.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.employee.first_name == "Steven"
    assert document.employee.middle_initial == "E"


@pytest.mark.parametrize("initial", ["D", "J", "K", "W", "M"])
def test_parser_still_recovers_other_middle_initials_after_capital_e_fix(initial: str) -> None:
    """Non-regression check: every other middle initial must still work
    exactly as before the capital-E fix."""

    observation_set = _rotated_style_observations(
        ocr_obs(f"Steven {initial}", 189, 815, 145, 24),
        ocr_obs("e Employee's first name and initial", 197, 800, 460, 24),
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id=f"paddle-rotated-initial-{initial}",
        source_filename="rotated.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.employee.first_name == "Steven"
    assert document.employee.middle_initial == initial


def test_parser_paddle_merged_label_case_still_works_after_capital_e_fix() -> None:
    """Non-regression check for the original PaddleOCR-style merged label
    case (no middle initial) after the capital-E fix."""

    observation_set = _rotated_style_observations(
        ocr_obs("Lori", 186, 815, 71, 24),
        ocr_obs("e Employee's first name and initial", 197, 800, 460, 24),
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="paddle-rotated-no-initial-after-e-fix",
        source_filename="rotated.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.employee.first_name == "Lori"
    assert document.employee.middle_initial is None


def test_parser_tesseract_fragmented_label_case_still_works_after_capital_e_fix() -> None:
    """Non-regression check for the Tesseract-style fragmented/interleaved
    label case after the capital-E fix."""

    observation_set = _rotated_style_observations(
        ocr_obs("Steven", 168, 822, 100, 24),
        ocr_obs("Employee’s", 280, 822, 130, 24),
        ocr_obs("D", 420, 822, 20, 24),
        ocr_obs("first", 460, 822, 60, 24),
        ocr_obs("name", 530, 822, 65, 24),
        ocr_obs("and", 605, 822, 45, 24),
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="tesseract-rotated-fragmented-after-e-fix",
        source_filename="rotated.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.employee.first_name == "Steven"


# --- Phase 6B: employer.name OCR layout fallback ---
#
# Investigation (docs/experiments/phase6b-employer-name-investigation.md)
# found employer.name was never recovered under OCR routing for external
# Symage documents: the real 2026 W-2 form's Box c is one combined,
# unlabeled "Employer's name, address, and ZIP code" block (employer name
# on the first line, street/city-state-ZIP on subsequent lines) with no
# literal "Name:" text the primary label-based path can match, and unlike
# employee fields, employer.name previously had no OCR zone fallback at
# all. Pixel coordinates below are the actual PaddleOCR output for the
# real symage_900001 document (see the investigation doc), the same
# document `test_parser_extracts_external_style_ocr_word_observations`
# above is already built from.


def _employer_box_c_observations() -> list[TextObservation]:
    return [
        ocr_obs("Timberline Trading Co.", 162, 414, 342, 39),
        ocr_obs("105 Penland St", 164, 454, 234, 34),
        ocr_obs("Murphy, NC 28906", 163, 489, 285, 40),
    ]


def _realistic_external_symage_900001_observations() -> list[TextObservation]:
    """The exact same real symage_900001 PaddleOCR output
    `test_parser_extracts_external_style_ocr_word_observations` above uses,
    duplicated here (rather than shared) so that already-passing test's
    fixture can never be perturbed by this investigation's additions.

    Reusing the identical observation set matters beyond convenience: every
    OCR zone fallback (SSN, EIN, employee name, and now employer name) is a
    *ratio* of `_layout_extent(observations)`, the maximum observed text
    bounding box -- not the true page pixel size. A trimmed-down fixture
    with fewer observations would shrink that computed extent and silently
    shift every zone ratio, breaking assertions that have nothing to do
    with employer.name. See docs/experiments/phase6b-employer-name-investigation.md.
    """

    return [
        ocr_obs("a", 650, 165, 15),
        ocr_obs("Employee’s", 690, 162, 150),
        ocr_obs("social", 850, 162, 75),
        ocr_obs("security", 935, 162, 100),
        ocr_obs("number", 1045, 162, 100),
        ocr_obs("242-48-4959", 805, 210, 190),
        ocr_obs("b", 175, 262, 15),
        ocr_obs("Employer", 210, 262, 122),
        ocr_obs("identification", 342, 262, 164),
        ocr_obs("number", 517, 262, 98),
        ocr_obs("(EIN)", 624, 262, 60),
        ocr_obs("1", 1413, 263, 10),
        ocr_obs("Wages,", 1449, 262, 88),
        ocr_obs("tips,", 1546, 262, 50),
        ocr_obs("other", 1605, 262, 62),
        ocr_obs("compensation", 1675, 262, 168),
        ocr_obs("2", 1922, 262, 15),
        ocr_obs("Federal", 1964, 262, 93),
        ocr_obs("income", 2069, 262, 93),
        ocr_obs("tax", 2171, 263, 39),
        ocr_obs("withheld", 2220, 262, 107),
        ocr_obs("75-5696876", 679, 310, 178),
        ocr_obs("$114,858.00", 1689, 309, 186, 30),
        ocr_obs("$21,930.26", 2218, 309, 167, 30),
        ocr_obs("3", 1412, 374, 12),
        ocr_obs("Social", 1453, 374, 88),
        ocr_obs("security", 1541, 374, 100),
        ocr_obs("wages", 1651, 374, 85),
        ocr_obs("4", 1922, 374, 15),
        ocr_obs("Social", 1963, 374, 88),
        ocr_obs("security", 2051, 374, 100),
        ocr_obs("tax", 2160, 374, 39),
        ocr_obs("withheld", 2209, 374, 107),
        ocr_obs("$122,000.00", 1693, 405, 184, 30),
        ocr_obs("$7,564.00", 2236, 409, 147, 30),
        ocr_obs("5", 1412, 473, 12),
        ocr_obs("Medicare", 1454, 473, 128),
        ocr_obs("wages", 1582, 473, 85),
        ocr_obs("and", 1676, 473, 45),
        ocr_obs("tips", 1732, 473, 50),
        ocr_obs("6", 1922, 473, 15),
        ocr_obs("Medicare", 1964, 473, 128),
        ocr_obs("tax", 2092, 473, 39),
        ocr_obs("withheld", 2140, 473, 107),
        ocr_obs("$122,000.00", 1693, 492, 184, 30),
        ocr_obs("$1,769.00", 2236, 509, 147, 30),
        ocr_obs("e", 176, 767, 15),
        ocr_obs("Employee’s", 210, 762, 150),
        ocr_obs("first", 368, 762, 50),
        ocr_obs("name", 426, 768, 72),
        ocr_obs("and", 506, 762, 49),
        ocr_obs("initial", 564, 762, 67),
        ocr_obs("Last", 739, 762, 55),
        ocr_obs("name", 802, 768, 72),
        ocr_obs("Steven", 168, 810, 100),
        ocr_obs("D", 282, 811, 20),
        ocr_obs("Armstrong", 733, 806, 151, 40),
        ocr_obs("13", 1399, 812, 30),
        ocr_obs("Retirement", 1592, 804, 112),
        ocr_obs("plan", 1595, 825, 46),
        ocr_obs("[V", 1601, 850, 36, 44),
        ocr_obs("Copy", 151, 1535, 50),
        ocr_obs("Return.", 993, 1535, 80),
    ]


def test_parser_recovers_employer_name_from_ocr_full_page_layout() -> None:
    """End-to-end reproduction of the real symage_900001 defect: the exact
    same realistic full-page fixture as
    `test_parser_extracts_external_style_ocr_word_observations` above,
    plus the three employer name/address/ZIP line observations that
    fixture deliberately omits. Before the fix, `employer.name` stayed
    `None` with no recovery path even though every other field on this
    same document already extracted correctly."""

    observation_set = ObservationSet(
        route=AcquisitionRoute.OCR,
        observations=[
            *_realistic_external_symage_900001_observations(),
            *_employer_box_c_observations(),
        ],
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="employer-name-fallback",
        source_filename="external.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.employer.name == "Timberline Trading Co."
    # The fix is scoped to employer.name only; address recovery is a
    # separate, out-of-scope gap (see the investigation doc's "Known
    # Limitations") and must not silently start working as a side effect.
    assert document.employer.address.address_line_1 is None
    # Unrelated fields recovered by other mechanisms must not regress.
    assert document.employer.ein == "75-5696876"
    assert document.employee.ssn == "242-48-4959"
    assert document.employee.first_name == "Steven"
    assert document.employee.middle_initial == "D"
    assert document.employee.last_name == "Armstrong"


def test_parser_recovers_multiword_employer_name_with_and() -> None:
    """A multi-word employer name containing "and" must survive intact.

    This specifically guards against reusing `_clean_layout_token` (whose
    Box e label-word denylist includes "and") for the employer-name zone:
    that would silently drop "and" from a real name like "Smith and Sons
    Inc." `_first_row_text_in_zone` deliberately does not use it. Built on
    the realistic full-page fixture (see
    `_realistic_external_symage_900001_observations`) so the zone ratio
    calibration matches a real document, with four Tesseract-style word
    fragments (rather than one merged PaddleOCR-style line) positioned
    across the same real employer-name pixel footprint, confirming the
    fix is backend-neutral at the word-fragment-reconstruction level too.
    """

    observation_set = ObservationSet(
        route=AcquisitionRoute.OCR,
        observations=[
            *_realistic_external_symage_900001_observations(),
            ocr_obs("Smith", 162, 414, 80, 39),
            ocr_obs("and", 250, 414, 50, 39),
            ocr_obs("Sons", 308, 414, 70, 39),
            ocr_obs("Inc.", 386, 414, 60, 39),
        ],
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="employer-name-and",
        source_filename="external.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.employer.name == "Smith and Sons Inc."


def test_parser_does_not_override_primary_path_employer_name() -> None:
    """When the primary label-based path already found a name, the OCR
    zone fallback must never override it, even if zone content exists."""

    observation_set = ObservationSet(
        route=AcquisitionRoute.OCR,
        observations=[
            obs("Name: Synthetic Payroll Fixture 0005 LLC", 330, 115),
            *_employer_box_c_observations(),
            ocr_obs("Copy", 151, 1535, 50),
            ocr_obs("Return.", 993, 1535, 80),
        ],
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="employer-name-primary-wins",
        source_filename="external.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.employer.name == "Synthetic Payroll Fixture 0005 LLC"


def test_parser_employer_name_fallback_absent_without_zone_observations() -> None:
    """No employer-name observations in the zone -> still None, not an
    exception or a spurious value (matches the pre-fix, already-passing
    `test_parser_extracts_external_style_ocr_word_observations` fixture,
    which omits Box c entirely)."""

    observation_set = ObservationSet(
        route=AcquisitionRoute.OCR,
        observations=[
            ocr_obs("Steven", 168, 810, 100),
            ocr_obs("Copy", 151, 1535, 50),
            ocr_obs("Return.", 993, 1535, 80),
        ],
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="employer-name-absent",
        source_filename="external.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.employer.name is None


def test_parser_recovers_employer_name_when_rotated_label_precedes_answer_in_zone() -> None:
    """Reproduction of the real Phase 8B rotation bug found on
    `symage_900001-...-rotated.png`: under rotation, PaddleOCR reads the
    printed Box c label ("c Employer's name, address, and ZIP code") as
    one merged line positioned topmost in the same calibrated zone as the
    real answer immediately below it. Before this fix,
    `_first_row_text_in_zone` always returned the single topmost row,
    yielding the label text as `employer.name` instead of the answer, on
    all 150/150 rotated documents for both backends. See
    docs/experiments/phase8c1-employer-name-rotation-remediation.md."""

    observation_set = ObservationSet(
        route=AcquisitionRoute.OCR,
        observations=[
            *_realistic_external_symage_900001_observations(),
            ocr_obs("c Employer's name, address, and ZIP code", 162, 390, 550, 15),
            *_employer_box_c_observations(),
        ],
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="employer-name-rotated-label-bleed",
        source_filename="external.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.employer.name == "Timberline Trading Co."


def test_parser_recovers_employer_name_when_rotated_label_fragmented_precedes_answer() -> None:
    """Same rotation label-bleed scenario as above, but with the label
    split into Tesseract-style word fragments rather than one merged
    PaddleOCR-style line, confirming the fix is backend-neutral (matches
    the real finding: zero overlap between the two backends' 150 failing
    documents each, same failure mode on both)."""

    observation_set = ObservationSet(
        route=AcquisitionRoute.OCR,
        observations=[
            *_realistic_external_symage_900001_observations(),
            ocr_obs("c", 162, 390, 15, 15),
            ocr_obs("Employer's", 185, 390, 120, 15),
            ocr_obs("name,", 313, 390, 60, 15),
            ocr_obs("address,", 381, 390, 90, 15),
            ocr_obs("and", 479, 390, 40, 15),
            ocr_obs("ZIP", 527, 390, 50, 15),
            ocr_obs("code", 585, 390, 60, 15),
            *_employer_box_c_observations(),
        ],
    )

    document, warnings = parse_w2_2026_observations(
        observation_set,
        document_id="employer-name-rotated-label-bleed-fragmented",
        source_filename="external.png",
        source_type=SourceDocumentType.PNG,
    )

    assert warnings == []
    assert document.employer.name == "Timberline Trading Co."


def test_first_row_text_in_zone_skips_rows_matched_by_skip_row_predicate() -> None:
    """Direct unit test of the new `skip_row` parameter in isolation: the
    topmost row is skipped when the predicate matches it, and the next
    row down is returned instead."""

    observations = [
        ocr_obs("c Employer's name, address, and ZIP code", 162, 390, 550, 15),
        *_employer_box_c_observations(),
    ]

    result = _first_row_text_in_zone(
        observations,
        (0.0, 1.0, 0.0, 1.0),
        skip_row=_looks_like_employer_name_label_row,
    )

    assert result == "Timberline Trading Co."


def test_first_row_text_in_zone_skip_row_none_preserves_old_topmost_behavior() -> None:
    """Without `skip_row`, behavior is unchanged from before this fix: the
    topmost row wins even if it is the label."""

    observations = [
        ocr_obs("c Employer's name, address, and ZIP code", 162, 390, 550, 15),
        *_employer_box_c_observations(),
    ]

    result = _first_row_text_in_zone(observations, (0.0, 1.0, 0.0, 1.0))

    assert result == "c Employer's name, address, and ZIP code"


def test_looks_like_employer_name_label_row_matches_the_real_printed_label() -> None:
    assert _looks_like_employer_name_label_row(
        "c Employer's name, address, and ZIP code"
    )
    assert _looks_like_employer_name_label_row("EMPLOYER'S NAME, ADDRESS, AND ZIP CODE")


@pytest.mark.parametrize(
    "employer_name",
    [
        "Timberline Trading Co.",
        "Smith and Sons Inc.",
        "Employer Solutions Group LLC",
        "ZIP Line Logistics Inc.",
    ],
)
def test_looks_like_employer_name_label_row_does_not_match_real_employer_names(
    employer_name: str,
) -> None:
    """Guards the false-positive side: a real employer name must never be
    mistaken for the label, even one that happens to contain one of the
    two marker words alone ("Employer Solutions Group LLC", "ZIP Line
    Logistics Inc."). Both markers together is required."""

    assert not _looks_like_employer_name_label_row(employer_name)


def test_first_row_text_in_zone_isolates_topmost_line_from_multiline_zone() -> None:
    """Direct unit test of the exact mechanism the root cause needed: a
    zone spanning multiple printed lines must return only the first
    (topmost) line, not every line concatenated together."""

    observations = _employer_box_c_observations()

    result = _first_row_text_in_zone(observations, (0.0, 1.0, 0.0, 1.0))

    assert result == "Timberline Trading Co."


def test_first_row_text_in_zone_joins_fragmented_words_left_to_right() -> None:
    """Tesseract-style word fragments on one row must join in reading order."""

    observations = [
        ocr_obs("Sons", 325, 415, 80, 30),
        ocr_obs("Smith", 170, 415, 90, 30),
        ocr_obs("Inc.", 410, 415, 60, 30),
        ocr_obs("and", 265, 415, 55, 30),
    ]

    result = _first_row_text_in_zone(observations, (0.0, 1.0, 0.0, 1.0))

    assert result == "Smith and Sons Inc."


def test_first_row_text_in_zone_returns_none_for_empty_zone() -> None:
    assert _first_row_text_in_zone([], (0.04, 0.35, 0.25, 0.33)) is None
