from decimal import Decimal

from w2_pipeline.evaluation.comparison import compare_w2_documents, flatten_w2_document
from w2_pipeline.evaluation.models import EvaluationFailureKind
from w2_pipeline.evaluation.synthetic import (
    SyntheticGenerationConfig,
    generate_synthetic_w2_documents,
)


def _sample_pair():
    document = generate_synthetic_w2_documents(
        SyntheticGenerationConfig(sample_count=5, seed=2026)
    )[4]
    return document, document.model_copy(deep=True)


def test_perfect_prediction_has_full_field_accuracy() -> None:
    expected, predicted = _sample_pair()

    evaluation = compare_w2_documents(
        expected=expected,
        predicted=predicted,
        sample_id="w2_2026_0004",
        variant_id="clean_pdf",
    )

    assert evaluation.field_accuracy == 1.0
    assert evaluation.correct_fields == evaluation.total_fields
    assert evaluation.failures == []


def test_incorrect_field_decreases_accuracy_and_is_mismatch() -> None:
    expected, predicted = _sample_pair()
    predicted.employee.last_name = "SyntheticWrong"

    evaluation = compare_w2_documents(
        expected=expected,
        predicted=predicted,
        sample_id="w2_2026_0004",
        variant_id="clean_pdf",
    )

    failure = next(issue for issue in evaluation.failures if issue.field_path == "employee.last_name")
    assert evaluation.field_accuracy < 1.0
    assert failure.kind == EvaluationFailureKind.MISMATCH


def test_expected_value_predicted_null_is_missing() -> None:
    expected, predicted = _sample_pair()
    predicted.employee.ssn = None

    evaluation = compare_w2_documents(
        expected=expected,
        predicted=predicted,
        sample_id="w2_2026_0004",
        variant_id="clean_pdf",
    )

    failure = next(issue for issue in evaluation.failures if issue.field_path == "employee.ssn")
    assert failure.kind == EvaluationFailureKind.MISSING


def test_null_vs_null_is_correct() -> None:
    expected, predicted = _sample_pair()
    expected.employer.control_number = None
    predicted.employer.control_number = None

    evaluation = compare_w2_documents(
        expected=expected,
        predicted=predicted,
        sample_id="w2_2026_0004",
        variant_id="clean_pdf",
    )
    control_field = next(
        field for field in evaluation.field_evaluations if field.field_path == "employer.control_number"
    )

    assert control_field.correct is True


def test_employee_middle_initial_is_scored_separately_from_first_name() -> None:
    expected, predicted = _sample_pair()
    expected.employee.first_name = "William"
    expected.employee.middle_initial = "G"
    expected.employee.last_name = "Hernandez"
    predicted.employee.first_name = "William"
    predicted.employee.middle_initial = None
    predicted.employee.last_name = "Hernandez"

    evaluation = compare_w2_documents(
        expected=expected,
        predicted=predicted,
        sample_id="w2_2026_0004",
        variant_id="clean_pdf",
        evaluated_field_paths=[
            "employee.first_name",
            "employee.middle_initial",
            "employee.last_name",
        ],
    )

    first = next(
        field for field in evaluation.field_evaluations if field.field_path == "employee.first_name"
    )
    middle = next(
        field
        for field in evaluation.field_evaluations
        if field.field_path == "employee.middle_initial"
    )
    last = next(
        field for field in evaluation.field_evaluations if field.field_path == "employee.last_name"
    )

    assert first.correct is True
    assert middle.correct is False
    assert middle.failure_kind == EvaluationFailureKind.MISSING
    assert last.correct is True


def test_employee_name_accents_are_exact_semantic_mismatches() -> None:
    expected, predicted = _sample_pair()
    expected.employee.first_name = "Jesús"
    predicted.employee.first_name = "Jesus"

    evaluation = compare_w2_documents(
        expected=expected,
        predicted=predicted,
        sample_id="w2_2026_0004",
        variant_id="clean_pdf",
        evaluated_field_paths=["employee.first_name"],
    )

    failure = evaluation.failures[0]
    assert failure.field_path == "employee.first_name"
    assert failure.kind == EvaluationFailureKind.MISMATCH


def test_decimal_mismatch_is_detected_without_float_conversion() -> None:
    expected, predicted = _sample_pair()
    predicted.federal_wages_and_taxes.box_1_wages_tips_other_compensation += Decimal("0.01")

    evaluation = compare_w2_documents(
        expected=expected,
        predicted=predicted,
        sample_id="w2_2026_0004",
        variant_id="clean_pdf",
    )

    failure = next(
        issue
        for issue in evaluation.failures
        if issue.field_path == "federal_wages_and_taxes.box_1_wages_tips_other_compensation"
    )
    assert failure.kind == EvaluationFailureKind.MISMATCH


def test_repeated_fields_are_compared_by_documented_index_strategy() -> None:
    expected, predicted = _sample_pair()
    predicted.box_12_entries = list(reversed(predicted.box_12_entries))

    evaluation = compare_w2_documents(
        expected=expected,
        predicted=predicted,
        sample_id="w2_2026_0004",
        variant_id="clean_pdf",
    )

    failure_paths = {issue.field_path for issue in evaluation.failures}
    assert "box_12_entries[0].code" in failure_paths
    assert "box_12_entries[1].amount" in failure_paths


def test_flattening_excludes_operational_metadata_and_field_observations() -> None:
    expected, _ = _sample_pair()

    flattened = flatten_w2_document(expected)

    assert "metadata.tax_year" in flattened
    assert "metadata.document_id" not in flattened
    assert all(not path.startswith("field_observations") for path in flattened)
