"""Canonical Pydantic contract for 2026 Form W-2 data.

The models in this module define the single typed internal structure that
future extraction pipelines must produce. They intentionally enforce only
structural/type constraints; IRS tax and business-rule validation belongs to a
later validation layer.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator


class ContractModel(BaseModel):
    """Base model for strict contract shape without tax-domain validation."""

    model_config = ConfigDict(extra="forbid")


Money = Decimal


class SourceFileType(str, Enum):
    """Initial source document types accepted by the system boundary."""

    PDF = "pdf"
    JPEG = "jpeg"
    JPG = "jpg"
    PNG = "png"


class FieldStatus(str, Enum):
    """Lightweight status for nullable fields when the value alone is unclear."""

    OBSERVED_BLANK = "observed_blank"
    NOT_APPLICABLE = "not_applicable"
    EXTRACTION_FAILED = "extraction_failed"


class FieldObservation(ContractModel):
    """Records blank, not-applicable, or failed extraction state for a field."""

    field_path: str = Field(
        min_length=1,
        description="Dotted canonical field path, such as employee.middle_initial.",
    )
    status: FieldStatus
    raw_value: str | None = None
    message: str | None = None


class W2Metadata(ContractModel):
    """Version-aware metadata for the initial 2026 W-2 schema contract."""

    document_type: Literal["W-2"]
    tax_year: Literal[2026]
    schema_version: Literal[2026]
    document_id: str = Field(min_length=1)
    source_filename: str | None = None
    source_file_type: SourceFileType


class Address(ContractModel):
    """Postal address block shared by employee and employer models."""

    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None


class Employee(ContractModel):
    """Employee identity fields represented on the 2026 Form W-2."""

    ssn: str | None = None
    first_name: str | None = None
    middle_initial: str | None = None
    last_name: str | None = None
    suffix: str | None = None
    address: Address


class Employer(ContractModel):
    """Employer identity fields represented on the 2026 Form W-2."""

    ein: str | None = None
    name: str | None = None
    address: Address
    control_number: str | None = None


class FederalWagesAndTaxes(ContractModel):
    """Federal W-2 Boxes 1 through 11."""

    box_1_wages_tips_other_compensation: Money | None = None
    box_2_federal_income_tax_withheld: Money | None = None
    box_3_social_security_wages: Money | None = None
    box_4_social_security_tax_withheld: Money | None = None
    box_5_medicare_wages_and_tips: Money | None = None
    box_6_medicare_tax_withheld: Money | None = None
    box_7_social_security_tips: Money | None = None
    box_8_allocated_tips: Money | None = None
    box_9_verification_code: str | None = None
    box_10_dependent_care_benefits: Money | None = None
    box_11_nonqualified_plans: Money | None = None


class Box12Entry(ContractModel):
    """One IRS Box 12 coded item: an IRS-defined code paired with an amount.

    Per the 2026 Form W-2 instructions, Box 12 represents coded items,
    not a fixed set of visually printed slots (12a-12d is a print-layout
    convenience, not part of the data model) -- `code` and `amount` are
    both required precisely because a "slot" with no code is not a
    coded item at all, whether the form prints it blank or with a
    placeholder "$0.00" (confirmed empirically, Phase 8D.1B: across all
    600 real slots audited, a blank code's amount is always either
    blank or exactly "$0.00", never a real nonzero value -- see
    `docs/experiments/phase8d1b-address-safety-and-box12-slot-semantics.md`).
    A slot with neither a real code nor a real amount is simply not
    represented here at all, the same way an unused line is not
    represented as an empty `Box12Entry`.
    """

    code: str = Field(min_length=1, max_length=2)
    amount: Money


class Box13Flags(ContractModel):
    """Box 13 checkbox fields."""

    statutory_employee: StrictBool = False
    retirement_plan: StrictBool = False
    third_party_sick_pay: StrictBool = False


class Box14Entry(ContractModel):
    """Flexible repeated Box 14a other entry."""

    label: str = Field(min_length=1)
    amount: Money | None = None
    value: str | None = None

    @model_validator(mode="after")
    def require_amount_or_value(self) -> "Box14Entry":
        if self.amount is None and self.value is None:
            raise ValueError("Box 14 entries require either amount or value.")
        return self


class TippedOccupationCode(ContractModel):
    """Box 14b Treasury tipped occupation code entry from the 2026 form."""

    code: str = Field(min_length=1)


class StateLocalEntry(ContractModel):
    """Repeated state/local W-2 Boxes 15 through 20."""

    box_15_state: str | None = None
    box_15_employer_state_id_number: str | None = None
    box_16_state_wages_tips_etc: Money | None = None
    box_17_state_income_tax: Money | None = None
    box_18_local_wages_tips_etc: Money | None = None
    box_19_local_income_tax: Money | None = None
    box_20_locality_name: str | None = None


class W2Document(ContractModel):
    """Canonical 2026 W-2 document produced by future extraction pipelines."""

    metadata: W2Metadata
    employee: Employee
    employer: Employer
    federal_wages_and_taxes: FederalWagesAndTaxes
    box_12_entries: list[Box12Entry] = Field(default_factory=list)
    box_13: Box13Flags
    box_14_entries: list[Box14Entry] = Field(default_factory=list)
    tipped_occupation_codes: list[TippedOccupationCode] = Field(default_factory=list)
    state_local_entries: list[StateLocalEntry] = Field(default_factory=list)
    field_observations: list[FieldObservation] = Field(default_factory=list)
