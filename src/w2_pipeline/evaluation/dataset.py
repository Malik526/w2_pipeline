"""Filesystem generation for synthetic evaluation datasets."""

from __future__ import annotations

from pathlib import Path

from w2_pipeline.evaluation.manifest import DatasetManifestEntry, DatasetSource, write_manifest_jsonl
from w2_pipeline.evaluation.rendering import RENDERER_VERSION, render_document_variants
from w2_pipeline.evaluation.synthetic import (
    DEFAULT_SYNTHETIC_SEED,
    SYNTHETIC_GENERATOR_VERSION,
    SyntheticGenerationConfig,
    generate_synthetic_w2_documents,
)


def generate_evaluation_dataset(
    output_dir: str | Path,
    *,
    sample_count: int = 12,
    seed: int = DEFAULT_SYNTHETIC_SEED,
) -> list[DatasetManifestEntry]:
    """Generate ground truth, documents, and a JSONL manifest."""

    root = Path(output_dir)
    ground_truth_dir = root / "ground_truth"
    documents_dir = root / "documents"
    ground_truth_dir.mkdir(parents=True, exist_ok=True)
    documents_dir.mkdir(parents=True, exist_ok=True)

    documents = generate_synthetic_w2_documents(
        SyntheticGenerationConfig(sample_count=sample_count, seed=seed)
    )
    entries: list[DatasetManifestEntry] = []

    for document in documents:
        sample_id = document.metadata.document_id
        ground_truth_path = ground_truth_dir / f"{sample_id}.json"
        ground_truth_path.write_text(document.model_dump_json(indent=2), encoding="utf-8")

        variants = render_document_variants(document, documents_dir)
        for variant in variants:
            entries.append(
                DatasetManifestEntry(
                    sample_id=sample_id,
                    tax_year=document.metadata.tax_year,
                    variant_id=variant.variant_id,
                    document_path=_relative_to_root(variant.document_path, root),
                    ground_truth_path=_relative_to_root(ground_truth_path, root),
                    variant_type=variant.variant_type,
                    expected_quality=variant.expected_quality,
                    source=DatasetSource.SYNTHETIC,
                    pii=False,
                    generator_seed=seed,
                    generator_version=SYNTHETIC_GENERATOR_VERSION,
                    renderer_version=RENDERER_VERSION,
                    transformation_config=variant.transformation_config,
                )
            )

    write_manifest_jsonl(root / "manifest.jsonl", entries)
    return entries


def _relative_to_root(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()
