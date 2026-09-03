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
