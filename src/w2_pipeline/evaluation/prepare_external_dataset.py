"""Developer CLI for preparing the external Symage Hugging Face W-2 benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path

from w2_pipeline.evaluation.external_symage import (
    HF_DATASET_NAME,
    SYMAGE_W2_FORM_ID,
    SymageW2Adapter,
)
from w2_pipeline.evaluation.manifest import write_manifest_jsonl

DEFAULT_OUTPUT_DIR = Path("data/evaluation/external/symage-synthetic-us-forms-preview")
HF_PARQUET_SPLITS = {
    "train": "data/train-00000-of-00001.parquet",
    "test": "data/test-00000-of-00001.parquet",
}


def main() -> None:
    """Load the Hugging Face dataset and prepare the 2026 W-2 subset locally."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"External benchmark output directory. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of W-2 records to prepare.",
    )
    parser.add_argument(
        "--no-variants",
        action="store_true",
        help="Prepare only original clean renders without derived degradation variants.",
    )
    parser.add_argument(
        "--loader",
        choices=("auto", "datasets", "pandas"),
        default="auto",
        help="Remote dataset loader to use. Default: auto",
    )
    args = parser.parse_args()

    adapter = SymageW2Adapter()
    entries = []
    prepared_records = 0
    for split, record in _iter_records(loader=args.loader):
        if not adapter.is_target_record(record):
            continue
        prepared = adapter.prepare_record(
            record,
            args.output_dir,
            split=split,
            include_variants=not args.no_variants,
        )
        entries.extend(prepared.manifest_entries)
        prepared_records += 1
        if args.limit is not None and prepared_records >= args.limit:
            break

    write_manifest_jsonl(args.output_dir / "manifest.jsonl", entries)
    print(
        f"Prepared {prepared_records} {SYMAGE_W2_FORM_ID} records "
        f"and {len(entries)} document variants from {HF_DATASET_NAME}."
    )
    print(f"Manifest: {args.output_dir / 'manifest.jsonl'}")


def _iter_records(*, loader: str):
    if loader in {"auto", "datasets"}:
        try:
            yield from _iter_records_with_datasets()
            return
        except ImportError:
            if loader == "datasets":
                raise SystemExit(
                    "Install the optional Hugging Face dependency first: "
                    "python3 -m pip install '.[external]'"
                )

    try:
        yield from _iter_records_with_pandas()
    except ImportError as exc:
        raise SystemExit(
            "Install the optional external dataset dependencies first: "
            "python3 -m pip install '.[external]'"
        ) from exc


def _iter_records_with_datasets():
    from datasets import load_dataset

    dataset = load_dataset(HF_DATASET_NAME)
    for split, rows in dataset.items():
        for record in rows:
            yield split, record


def _iter_records_with_pandas():
    import pandas as pd

    for split, relative_path in HF_PARQUET_SPLITS.items():
        dataframe = pd.read_parquet(f"hf://datasets/{HF_DATASET_NAME}/{relative_path}")
        for record in dataframe.to_dict(orient="records"):
            yield split, record


if __name__ == "__main__":
    main()
