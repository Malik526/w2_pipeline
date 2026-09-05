from pathlib import Path

import pytest

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.review.errors import ReviewRecordNotFoundError
from w2_pipeline.review.repository import FileReviewRepository
from w2_pipeline.review.workflow import apply_correction, start_review
from w2_pipeline.validation.models import ValidationResult


def test_save_and_get_round_trips_a_record(
    tmp_path: Path, missing_ssn_document: W2Document, needs_review_result: ValidationResult
) -> None:
    repository = FileReviewRepository(tmp_path)
    record = start_review(missing_ssn_document, needs_review_result, document_id="doc-1")

    repository.save(record)
    loaded = repository.get(record.review_id)

    assert loaded == record


def test_save_overwrites_existing_record_with_same_id(
    tmp_path: Path, missing_ssn_document: W2Document, needs_review_result: ValidationResult
) -> None:
    repository = FileReviewRepository(tmp_path)
    record = start_review(missing_ssn_document, needs_review_result, document_id="doc-1")
    repository.save(record)

    corrected = apply_correction(record, field_path="employee.ssn", new_value="123-45-6789")
    repository.save(corrected)

    loaded = repository.get(record.review_id)
    assert loaded.status.value == "in_review"
    assert len(loaded.corrections) == 1


def test_get_raises_for_unknown_review_id(tmp_path: Path) -> None:
    repository = FileReviewRepository(tmp_path)

    with pytest.raises(ReviewRecordNotFoundError):
        repository.get("does-not-exist")


def test_list_returns_every_saved_record(
    tmp_path: Path, missing_ssn_document: W2Document, needs_review_result: ValidationResult
) -> None:
    repository = FileReviewRepository(tmp_path)
    record_a = start_review(missing_ssn_document, needs_review_result, document_id="doc-a")
    record_b = start_review(missing_ssn_document, needs_review_result, document_id="doc-b")
    repository.save(record_a)
    repository.save(record_b)

    records = repository.list()

    assert {record.document_id for record in records} == {"doc-a", "doc-b"}


def test_list_returns_empty_for_new_repository(tmp_path: Path) -> None:
    repository = FileReviewRepository(tmp_path / "fresh")

    assert repository.list() == []


def test_filenames_are_review_id_only_not_document_metadata(
    tmp_path: Path, missing_ssn_document: W2Document, needs_review_result: ValidationResult
) -> None:
    repository = FileReviewRepository(tmp_path)
    record = start_review(missing_ssn_document, needs_review_result, document_id="doc-1")

    repository.save(record)

    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    assert files[0].stem == record.review_id
    # No employee name/SSN in the filename.
    assert missing_ssn_document.employee.first_name not in files[0].name
