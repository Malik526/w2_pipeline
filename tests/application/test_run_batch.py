"""Phase 8D.5: batch runner service tests.

Mirrors `tests/application/test_run_document.py`'s fake-extractor
convention: a minimal `PipelineAExtractor`-shaped double (only
`ingestion_service.ingest`, `warm_up`, `extract_ingested`) stands in for
the real OCR backend, so this suite needs neither GPU nor a real OCR
engine. Every other step -- `run_document()`'s own orchestration,
validation, finalize, export, review persistence, and this module's
aggregation/aggregate-CSV logic -- is the real production code.
"""

from __future__ import annotations

import csv
import io
from decimal import Decimal
from pathlib import Path

import pytest

from w2_pipeline.application.run_batch import run_batch
from w2_pipeline.application.run_document import DocumentRunStatus
from w2_pipeline.contracts.w2 import (
    Address,
    Box13Flags,
    Employee,
    Employer,
    FederalWagesAndTaxes,
    W2Document,
    W2Metadata,
)
from w2_pipeline.extraction.models import (
    AcquisitionRoute,
    AddressExtractionEvidence,
    Box13CheckboxEvidence,
    ExtractionResult,
)
from w2_pipeline.review.repository import FileReviewRepository

_FULL_CHECKBOX_EVIDENCE = Box13CheckboxEvidence(
    detection_method="anchor_relative", fallback_used=False, anchor_found=True, checkbox_found=True, decision_margin=5.0
)
_COMPLETE_ADDRESS_EVIDENCE = AddressExtractionEvidence(
    region_observation_count=5, usable_row_count=3, parse_complete=True
)


def _document(document_id: str) -> W2Document:
    address = Address(address_line_1="1 Main St", city="Springfield", state="IL", postal_code="62704")
    return W2Document(
        metadata=W2Metadata(
            document_type="W-2", tax_year=2026, schema_version=2026, document_id=document_id, source_file_type="png"
        ),
        employee=Employee(ssn="242-48-4959", first_name="Steven", last_name="Armstrong", address=address),
        employer=Employer(ein="75-5696876", name="Timberline Trading Co.", address=address),
        federal_wages_and_taxes=FederalWagesAndTaxes(
            box_1_wages_tips_other_compensation=Decimal("100.00"),
            box_2_federal_income_tax_withheld=Decimal("10.00"),
            box_5_medicare_wages_and_tips=Decimal("100.00"),
            box_6_medicare_tax_withheld=Decimal("1.00"),
        ),
        box_13=Box13Flags(retirement_plan=False),
    )


def _accepted_result(document_id: str) -> ExtractionResult:
    return ExtractionResult(
        document=_document(document_id),
        route=AcquisitionRoute.OCR,
        observation_count=42,
        box_13_checkbox_evidence=_FULL_CHECKBOX_EVIDENCE,
        employer_address_evidence=_COMPLETE_ADDRESS_EVIDENCE,
        employee_address_evidence=_COMPLETE_ADDRESS_EVIDENCE,
    )


def _needs_review_result(document_id: str) -> ExtractionResult:
    return ExtractionResult(
        document=_document(document_id), route=AcquisitionRoute.OCR, observation_count=42, box_13_checkbox_evidence=None
    )


class _FakeIngestionService:
    def ingest(self, path: str | Path, document_id: str | None = None):  # noqa: ANN001 - test double
        return object()


class _FakeBatchExtractor:
    """`PipelineAExtractor`-shaped double that serves one canned outcome per
    call, keyed by input path stem, and tracks warm-up calls separately
    from one-time "heavy" construction -- mirroring the real
    `PaddleOcrAdapter._get_client()` cache so a test can assert the
    shared extractor is warmed once, not reconstructed per document."""

    pipeline_id = "pipeline_a"

    def __init__(self, outcomes: dict[str, object]) -> None:
        self.ingestion_service = _FakeIngestionService()
        self._outcomes = outcomes
        self.warm_up_calls = 0
        self.built_count = 0
        self.extract_calls = 0

    def warm_up(self) -> None:
        self.warm_up_calls += 1
        if self.built_count == 0:
            self.built_count = 1

    def extract_ingested(self, ingested):  # noqa: ANN001 - test double
        raise AssertionError("extract_ingested must be called via extract_ingested(input_path) in these tests")


class _FakeBatchExtractorByPath(_FakeBatchExtractor):
    """Resolves the canned outcome from the input path threaded in by
    `run_document()`'s own `ingestion_service.ingest(input_path, ...)`
    call -- `extract_ingested` receives whatever `ingest()` returns, so
    the fake ingestion service returns the input path itself."""

    def __init__(self, outcomes: dict[str, object]) -> None:
        super().__init__(outcomes)
        self.ingestion_service = self._IngestionService()

    class _IngestionService:
        def ingest(self, path: str | Path, document_id: str | None = None):  # noqa: ANN001
            return Path(path)

    def extract_ingested(self, ingested_path: Path):
        self.extract_calls += 1
        outcome = self._outcomes[ingested_path.stem]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome()


def _write_inputs(tmp_path: Path, names: list[str]) -> list[Path]:
    paths = []
    for name in names:
        path = tmp_path / name
        path.write_bytes(b"fake-image-bytes")
        paths.append(path)
    return paths


def test_shared_extractor_is_reused_and_warmed_exactly_once(tmp_path: Path) -> None:
    inputs = _write_inputs(tmp_path, ["doc_a.png", "doc_b.png", "doc_c.png"])
    extractor = _FakeBatchExtractorByPath(
        {"doc_a": lambda: _accepted_result("doc_a"), "doc_b": lambda: _accepted_result("doc_b"), "doc_c": lambda: _accepted_result("doc_c")}
    )

    result = run_batch(
        inputs, output_dir=tmp_path / "output", extractor=extractor, review_repo_dir=tmp_path / "review"
    )

    assert result.documents_total == 3
    assert result.accepted == 3
    # Warmed once by run_batch itself, then once per run_document() call
    # (cheap/idempotent, mirroring PaddleOcrAdapter's cached client) --
    # never a "heavy" rebuild after the first.
    assert extractor.warm_up_calls == 4
    assert extractor.built_count == 1
    assert extractor.extract_calls == 3


def test_shared_extractor_is_not_reconstructed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = _write_inputs(tmp_path, ["doc_a.png"])
    extractor = _FakeBatchExtractorByPath({"doc_a": lambda: _accepted_result("doc_a")})

    def _fail_if_called(**kwargs):  # noqa: ANN001 - test double
        raise AssertionError("build_pipeline_a_extractor must not be called when extractor= is given")

    monkeypatch.setattr("w2_pipeline.application.run_batch.build_pipeline_a_extractor", _fail_if_called)

    result = run_batch(inputs, output_dir=tmp_path / "output", extractor=extractor, review_repo_dir=tmp_path / "review")

    assert result.accepted == 1


def test_mixed_accepted_and_needs_review_batch_aggregate_csv_is_accepted_only(tmp_path: Path) -> None:
    inputs = _write_inputs(tmp_path, ["doc_a.png", "doc_b.png", "doc_c.png"])
    extractor = _FakeBatchExtractorByPath(
        {
            "doc_a": lambda: _accepted_result("doc_a"),
            "doc_b": lambda: _needs_review_result("doc_b"),
            "doc_c": lambda: _accepted_result("doc_c"),
        }
    )

    result = run_batch(
        inputs, output_dir=tmp_path / "output", extractor=extractor, review_repo_dir=tmp_path / "review"
    )

    assert result.documents_total == 3
    assert result.accepted == 2
    assert result.needs_review == 1
    assert result.failed == 0
    assert result.aggregate_csv is not None

    csv_text = Path(result.aggregate_csv).read_text(encoding="utf-8")
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    assert len(rows) == 2
    document_ids = {row["metadata.document_id"] for row in rows}
    assert document_ids == {"doc_a", "doc_c"}
    assert "doc_b" not in csv_text

    needs_review_doc = next(doc for doc in result.documents if doc.document_id == "doc_b")
    assert needs_review_doc.review_id is not None
    persisted = FileReviewRepository(tmp_path / "review").get(needs_review_doc.review_id)
    assert persisted.document_id == "doc_b"


def test_aggregate_csv_rows_match_individual_final_csv_and_are_deterministic(tmp_path: Path) -> None:
    inputs = _write_inputs(tmp_path, ["doc_a.png", "doc_c.png"])
    outcomes = {"doc_a": lambda: _accepted_result("doc_a"), "doc_c": lambda: _accepted_result("doc_c")}

    first = run_batch(
        inputs,
        output_dir=tmp_path / "output",
        extractor=_FakeBatchExtractorByPath(outcomes),
        review_repo_dir=tmp_path / "review",
    )
    second = run_batch(
        inputs,
        output_dir=tmp_path / "output2",
        extractor=_FakeBatchExtractorByPath(outcomes),
        review_repo_dir=tmp_path / "review2",
    )

    first_csv = Path(first.aggregate_csv).read_bytes()
    second_csv = Path(second.aggregate_csv).read_bytes()
    assert first_csv == second_csv

    individual_final_csv = (tmp_path / "output" / "doc_a" / "final.csv").read_bytes()
    aggregate_rows = list(csv.DictReader(io.StringIO(first_csv.decode("utf-8"))))
    individual_rows = list(csv.DictReader(io.StringIO(individual_final_csv.decode("utf-8"))))
    doc_a_row = next(row for row in aggregate_rows if row["metadata.document_id"] == "doc_a")
    assert doc_a_row == individual_rows[0]


def test_zero_accepted_batch_has_no_aggregate_csv(tmp_path: Path) -> None:
    inputs = _write_inputs(tmp_path, ["doc_a.png"])
    extractor = _FakeBatchExtractorByPath({"doc_a": lambda: _needs_review_result("doc_a")})

    result = run_batch(inputs, output_dir=tmp_path / "output", extractor=extractor, review_repo_dir=tmp_path / "review")

    assert result.accepted == 0
    assert result.aggregate_csv is None
    assert not (tmp_path / "output" / "batch_finalized.csv").exists()


def test_failure_isolation_one_bad_document_does_not_stop_the_batch(tmp_path: Path) -> None:
    inputs = _write_inputs(tmp_path, ["doc_a.png", "doc_bad.png", "doc_c.png"])
    extractor = _FakeBatchExtractorByPath(
        {
            "doc_a": lambda: _accepted_result("doc_a"),
            "doc_bad": RuntimeError("simulated OCR crash"),
            "doc_c": lambda: _accepted_result("doc_c"),
        }
    )

    result = run_batch(inputs, output_dir=tmp_path / "output", extractor=extractor, review_repo_dir=tmp_path / "review")

    assert result.documents_total == 3
    assert result.accepted == 2
    assert result.failed == 1
    statuses = {doc.document_id: doc.status for doc in result.documents}
    assert statuses["doc_a"] is DocumentRunStatus.ACCEPTED
    assert statuses["doc_bad"] is DocumentRunStatus.FAILED
    assert statuses["doc_c"] is DocumentRunStatus.ACCEPTED
    assert result.aggregate_csv is not None
    csv_text = Path(result.aggregate_csv).read_text(encoding="utf-8")
    assert "doc_bad" not in csv_text
    assert not (tmp_path / "output" / "doc_bad" / "final.json").exists()


def test_shared_extractor_warmup_failure_propagates(tmp_path: Path) -> None:
    class _FailsToWarmUp(_FakeBatchExtractorByPath):
        def warm_up(self) -> None:
            raise RuntimeError("simulated missing OCR dependency")

    inputs = _write_inputs(tmp_path, ["doc_a.png"])
    extractor = _FailsToWarmUp({"doc_a": lambda: _accepted_result("doc_a")})

    with pytest.raises(RuntimeError, match="simulated missing OCR dependency"):
        run_batch(inputs, output_dir=tmp_path / "output", extractor=extractor, review_repo_dir=tmp_path / "review")


def test_batch_summary_json_matches_return_value(tmp_path: Path) -> None:
    inputs = _write_inputs(tmp_path, ["doc_a.png"])
    extractor = _FakeBatchExtractorByPath({"doc_a": lambda: _accepted_result("doc_a")})

    result = run_batch(inputs, output_dir=tmp_path / "output", extractor=extractor, review_repo_dir=tmp_path / "review")

    summary_path = tmp_path / "output" / "batch_summary.json"
    assert summary_path.exists()
    assert summary_path.read_text(encoding="utf-8") == result.model_dump_json(indent=2)


def test_progress_hooks_are_called_in_order(tmp_path: Path) -> None:
    inputs = _write_inputs(tmp_path, ["doc_a.png", "doc_b.png"])
    extractor = _FakeBatchExtractorByPath(
        {"doc_a": lambda: _accepted_result("doc_a"), "doc_b": lambda: _accepted_result("doc_b")}
    )
    events: list[str] = []

    run_batch(
        inputs,
        output_dir=tmp_path / "output",
        extractor=extractor,
        review_repo_dir=tmp_path / "review",
        on_ready=lambda seconds: events.append("ready"),
        on_document_start=lambda index, total, path: events.append(f"start:{path.stem}"),
        on_document_complete=lambda result: events.append(f"complete:{result.document_id}"),
    )

    assert events == ["ready", "start:doc_a", "complete:doc_a", "start:doc_b", "complete:doc_b"]


def test_mean_and_median_document_latency_are_computed(tmp_path: Path) -> None:
    inputs = _write_inputs(tmp_path, ["doc_a.png", "doc_b.png"])
    extractor = _FakeBatchExtractorByPath(
        {"doc_a": lambda: _accepted_result("doc_a"), "doc_b": lambda: _accepted_result("doc_b")}
    )

    result = run_batch(inputs, output_dir=tmp_path / "output", extractor=extractor, review_repo_dir=tmp_path / "review")

    latencies = [doc.processing_latency_seconds for doc in result.documents]
    assert result.mean_document_latency_seconds == pytest.approx(sum(latencies) / len(latencies))
    assert result.mean_document_latency_seconds >= 0.0
    assert result.median_document_latency_seconds >= 0.0
