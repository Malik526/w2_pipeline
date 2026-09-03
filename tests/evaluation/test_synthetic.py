from decimal import Decimal

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.synthetic import (
    SyntheticGenerationConfig,
    generate_synthetic_w2_documents,
)


def test_synthetic_generation_is_deterministic_with_fixed_seed() -> None:
    config = SyntheticGenerationConfig(sample_count=5, seed=2026)

    first = generate_synthetic_w2_documents(config)
    second = generate_synthetic_w2_documents(config)

    assert [document.model_dump() for document in first] == [
        document.model_dump() for document in second
    ]


def test_synthetic_documents_validate_against_canonical_contract() -> None:
    documents = generate_synthetic_w2_documents(SyntheticGenerationConfig(sample_count=12))

    assert all(isinstance(document, W2Document) for document in documents)
    assert all(document.metadata.tax_year == 2026 for document in documents)
    assert all(document.employee.first_name.startswith("SyntheticFirst") for document in documents)
    assert all(document.employee.ssn.startswith("000-00-") for document in documents)
    assert all(document.employer.ein.startswith("00-") for document in documents)


def test_synthetic_generation_exercises_meaningful_schema_variation() -> None:
    documents = generate_synthetic_w2_documents(SyntheticGenerationConfig(sample_count=12))

    box_12_lengths = {len(document.box_12_entries) for document in documents}
    state_local_lengths = {len(document.state_local_entries) for document in documents}
    retirement_values = {document.box_13.retirement_plan for document in documents}
    optional_box_7_values = {
        document.federal_wages_and_taxes.box_7_social_security_tips is None
        for document in documents
    }

    assert {0, 1, 2}.issubset(box_12_lengths)
    assert {1, 2}.issubset(state_local_lengths)
    assert retirement_values == {False, True}
    assert optional_box_7_values == {False, True}
    assert any(document.tipped_occupation_codes for document in documents)
    assert any(document.field_observations for document in documents)


def test_ground_truth_round_trip_preserves_decimals_and_nulls() -> None:
    document = generate_synthetic_w2_documents(SyntheticGenerationConfig(sample_count=6))[5]
    json_payload = document.model_dump_json()

    round_tripped = W2Document.model_validate_json(json_payload)

    assert isinstance(
        round_tripped.federal_wages_and_taxes.box_1_wages_tips_other_compensation,
        Decimal,
    )
    assert round_tripped.employee.middle_initial is None
    assert round_tripped == document


def test_internal_synthetic_2026_ground_truth_does_not_invent_box_9() -> None:
    documents = generate_synthetic_w2_documents(SyntheticGenerationConfig(sample_count=12))

    assert all(
        document.federal_wages_and_taxes.box_9_verification_code is None
        for document in documents
    )
