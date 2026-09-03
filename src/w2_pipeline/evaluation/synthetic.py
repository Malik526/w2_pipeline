"""Deterministic synthetic canonical W-2 sample generation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from random import Random

from w2_pipeline.contracts.w2 import (
    Address,
    Box12Entry,
    Box13Flags,
    Box14Entry,
    Employee,
    Employer,
    FederalWagesAndTaxes,
    FieldObservation,
    FieldStatus,
    SourceFileType,
    StateLocalEntry,
    TippedOccupationCode,
    W2Document,
    W2Metadata,
)

DEFAULT_SYNTHETIC_SEED = 2026
SYNTHETIC_GENERATOR_VERSION = "2026.phase3.v1"


@dataclass(frozen=True)
class SyntheticGenerationConfig:
    """Configuration for deterministic semantic W-2 sample generation."""

    sample_count: int = 12
    seed: int = DEFAULT_SYNTHETIC_SEED
    tax_year: int = 2026


def generate_synthetic_w2_documents(
    config: SyntheticGenerationConfig | None = None,
) -> list[W2Document]:
    """Generate structurally valid synthetic W-2 documents."""

    resolved_config = config or SyntheticGenerationConfig()
    if resolved_config.tax_year != 2026:
        raise ValueError("Only tax year 2026 synthetic W-2 generation is supported.")
    if resolved_config.sample_count < 1:
        raise ValueError("sample_count must be at least 1.")

    random = Random(resolved_config.seed)
    return [
        _generate_document(sample_number=index + 1, random=random)
        for index in range(resolved_config.sample_count)
    ]


def _generate_document(*, sample_number: int, random: Random) -> W2Document:
    sample_id = f"w2_2026_{sample_number:04d}"
    wages = _money(random, minimum_cents=28_000_00, maximum_cents=185_000_00)
    federal_withheld = (wages * Decimal("0.117")).quantize(Decimal("0.01"))
    social_security_wages = wages if sample_number % 5 else None
    social_security_tax = (
        (social_security_wages * Decimal("0.062")).quantize(Decimal("0.01"))
        if social_security_wages is not None
        else None
    )
    medicare_wages = wages + _money(random, minimum_cents=0, maximum_cents=2_500_00)
    medicare_tax = (medicare_wages * Decimal("0.0145")).quantize(Decimal("0.01"))

    return W2Document(
        metadata=W2Metadata(
            document_type="W-2",
            tax_year=2026,
            schema_version=2026,
            document_id=sample_id,
            source_filename=f"{sample_id}_synthetic.pdf",
            source_file_type=SourceFileType.PDF,
        ),
        employee=_employee(sample_number),
        employer=_employer(sample_number),
        federal_wages_and_taxes=FederalWagesAndTaxes(
            box_1_wages_tips_other_compensation=wages,
            box_2_federal_income_tax_withheld=federal_withheld,
            box_3_social_security_wages=social_security_wages,
            box_4_social_security_tax_withheld=social_security_tax,
            box_5_medicare_wages_and_tips=medicare_wages,
            box_6_medicare_tax_withheld=medicare_tax,
            box_7_social_security_tips=_optional_money(random, sample_number, 2),
            box_8_allocated_tips=_optional_money(random, sample_number, 3),
            box_9_verification_code=None,
            box_10_dependent_care_benefits=_optional_money(random, sample_number, 5),
            box_11_nonqualified_plans=_optional_money(random, sample_number, 6),
        ),
        box_12_entries=_box_12_entries(sample_number, random),
        box_13=Box13Flags(
            statutory_employee=sample_number % 2 == 0,
            retirement_plan=sample_number % 3 == 0,
            third_party_sick_pay=sample_number % 4 == 0,
        ),
        box_14_entries=_box_14_entries(sample_number, random),
        tipped_occupation_codes=_tipped_occupation_codes(sample_number),
        state_local_entries=_state_local_entries(sample_number, wages, random),
        field_observations=_field_observations(sample_number),
    )


def _employee(sample_number: int) -> Employee:
    return Employee(
        ssn=f"000-00-{sample_number:04d}",
        first_name=f"SyntheticFirst{sample_number:04d}",
        middle_initial=chr(65 + (sample_number % 26)) if sample_number % 3 else None,
        last_name=f"SyntheticLast{sample_number:04d}",
        suffix=None,
        address=Address(
            address_line_1=f"{1000 + sample_number} Synthetic Test Ave",
            address_line_2=f"Unit {sample_number}" if sample_number % 2 else None,
            city="Faketown",
            state=("NY", "NJ", "PA", "CT")[sample_number % 4],
            postal_code=f"00{sample_number:03d}",
            country="US",
        ),
    )


def _employer(sample_number: int) -> Employer:
    return Employer(
        ein=f"00-{sample_number:07d}",
        name=f"Synthetic Payroll Fixture {sample_number:04d} LLC",
        address=Address(
            address_line_1=f"{2000 + sample_number} Fixture Payroll Plaza",
            address_line_2="Suite 2026" if sample_number % 2 else None,
            city="Example City",
            state=("DE", "NY", "NJ")[sample_number % 3],
            postal_code=f"10{sample_number:03d}",
            country="US",
        ),
        control_number=f"SYN-CTRL-{sample_number:04d}" if sample_number % 5 else None,
    )


def _box_12_entries(sample_number: int, random: Random) -> list[Box12Entry]:
    entry_count = sample_number % 3
    codes = ("D", "DD", "W", "C")
    return [
        Box12Entry(
            code=codes[(sample_number + index) % len(codes)],
            amount=_money(random, minimum_cents=100_00, maximum_cents=12_000_00),
        )
        for index in range(entry_count)
    ]


def _box_14_entries(sample_number: int, random: Random) -> list[Box14Entry]:
    entries = [
        Box14Entry(
            label="SYNUNION",
            amount=_money(random, minimum_cents=10_00, maximum_cents=900_00),
        )
    ]
    if sample_number % 2 == 0:
        entries.append(Box14Entry(label="SYNMEMO", value=f"Synthetic note {sample_number:04d}"))
    return entries


def _tipped_occupation_codes(sample_number: int) -> list[TippedOccupationCode]:
    if sample_number % 4 != 0:
        return []
    return [TippedOccupationCode(code=f"SYN-TIP-{sample_number:03d}")]


def _state_local_entries(
    sample_number: int,
    wages: Decimal,
    random: Random,
) -> list[StateLocalEntry]:
    primary_state = ("NY", "NJ", "PA", "CT")[sample_number % 4]
    entries = [
        StateLocalEntry(
            box_15_state=primary_state,
            box_15_employer_state_id_number=f"{primary_state}-SYN-{sample_number:06d}",
            box_16_state_wages_tips_etc=wages,
            box_17_state_income_tax=(wages * Decimal("0.047")).quantize(Decimal("0.01")),
            box_18_local_wages_tips_etc=(
                (wages * Decimal("0.25")).quantize(Decimal("0.01"))
                if sample_number % 2
                else None
            ),
            box_19_local_income_tax=_optional_money(random, sample_number, 2),
            box_20_locality_name="SYNLOCAL" if sample_number % 2 else None,
        )
    ]
    if sample_number % 4 == 0:
        secondary_state = "NJ" if primary_state != "NJ" else "NY"
        entries.append(
            StateLocalEntry(
                box_15_state=secondary_state,
                box_15_employer_state_id_number=f"{secondary_state}-SYN-{sample_number:06d}",
                box_16_state_wages_tips_etc=(wages * Decimal("0.15")).quantize(Decimal("0.01")),
                box_17_state_income_tax=_money(random, minimum_cents=25_00, maximum_cents=300_00),
            )
        )
    return entries


def _field_observations(sample_number: int) -> list[FieldObservation]:
    observations: list[FieldObservation] = []
    if sample_number % 3 == 0:
        observations.append(
            FieldObservation(
                field_path="employee.middle_initial",
                status=FieldStatus.NOT_APPLICABLE,
                raw_value=None,
                message="Synthetic fixture omits a middle initial.",
            )
        )
    if sample_number % 4 == 0:
        observations.append(
            FieldObservation(
                field_path="employee.suffix",
                status=FieldStatus.OBSERVED_BLANK,
                raw_value="",
            )
        )
    return observations


def _optional_money(
    random: Random,
    sample_number: int,
    divisor: int,
) -> Decimal | None:
    if sample_number % divisor:
        return None
    return _money(random, minimum_cents=0, maximum_cents=5_000_00)


def _money(random: Random, *, minimum_cents: int, maximum_cents: int) -> Decimal:
    cents = random.randrange(minimum_cents, maximum_cents + 1)
    return (Decimal(cents) / Decimal(100)).quantize(Decimal("0.01"))
