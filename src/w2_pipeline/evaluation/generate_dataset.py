"""Developer CLI for regenerating the synthetic Phase 3 evaluation dataset."""

from __future__ import annotations

import argparse
from pathlib import Path

from w2_pipeline.evaluation.dataset import generate_evaluation_dataset
from w2_pipeline.evaluation.synthetic import DEFAULT_SYNTHETIC_SEED

DEFAULT_OUTPUT_DIR = Path("data/evaluation/generated")


def main() -> None:
    """Generate deterministic synthetic evaluation assets."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Dataset output directory. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--sample-count",
        type=int,
        default=12,
        help="Number of semantic W-2 samples to generate. Default: 12",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SYNTHETIC_SEED,
        help=f"Deterministic generator seed. Default: {DEFAULT_SYNTHETIC_SEED}",
    )
    args = parser.parse_args()

    entries = generate_evaluation_dataset(
        args.output_dir,
        sample_count=args.sample_count,
        seed=args.seed,
    )
    print(f"Wrote {len(entries)} evaluation document variants to {args.output_dir}")
    print(f"Manifest: {args.output_dir / 'manifest.jsonl'}")


if __name__ == "__main__":
    main()
