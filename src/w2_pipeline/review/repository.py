"""Review record persistence, behind a small interface.

`ReviewRepository` is a `Protocol` so a future production replacement
(Postgres, S3, ...) can implement the same three methods without any
review-workflow business logic (`workflow.py`) needing to change.
`FileReviewRepository` is the one filesystem-backed implementation this
phase ships, sufficient to demonstrate the full workflow end to end.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from w2_pipeline.review.errors import ReviewRecordNotFoundError
from w2_pipeline.review.models import ReviewRecord


@runtime_checkable
class ReviewRepository(Protocol):
    """Structural contract every review record store must satisfy."""

    def save(self, record: ReviewRecord) -> None:
        """Persist `record`, replacing any existing record with the same ID."""

    def get(self, review_id: str) -> ReviewRecord:
        """Return the record for `review_id`, or raise `ReviewRecordNotFoundError`."""

    def list(self) -> list[ReviewRecord]:
        """Return every persisted record, in no particular order."""


class FileReviewRepository:
    """One JSON file per review record, named only by review ID.

    Filenames never carry a document ID, name, SSN, or EIN -- only the
    review record's own opaque ID -- per this project's PII-in-filenames
    policy. Review records may carry real PII in production use
    (`data/review/README.md`); this repository does not redact anything on
    write, since the whole point of a review record is to preserve the
    document a human is correcting.
    """

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, record: ReviewRecord) -> None:
        self._path(record.review_id).write_text(record.model_dump_json(indent=2), encoding="utf-8")

    def get(self, review_id: str) -> ReviewRecord:
        path = self._path(review_id)
        if not path.exists():
            raise ReviewRecordNotFoundError(f"No review record found for ID {review_id!r}.")
        return ReviewRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def list(self) -> list[ReviewRecord]:
        return [
            ReviewRecord.model_validate_json(path.read_text(encoding="utf-8"))
            for path in sorted(self.base_dir.glob("*.json"))
        ]

    def _path(self, review_id: str) -> Path:
        return self.base_dir / f"{review_id}.json"
