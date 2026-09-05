from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.validation.models import (
    ExtractionOutcome,
    ExtractionSignals,
    ValidationSeverity,
    ValidationStatus,
)
from w2_pipeline.validation.routing import RoutingPolicy
from w2_pipeline.validation.rules import ALL_RULE_NAMES
from w2_pipeline.validation.validator import validate_w2_document


def test_happy_path_document_is_accepted(happy_path_document: W2Document) -> None:
    result = validate_w2_document(happy_path_document)

    assert result.status == ValidationStatus.ACCEPTED
    assert [issue for issue in result.issues if issue.severity == ValidationSeverity.ERROR] == []
    assert result.checks_run == len(ALL_RULE_NAMES)


def test_missing_ssn_is_needs_review(happy_path_document: W2Document) -> None:
    document = happy_path_document.model_copy(
        update={"employee": happy_path_document.employee.model_copy(update={"ssn": None})}
    )

    result = validate_w2_document(document)

    assert result.status == ValidationStatus.NEEDS_REVIEW
    assert any(issue.code == "required_field_missing" for issue in result.issues)


def test_none_document_is_needs_review_with_extraction_output_invalid() -> None:
    result = validate_w2_document(None)

    assert result.status == ValidationStatus.NEEDS_REVIEW
    assert len(result.issues) == 1
    assert result.issues[0].code == "extraction_output_invalid"
    assert result.issues[0].severity == ValidationSeverity.ERROR
    assert result.checks_run == 1


def test_none_document_skips_all_field_rules() -> None:
    # A None document can't have field-level issues -- only the one
    # extraction_output_invalid issue, never a required_field_missing, etc.
    result = validate_w2_document(None)

    assert {issue.code for issue in result.issues} == {"extraction_output_invalid"}


def test_extraction_failed_signal_with_valid_document_is_needs_review(
    happy_path_document: W2Document,
) -> None:
    signals = ExtractionSignals(pipeline_id="pipeline_a", outcome=ExtractionOutcome.EXTRACTION_FAILED)

    result = validate_w2_document(happy_path_document, signals=signals)

    assert result.status == ValidationStatus.NEEDS_REVIEW
    assert any(issue.code == "extraction_failure" for issue in result.issues)


def test_pipeline_metadata_recorded_when_signals_provided(happy_path_document: W2Document) -> None:
    signals = ExtractionSignals(pipeline_id="pipeline_b", route="vlm", document_condition="clean")

    result = validate_w2_document(happy_path_document, signals=signals)

    assert result.pipeline_metadata == {
        "pipeline_id": "pipeline_b",
        "route": "vlm",
        "document_condition": "clean",
    }


def test_pipeline_metadata_none_when_no_signals_given(happy_path_document: W2Document) -> None:
    result = validate_w2_document(happy_path_document)

    assert result.pipeline_metadata is None


def test_conservative_policy_sends_warning_only_document_to_review(
    happy_path_document: W2Document,
) -> None:
    from w2_pipeline.contracts.w2 import StateLocalEntry

    document = happy_path_document.model_copy(
        update={"state_local_entries": [StateLocalEntry()]}
    )

    default_result = validate_w2_document(document)
    conservative_result = validate_w2_document(document, policy=RoutingPolicy(escalate_warnings=True))

    assert default_result.status == ValidationStatus.ACCEPTED
    assert conservative_result.status == ValidationStatus.NEEDS_REVIEW


def test_validate_w2_document_backend_neutral_for_pipeline_a_and_b_signals(
    happy_path_document: W2Document,
) -> None:
    pipeline_a_result = validate_w2_document(
        happy_path_document, signals=ExtractionSignals(pipeline_id="pipeline_a", route="ocr")
    )
    pipeline_b_result = validate_w2_document(
        happy_path_document, signals=ExtractionSignals(pipeline_id="pipeline_b", route="vlm")
    )

    # Same document, same rules, same routing outcome -- only the recorded
    # pipeline metadata differs. The validator does not branch on pipeline
    # identity anywhere.
    assert pipeline_a_result.status == pipeline_b_result.status == ValidationStatus.ACCEPTED
    assert pipeline_a_result.issues == pipeline_b_result.issues
    assert pipeline_a_result.pipeline_metadata != pipeline_b_result.pipeline_metadata
