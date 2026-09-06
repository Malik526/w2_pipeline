"""Phase 8A: complete per-document prediction capture for final benchmark runs.

Historical benchmark result artifacts (`data/evaluation/results/*.json`)
store aggregate metrics plus field-level failures, not the complete
predicted canonical document -- sufficient for accuracy reporting, but not
for a later analysis that needs to run an extractor's actual output
through something else (e.g. the Phase 6 validator, as
`validator_effectiveness.py` had to reconstruct from ground truth plus
recorded failures rather than a stored prediction).

`PredictionRecord` is deliberately distinct from
`w2_pipeline.evaluation.models.DocumentEvaluation`, which mixes expected
and predicted values together for scoring: a `PredictionRecord` contains
only what an extractor actually produced -- no ground truth anywhere in
it -- so a later analysis can feed it straight to a production consumer
(the Phase 6 validator) without any risk of ground-truth leakage, and
without needing to reconstruct anything.

See `docs/experiments/phase8a-final-benchmark-coverage.md`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.models import EvaluationModel


class PredictionRecord(EvaluationModel):
    """One extractor's complete, ground-truth-free prediction for one document variant."""

    document_id: str = Field(min_length=1)
    variant_id: str = Field(min_length=1)
    pipeline_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    document: W2Document | None = None
    extraction_route: str | None = None
    duration_seconds: float | None = Field(default=None, ge=0.0)
    message: str | None = None
    pipeline_metadata: dict[str, Any] | None = None


def write_prediction_records_jsonl(path: str | Path, records: list[PredictionRecord]) -> None:
    """Write one JSON object per line.

    JSONL, not one large JSON array: a final run can carry hundreds of
    full canonical documents, matching this project's existing
    `manifest.jsonl` convention for large per-document collections.
    """

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as file_obj:
        for record in records:
            file_obj.write(record.model_dump_json())
            file_obj.write("\n")


def load_prediction_records_jsonl(path: str | Path) -> list[PredictionRecord]:
    """Read prediction records written by `write_prediction_records_jsonl`."""

    records: list[PredictionRecord] = []
    with Path(path).open("r", encoding="utf-8") as file_obj:
        for line in file_obj:
            stripped = line.strip()
            if stripped:
                records.append(PredictionRecord.model_validate_json(stripped))
    return records
