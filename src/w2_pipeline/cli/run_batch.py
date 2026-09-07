"""Phase 8D.5: multi-document production runner CLI.

    PYTHONPATH=src python3 -m w2_pipeline.cli.run_batch w2_1.png w2_2.png
    PYTHONPATH=src python3 -m w2_pipeline.cli.run_batch --input-dir path/to/w2s/

A thin argparse wrapper around `w2_pipeline.application.run_batch`, this
project's canonical multi-document execution path: build one Pipeline A
extractor, warm it up once, then run every input file through the exact
same production workflow `w2_pipeline.cli.run_document` runs one file
through -- reusing that one warmed extractor instead of paying OCR
backend startup per file. No pipeline/validation/review/export/batch
aggregation logic is duplicated here; see
`w2_pipeline.application.run_batch.run_batch` for the orchestration
itself.

Exit-code contract (see `docs/batch-runner.md`):

    0 = every document processed without a runtime failure; accepted and
        needs_review are both valid per-document outcomes
    1 = at least one document hit a runtime/processing failure, or the
        shared OCR backend itself could not become ready

A document correctly routed to human review is this system working as
designed, not a batch failure -- exactly the same reasoning
`w2_pipeline.cli.run_document`'s exit-code contract already uses.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from w2_pipeline.application.run_batch import (
    DEFAULT_AGGREGATE_CSV_NAME,
    BatchRunResult,
    run_batch,
)
from w2_pipeline.application.run_document import (
    DEFAULT_DEVICE,
    DEFAULT_OCR_BACKEND,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_REVIEW_REPO_DIR,
    DocumentRunResult,
    DocumentRunStatus,
)
from w2_pipeline.extraction.factory import SUPPORTED_OCR_BACKENDS

EXIT_SUCCESS = 0
EXIT_FAILURE = 1

_INPUT_DIR_EXTENSIONS = (".png", ".jpg", ".jpeg", ".pdf")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        input_files = _resolve_input_files(args.input_file, args.input_dir)
    except ValueError as exc:
        parser.error(str(exc))
        return EXIT_FAILURE  # pragma: no cover - parser.error() exits

    print("W-2 batch processing")
    print()

    try:
        result = run_batch(
            input_files,
            output_dir=args.output_dir,
            ocr_backend=args.ocr_backend,
            device=args.device,
            review_repo_dir=args.review_repo_dir,
            aggregate_csv_name=args.aggregate_csv,
            on_ready=_on_ready(args.ocr_backend),
            on_document_start=_on_document_start,
            on_document_complete=_on_document_complete,
        )
    except Exception as exc:  # noqa: BLE001 - the shared OCR backend itself is unusable.
        print(f"Batch failed to start: {exc.__class__.__name__}: {exc}")
        return EXIT_FAILURE

    _print_summary(result)
    return EXIT_SUCCESS if result.failed == 0 else EXIT_FAILURE


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "input_file", type=Path, nargs="*", help="Paths to one or more W-2 PDF/PNG/JPEG files."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=None,
        help=(
            "Directory of W-2 files to process (non-recursive; "
            f"{', '.join(_INPUT_DIR_EXTENSIONS)} only). Combined with any "
            "positional INPUT_FILE arguments if both are given."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Base output directory; one subdirectory per document ID is created (default: {DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument("--ocr-backend", choices=SUPPORTED_OCR_BACKENDS, default=DEFAULT_OCR_BACKEND)
    parser.add_argument(
        "--device",
        choices=("gpu", "cpu"),
        default=DEFAULT_DEVICE,
        help="PaddleOCR execution device; ignored for --ocr-backend tesseract.",
    )
    parser.add_argument("--review-repo-dir", type=Path, default=DEFAULT_REVIEW_REPO_DIR)
    parser.add_argument(
        "--aggregate-csv",
        default=DEFAULT_AGGREGATE_CSV_NAME,
        help=(
            "Filename (relative to --output-dir) for the accepted-only aggregate "
            f"CSV (default: {DEFAULT_AGGREGATE_CSV_NAME})."
        ),
    )
    return parser


def _resolve_input_files(positional: list[Path], input_dir: Path | None) -> list[Path]:
    files = list(positional)
    if input_dir is not None:
        files.extend(
            sorted(
                path
                for path in input_dir.iterdir()
                if path.is_file() and path.suffix.lower() in _INPUT_DIR_EXTENSIONS
            )
        )
    if not files:
        raise ValueError("No input files given: pass one or more INPUT_FILE paths, or --input-dir.")
    return files


def _on_ready(ocr_backend: str):
    def _handler(model_startup_seconds: float) -> None:
        print(f"Initializing Pipeline A / {ocr_backend}...")
        print(f"Ready in {model_startup_seconds:.2f}s")
        print()

    return _handler


def _on_document_start(index: int, total: int, input_path: Path) -> None:
    print(f"[{index}/{total}] {input_path.name}")


def _on_document_complete(result: DocumentRunResult) -> None:
    if result.status is DocumentRunStatus.ACCEPTED:
        print(f"      ACCEPTED — {result.processing_latency_seconds:.2f}s")
    elif result.status is DocumentRunStatus.NEEDS_REVIEW:
        print(f"      NEEDS REVIEW — {result.processing_latency_seconds:.2f}s")
        for code in result.issue_codes:
            print(f"      {code}")
        print(f"      Review: {result.review_id}")
    else:
        print(f"      FAILED — {result.processing_latency_seconds:.2f}s")
        print(f"      {result.error_message}")
    print()


def _print_summary(result: BatchRunResult) -> None:
    print("Batch complete")
    print()
    print(f"Documents:        {result.documents_total}")
    print(f"Accepted:         {result.accepted}")
    print(f"Needs review:     {result.needs_review}")
    print(f"Failed:           {result.failed}")
    print()
    print(f"Model startup:    {result.model_startup_seconds:.2f}s")
    print(f"Mean doc latency: {result.mean_document_latency_seconds:.2f}s")
    print(f"Batch processing: {result.batch_processing_seconds:.2f}s")
    print(f"Total wall time:  {result.total_duration_seconds:.2f}s")
    if result.aggregate_csv is not None:
        print()
        print("CSV:")
        print(result.aggregate_csv)


if __name__ == "__main__":
    sys.exit(main())
