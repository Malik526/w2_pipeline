"""Phase 8D.4: single-document production runner service tests.

The accepted-path test exercises the real `PipelineAExtractor` end to
end (ingestion -> native-PDF extraction -> validation -> finalize ->
export) against a generated clean PDF -- no OCR backend is ever invoked
for a native-PDF route, so this needs neither GPU nor a real OCR engine,
matching this project's existing `tests/extraction/test_pipeline_a.py`
convention.

The needs_review/failure/regression tests inject a minimal fake
extractor (only `ingestion_service.ingest` and `extract_ingested` --
the exact `W2Extractor`-shaped boundary `PipelineAExtractor` itself
satisfies) so the OCR/PaddleOCR step, which the full suite must not
depend on, is the only thing stubbed. Every other step -- signal
construction, validation, finalize, export, review persistence -- is
the real production code.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from w2_pipeline.contracts.w2 import (
    Address,
    Box13Flags,
    Employee,
    Employer,
    FederalWagesAndTaxes,
    W2Document,
    W2Metadata,
)
from w2_pipeline.evaluation.dataset import generate_evaluation_dataset
from w2_pipeline.extraction.models import (
    AcquisitionRoute,
    AddressExtractionEvidence,
    Box13CheckboxEvidence,
    ExtractionResult,
)
from w2_pipeline.extraction.pipeline_a import PipelineAExtractor
from w2_pipeline.application.run_document import DocumentRunStatus, run_document
from w2_pipeline.review.repository import FileReviewRepository


def _minimal_valid_document(*, retirement_plan: bool = False, with_addresses: bool = True) -> W2Document:
    address = (
        Address(address_line_1="1 Main St", city="Springfield", state="IL", postal_code="62704")
        if with_addresses
        else Address()
    )
    return W2Document(
        metadata=W2Metadata(
            document_type="W-2",
            tax_year=2026,
            schema_version=2026,
            document_id="doc-1",
            source_file_type="png",
        ),
        employee=Employee(ssn="242-48-4959", first_name="Steven", last_name="Armstrong", address=address),
        employer=Employer(ein="75-5696876", name="Timberline Trading Co.", address=address),
        federal_wages_and_taxes=FederalWagesAndTaxes(
            box_1_wages_tips_other_compensation=Decimal("100.00"),
            box_2_federal_income_tax_withheld=Decimal("10.00"),
            box_5_medicare_wages_and_tips=Decimal("100.00"),
            box_6_medicare_tax_withheld=Decimal("1.00"),
        ),
        box_13=Box13Flags(retirement_plan=retirement_plan),
    )


_FULL_CHECKBOX_EVIDENCE = Box13CheckboxEvidence(
    detection_method="anchor_relative",
    fallback_used=False,
    anchor_found=True,
    checkbox_found=True,
    decision_margin=5.0,
)
_COMPLETE_ADDRESS_EVIDENCE = AddressExtractionEvidence(
    region_observation_count=5, usable_row_count=3, parse_complete=True
)


class _FakeIngestionService:
    def ingest(self, path: str | Path, document_id: str | None = None):  # noqa: ANN001 - test double
        return object()


class _FakeExtractor:
    """Minimal `PipelineAExtractor`-shaped double: no OCR/GPU dependency."""

    pipeline_id = "pipeline_a"

    def __init__(self, result_factory) -> None:  # noqa: ANN001 - test double
        self.ingestion_service = _FakeIngestionService()
        self._result_factory = result_factory
        self.warm_up_calls = 0

    def warm_up(self) -> None:
        self.warm_up_calls += 1

    def extract_ingested(self, ingested):  # noqa: ANN001 - test double
        return self._result_factory()


def _accepted_ocr_result() -> ExtractionResult:
    return ExtractionResult(
        document=_minimal_valid_document(retirement_plan=True),
        route=AcquisitionRoute.OCR,
        observation_count=42,
        box_13_checkbox_evidence=_FULL_CHECKBOX_EVIDENCE,
        employer_address_evidence=_COMPLETE_ADDRESS_EVIDENCE,
        employee_address_evidence=_COMPLETE_ADDRESS_EVIDENCE,
    )


def _needs_review_ocr_result_missing_checkbox_evidence() -> ExtractionResult:
    return ExtractionResult(
        document=_minimal_valid_document(),
        route=AcquisitionRoute.OCR,
        observation_count=42,
        box_13_checkbox_evidence=None,
    )


def test_accepted_path_real_native_pdf_extraction_finalizes_and_exports(tmp_path: Path) -> None:
    generate_evaluation_dataset(tmp_path, sample_count=1, seed=2026)
    pdf_path = tmp_path / "documents" / "w2_2026_0001_clean.pdf"

    result = run_document(
        pdf_path,
        output_dir=tmp_path / "output",
        ocr_backend="tesseract",
        extractor=PipelineAExtractor(),
        review_repo_dir=tmp_path / "review",
    )

    assert result.status is DocumentRunStatus.ACCEPTED
    assert result.route == "native_pdf"
    assert result.validation_status == "accepted"
    assert result.issue_codes == []
    assert result.finalized is True
    assert result.review_id is None

    doc_dir = tmp_path / "output" / result.document_id
    assert (doc_dir / "extracted.json").exists()
    assert (doc_dir / "signals.json").exists()
    assert (doc_dir / "validation.json").exists()
    assert (doc_dir / "final.json").exists()
    assert (doc_dir / "final.csv").exists()
    assert (doc_dir / "run_summary.json").exists()


def test_needs_review_path_blocks_finalization_and_persists_review_record(tmp_path: Path) -> None:
    extractor = _FakeExtractor(_needs_review_ocr_result_missing_checkbox_evidence)

    result = run_document(
        tmp_path / "input.png",
        output_dir=tmp_path / "output",
        extractor=extractor,
        review_repo_dir=tmp_path / "review",
    )

    assert result.status is DocumentRunStatus.NEEDS_REVIEW
    assert result.validation_status == "needs_review"
    assert "retirement_plan_checkbox_evidence_missing" in result.issue_codes
    assert result.finalized is False
    assert result.outputs == {}
    assert result.review_id is not None

    doc_dir = tmp_path / "output" / result.document_id
    assert not (doc_dir / "final.json").exists()
    assert not (doc_dir / "final.csv").exists()
    assert (doc_dir / "extracted.json").exists()
    assert (doc_dir / "validation.json").exists()
    assert (doc_dir / "run_summary.json").exists()

    persisted = FileReviewRepository(tmp_path / "review").get(result.review_id)
    assert persisted.document_id == result.document_id
    assert persisted.validation_result.status.value == "needs_review"


def test_runtime_extraction_failure_produces_no_trusted_output(tmp_path: Path) -> None:
    def _raise():
        raise RuntimeError("simulated OCR crash")

    extractor = _FakeExtractor(_raise)

    result = run_document(
        tmp_path / "input.png",
        output_dir=tmp_path / "output",
        extractor=extractor,
        review_repo_dir=tmp_path / "review",
    )

    assert result.status is DocumentRunStatus.FAILED
    assert "simulated OCR crash" in result.error_message
    assert result.outputs == {}
    assert result.finalized is False

    doc_dir = tmp_path / "output" / result.document_id
    assert not (doc_dir / "final.json").exists()
    assert not (doc_dir / "extracted.json").exists()
    assert (doc_dir / "run_summary.json").exists()


def test_nonexistent_input_file_fails_cleanly(tmp_path: Path) -> None:
    result = run_document(
        tmp_path / "does_not_exist.png",
        output_dir=tmp_path / "output",
        ocr_backend="tesseract",
        review_repo_dir=tmp_path / "review",
    )

    assert result.status is DocumentRunStatus.FAILED
    assert result.error_message is not None
    assert result.outputs == {}


def test_unsupported_input_extension_fails_cleanly(tmp_path: Path) -> None:
    bad_input = tmp_path / "not_a_w2.txt"
    bad_input.write_text("hello", encoding="utf-8")

    result = run_document(
        bad_input,
        output_dir=tmp_path / "output",
        ocr_backend="tesseract",
        review_repo_dir=tmp_path / "review",
    )

    assert result.status is DocumentRunStatus.FAILED
    assert result.outputs == {}


def test_regression_full_evidence_is_threaded_not_just_route(tmp_path: Path) -> None:
    """Phase 8D.2 regression guard: the runner must never validate a real
    OCR-route extraction with `route=ocr` and no evidence (the exact bug
    `review/cli.py`'s `--signals-json` flag was added to fix). An
    accepted OCR-route document with full checkbox/address evidence must
    be accepted; the same route with the evidence stripped out (below)
    must instead need review, proving the outcome is driven by the real
    evidence Pipeline A produced, not merely by `route="ocr"`.
    """

    accepted_extractor = _FakeExtractor(_accepted_ocr_result)
    accepted = run_document(
        tmp_path / "input.png",
        output_dir=tmp_path / "output_accepted",
        extractor=accepted_extractor,
        review_repo_dir=tmp_path / "review",
    )
    assert accepted.status is DocumentRunStatus.ACCEPTED
    assert accepted.route == "ocr"

    signals_text = (tmp_path / "output_accepted" / accepted.document_id / "signals.json").read_text(
        encoding="utf-8"
    )
    assert '"checkbox_evidence_detection_method": "anchor_relative"' in signals_text
    assert '"employer_address_evidence_parse_complete": true' in signals_text

    missing_evidence_extractor = _FakeExtractor(_needs_review_ocr_result_missing_checkbox_evidence)
    missing_evidence = run_document(
        tmp_path / "input.png",
        output_dir=tmp_path / "output_missing_evidence",
        extractor=missing_evidence_extractor,
        review_repo_dir=tmp_path / "review",
    )
    assert missing_evidence.status is DocumentRunStatus.NEEDS_REVIEW
    assert missing_evidence.route == "ocr"
    assert "retirement_plan_checkbox_evidence_missing" in missing_evidence.issue_codes


def test_output_determinism_across_two_runs_without_rerunning_extraction(tmp_path: Path) -> None:
    first = run_document(
        tmp_path / "input.png",
        output_dir=tmp_path / "run1",
        extractor=_FakeExtractor(_accepted_ocr_result),
        review_repo_dir=tmp_path / "review",
    )
    second = run_document(
        tmp_path / "input.png",
        output_dir=tmp_path / "run2",
        extractor=_FakeExtractor(_accepted_ocr_result),
        review_repo_dir=tmp_path / "review",
    )

    first_json = (tmp_path / "run1" / first.document_id / "final.json").read_bytes()
    second_json = (tmp_path / "run2" / second.document_id / "final.json").read_bytes()
    first_csv = (tmp_path / "run1" / first.document_id / "final.csv").read_bytes()
    second_csv = (tmp_path / "run2" / second.document_id / "final.csv").read_bytes()

    assert first_json == second_json
    assert first_csv == second_csv


def test_unsupported_output_format_rejected() -> None:
    with pytest.raises(ValueError):
        run_document("whatever.png", output_format="xml")


def test_latency_fields_are_populated_and_consistent(tmp_path: Path) -> None:
    """Phase 8D.5: `total_duration_seconds` must never be smaller than the
    two components it is made of, and a pre-warmed extractor (the shared
    extractor a batch caller passes in) must report near-zero
    `model_startup_seconds` since `warm_up()` on an already-warm double is
    a cheap no-op, not a real cold start."""

    extractor = _FakeExtractor(_accepted_ocr_result)

    result = run_document(
        tmp_path / "input.png",
        output_dir=tmp_path / "output",
        extractor=extractor,
        review_repo_dir=tmp_path / "review",
    )

    assert extractor.warm_up_calls == 1
    assert result.model_startup_seconds >= 0.0
    assert result.processing_latency_seconds >= 0.0
    assert result.total_duration_seconds >= (
        result.model_startup_seconds + result.processing_latency_seconds
    )


def test_model_startup_failure_reports_failed_with_zero_processing_latency(tmp_path: Path) -> None:
    """A backend that cannot become ready (e.g. a missing OCR dependency)
    must fail before any per-document processing is attempted -- this is
    a runtime-unusable condition, not a per-document outcome, and must be
    distinguishable from a mid-processing failure via
    `processing_latency_seconds == 0.0`."""

    class _FailsToWarmUpExtractor:
        pipeline_id = "pipeline_a"
        ingestion_service = _FakeIngestionService()

        def warm_up(self) -> None:
            raise RuntimeError("simulated missing OCR dependency")

        def extract_ingested(self, ingested):  # noqa: ANN001 - test double
            raise AssertionError("must not be reached when warm_up() fails")

    result = run_document(
        tmp_path / "input.png",
        output_dir=tmp_path / "output",
        extractor=_FailsToWarmUpExtractor(),
        review_repo_dir=tmp_path / "review",
    )

    assert result.status is DocumentRunStatus.FAILED
    assert "simulated missing OCR dependency" in result.error_message
    assert result.processing_latency_seconds == 0.0
    assert result.total_duration_seconds >= result.model_startup_seconds
