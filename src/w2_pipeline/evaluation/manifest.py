"""Dataset manifest contracts and JSONL persistence helpers."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ManifestModel(BaseModel):
    """Base model for strict evaluation manifest contracts."""

    model_config = ConfigDict(extra="forbid")


class DatasetSource(str, Enum):
    """Supported provenance labels for evaluation dataset items."""

    SYNTHETIC = "synthetic"
    PUBLIC_DATASET = "public_dataset"


class VariantType(str, Enum):
    """Document variants generated for the initial Phase 3 benchmark."""

    CLEAN_PDF = "clean_pdf"
    CLEAN_PNG = "clean_png"
    ROTATED_PNG = "rotated_png"
    COMPRESSED_JPEG = "compressed_jpeg"
    BLURRED_PNG = "blurred_png"


class ExpectedQuality(str, Enum):
    """Human-readable quality tier for a rendered evaluation document."""

    CLEAN = "clean"
    ROTATED = "rotated"
    COMPRESSED = "compressed"
    DEGRADED = "degraded"


class DatasetManifestEntry(ManifestModel):
    """One document variant linked to one canonical ground-truth sample."""

    sample_id: str = Field(min_length=1)
    tax_year: int
    variant_id: str = Field(min_length=1)
    document_path: str = Field(min_length=1)
    ground_truth_path: str = Field(min_length=1)
    variant_type: VariantType
    expected_quality: ExpectedQuality
    source: DatasetSource = DatasetSource.SYNTHETIC
    pii: bool = False
    generator_seed: int | None = None
    generator_version: str | None = None
    renderer_version: str | None = None
    transformation_config: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_safe_synthetic_entry(self) -> "DatasetManifestEntry":
        if self.source == DatasetSource.SYNTHETIC and self.pii:
            raise ValueError("Synthetic evaluation entries must not contain PII.")
        return self


class DatasetManifest(ManifestModel):
    """Collection wrapper for manifest entries."""

    entries: list[DatasetManifestEntry] = Field(default_factory=list)


def load_manifest_jsonl(
    manifest_path: str | Path,
    *,
    validate_paths: bool = True,
) -> DatasetManifest:
    """Load manifest entries from JSON Lines and optionally check references."""

    path = Path(manifest_path)
    entries: list[DatasetManifestEntry] = []
    with path.open("r", encoding="utf-8") as file_obj:
        for line_number, line in enumerate(file_obj, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid manifest JSON on line {line_number}.") from exc
            entry = DatasetManifestEntry.model_validate(payload)
            if validate_paths:
                _ensure_manifest_reference(path.parent, entry.document_path, "document_path")
                _ensure_manifest_reference(
                    path.parent,
                    entry.ground_truth_path,
                    "ground_truth_path",
                )
            entries.append(entry)
    return DatasetManifest(entries=entries)


def write_manifest_jsonl(
    manifest_path: str | Path,
    entries: list[DatasetManifestEntry],
) -> None:
    """Write manifest entries as stable JSON Lines."""

    path = Path(manifest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file_obj:
        for entry in entries:
            file_obj.write(entry.model_dump_json(exclude_none=True))
            file_obj.write("\n")


def _ensure_manifest_reference(
    base_dir: Path,
    relative_or_absolute_path: str,
    field_name: str,
) -> None:
    referenced_path = Path(relative_or_absolute_path)
    if not referenced_path.is_absolute():
        referenced_path = base_dir / referenced_path
    if not referenced_path.exists():
        raise FileNotFoundError(
            f"Manifest {field_name} does not exist: {relative_or_absolute_path}"
        )
