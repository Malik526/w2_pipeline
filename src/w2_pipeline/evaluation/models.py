"""Typed evaluation result contracts independent of extraction strategy."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvaluationModel(BaseModel):
    """Base model for strict evaluation contracts."""

    model_config = ConfigDict(extra="forbid")


class EvaluationFailureKind(str, Enum):
    """Explicit classifications for field and document evaluation failures."""

    MISSING = "missing"
    MISMATCH = "mismatch"
    UNEXPECTED = "unexpected"
    EXTRACTION_FAILED = "extraction_failed"
    INVALID_CANONICAL_RESULT = "invalid_canonical_result"


class DocumentEvaluationStatus(str, Enum):
    """Terminal status for one evaluated document variant."""

    SUCCESS = "success"
    EXTRACTION_FAILED = "extraction_failed"
    INVALID_CANONICAL_RESULT = "invalid_canonical_result"


class FieldEvaluation(EvaluationModel):
    """Comparison result for one flattened canonical W-2 field path."""

    field_path: str = Field(min_length=1)
    expected: Any = None
    predicted: Any = None
    correct: bool
    failure_kind: EvaluationFailureKind | None = None


class EvaluationIssue(EvaluationModel):
    """Machine-readable issue raised while evaluating a document or field."""

    kind: EvaluationFailureKind
    field_path: str | None = None
    expected: Any = None
    predicted: Any = None
    message: str | None = None


class DocumentEvaluation(EvaluationModel):
    """Field-accuracy result for one manifest document variant."""

    sample_id: str = Field(min_length=1)
    variant_id: str = Field(min_length=1)
    tax_year: int
    pipeline_id: str | None = None
    status: DocumentEvaluationStatus = DocumentEvaluationStatus.SUCCESS
    total_fields: int = Field(ge=0)
    correct_fields: int = Field(ge=0)
    field_accuracy: float = Field(ge=0.0, le=1.0)
    field_evaluations: list[FieldEvaluation] = Field(default_factory=list)
    failures: list[EvaluationIssue] = Field(default_factory=list)
    started_at: datetime | None = None
    duration_seconds: float | None = Field(default=None, ge=0.0)
    extraction_route: str | None = None


class BenchmarkEvaluation(EvaluationModel):
    """Aggregate-friendly wrapper for many document evaluations."""

    pipeline_id: str | None = None
    document_evaluations: list[DocumentEvaluation] = Field(default_factory=list)

    @property
    def total_documents(self) -> int:
        """Return the number of document variants evaluated."""

        return len(self.document_evaluations)

    @property
    def successful_documents(self) -> int:
        """Return the number of variants with a valid canonical prediction."""

        return sum(
            evaluation.status == DocumentEvaluationStatus.SUCCESS
            for evaluation in self.document_evaluations
        )

    @property
    def failed_documents(self) -> int:
        """Return the number of variants that did not produce a valid prediction."""

        return self.total_documents - self.successful_documents

    @property
    def failure_rate(self) -> float:
        """Return document-level failure rate."""

        if self.total_documents == 0:
            return 0.0
        return self.failed_documents / self.total_documents

    @property
    def field_accuracy(self) -> float:
        """Return aggregate field accuracy across all evaluated variants."""

        total_fields = sum(evaluation.total_fields for evaluation in self.document_evaluations)
        if total_fields == 0:
            return 0.0
        correct_fields = sum(
            evaluation.correct_fields for evaluation in self.document_evaluations
        )
        return correct_fields / total_fields
