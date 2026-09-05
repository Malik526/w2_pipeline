import pytest

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.synthetic import SyntheticGenerationConfig, generate_synthetic_w2_documents
from w2_pipeline.validation.models import ValidationResult
from w2_pipeline.validation.validator import validate_w2_document


@pytest.fixture
def happy_path_document() -> W2Document:
    """A structurally complete, fully populated synthetic 2026 W-2."""

    return generate_synthetic_w2_documents(SyntheticGenerationConfig(sample_count=1))[0]


@pytest.fixture
def missing_ssn_document(happy_path_document: W2Document) -> W2Document:
    return happy_path_document.model_copy(
        update={"employee": happy_path_document.employee.model_copy(update={"ssn": None})}
    )


@pytest.fixture
def needs_review_result(missing_ssn_document: W2Document) -> ValidationResult:
    return validate_w2_document(missing_ssn_document)


@pytest.fixture
def accepted_result(happy_path_document: W2Document) -> ValidationResult:
    return validate_w2_document(happy_path_document)
