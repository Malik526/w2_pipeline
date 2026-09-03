"""Pipeline-independent benchmark runner utilities."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.comparison import compare_w2_documents, flatten_w2_document
from w2_pipeline.evaluation.inputs import ExtractionInput
from w2_pipeline.evaluation.manifest import DatasetManifestEntry
from w2_pipeline.evaluation.models import (
    BenchmarkEvaluation,
    DocumentEvaluation,
    DocumentEvaluationStatus,
    EvaluationFailureKind,
    EvaluationIssue,
)


class W2Extractor(Protocol):
    """Minimal boundary future extractors must satisfy for evaluation."""

    def extract(self, extraction_input: ExtractionInput) -> W2Document | dict:
        """Return a canonical W-2 prediction for the provided source document."""


def evaluate_manifest(
    *,
    entries: list[DatasetManifestEntry],
    manifest_base_dir: str | Path,
    extractor: W2Extractor,
    pipeline_id: str,
) -> BenchmarkEvaluation:
    """Evaluate an extractor against manifest entries without aborting on failures."""

    base_dir = Path(manifest_base_dir)
    evaluations = [
        _evaluate_entry(
            entry=entry,
            base_dir=base_dir,
            extractor=extractor,
            pipeline_id=pipeline_id,
        )
        for entry in entries
    ]
    return BenchmarkEvaluation(pipeline_id=pipeline_id, document_evaluations=evaluations)


def _evaluate_entry(
    *,
    entry: DatasetManifestEntry,
    base_dir: Path,
    extractor: W2Extractor,
    pipeline_id: str,
) -> DocumentEvaluation:
    expected = _load_ground_truth(base_dir / entry.ground_truth_path)
    extraction_input = ExtractionInput(
        document_path=base_dir / entry.document_path,
        document_id=f"{entry.sample_id}:{entry.variant_id}",
        tax_year_hint=entry.tax_year,
        source=entry.source,
    )
    started_at = datetime.now(timezone.utc)
    start = time.perf_counter()

    try:
        raw_prediction = extractor.extract(extraction_input)
    except Exception as exc:  # noqa: BLE001 - runner isolates pipeline failures.
        duration = time.perf_counter() - start
        return _failed_evaluation(
            entry=entry,
            expected=expected,
            pipeline_id=pipeline_id,
            status=DocumentEvaluationStatus.EXTRACTION_FAILED,
            kind=EvaluationFailureKind.EXTRACTION_FAILED,
            started_at=started_at,
            duration_seconds=duration,
            message=f"Extractor raised {exc.__class__.__name__}.",
        )

    try:
        predicted = (
            raw_prediction
            if isinstance(raw_prediction, W2Document)
            else W2Document.model_validate(raw_prediction)
        )
    except ValidationError as exc:
        duration = time.perf_counter() - start
        return _failed_evaluation(
            entry=entry,
            expected=expected,
            pipeline_id=pipeline_id,
            status=DocumentEvaluationStatus.INVALID_CANONICAL_RESULT,
            kind=EvaluationFailureKind.INVALID_CANONICAL_RESULT,
            started_at=started_at,
            duration_seconds=duration,
            message=f"Prediction failed canonical validation: {exc.__class__.__name__}.",
        )

    duration = time.perf_counter() - start
    evaluation = compare_w2_documents(
        expected=expected,
        predicted=predicted,
        sample_id=entry.sample_id,
        variant_id=entry.variant_id,
        pipeline_id=pipeline_id,
        evaluated_field_paths=entry.evaluated_field_paths,
    )
    return evaluation.model_copy(
        update={"started_at": started_at, "duration_seconds": duration}
    )


def _load_ground_truth(path: Path) -> W2Document:
    return W2Document.model_validate_json(path.read_text(encoding="utf-8"))


def _failed_evaluation(
    *,
    entry: DatasetManifestEntry,
    expected: W2Document,
    pipeline_id: str,
    status: DocumentEvaluationStatus,
    kind: EvaluationFailureKind,
    started_at: datetime,
    duration_seconds: float,
    message: str,
) -> DocumentEvaluation:
    total_fields = len(flatten_w2_document(expected))
    return DocumentEvaluation(
        sample_id=entry.sample_id,
        variant_id=entry.variant_id,
        tax_year=entry.tax_year,
        pipeline_id=pipeline_id,
        status=status,
        total_fields=total_fields,
        correct_fields=0,
        field_accuracy=0.0,
        failures=[EvaluationIssue(kind=kind, message=message)],
        started_at=started_at,
        duration_seconds=duration_seconds,
    )
