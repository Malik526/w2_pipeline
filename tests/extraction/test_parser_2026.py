from decimal import Decimal

import pytest

from w2_pipeline.extraction.models import (
    AcquisitionRoute,
    BoundingBox,
    ObservationSet,
    ObservationSource,
    TextObservation,
)
from w2_pipeline.extraction.parser_2026 import parse_money, parse_w2_2026_observations
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
