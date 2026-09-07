"""Phase 8D.4: single-document production runner CLI.

    PYTHONPATH=src python3 -m w2_pipeline.cli.run_document path/to/w2.png

A thin argparse wrapper around `w2_pipeline.application.run_document`,
this project's canonical single-document execution path: ingestion ->
Pipeline A (PaddleOCR by default) extraction -> canonical document +
extraction evidence -> evidence-preserving validation -> accepted
(finalize + export) or needs_review (persist a `ReviewRecord`). No
pipeline/validation/review/export logic is duplicated here -- every step
is the same production component the rest of this project already uses;
see `w2_pipeline.application.run_document` for the orchestration itself.

Exit-code contract (see `docs/single-document-runner.md`):

    0 = accepted, requested downstream output produced
    2 = processed successfully but needs human review (not a failure)
    1 = processing/runtime/configuration failure

`needs_review` is deliberately not a failure exit code: a document that
was correctly routed to a human is this system working as designed, not
breaking, and a future batch runner/skill must be able to tell the two
apart from the exit code alone.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from w2_pipeline.application.run_document import (
    DEFAULT_DEVICE,
    DEFAULT_OCR_BACKEND,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_REVIEW_REPO_DIR,
    DocumentRunResult,
    DocumentRunStatus,
    run_document,
)
from w2_pipeline.extraction.factory import SUPPORTED_OCR_BACKENDS

EXIT_ACCEPTED = 0
EXIT_NEEDS_REVIEW = 2
EXIT_FAILURE = 1


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    result = run_document(
        args.input_file,
        output_dir=args.output_dir,
        document_id=args.document_id,
        ocr_backend=args.ocr_backend,
        device=args.device,
        output_format=args.format,
        review_repo_dir=args.review_repo_dir,
    )
    _print_result(result)
    return _exit_code_for(result)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("input_file", type=Path, help="Path to one W-2 PDF/PNG/JPEG file.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Base output directory; one subdirectory per document ID is created (default: {DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument("--format", choices=("json", "csv", "both"), default="both")
    parser.add_argument(
        "--document-id",
        default=None,
        help="Defaults to the input file's stem (used as the output subdirectory name).",
    )
    parser.add_argument("--ocr-backend", choices=SUPPORTED_OCR_BACKENDS, default=DEFAULT_OCR_BACKEND)
    parser.add_argument(
        "--device",
        choices=("gpu", "cpu"),
        default=DEFAULT_DEVICE,
        help="PaddleOCR execution device; ignored for --ocr-backend tesseract.",
    )
    parser.add_argument("--review-repo-dir", type=Path, default=DEFAULT_REVIEW_REPO_DIR)
    return parser


def _print_result(result: DocumentRunResult) -> None:
    print("W-2 processing complete")
    print()
    print(f"Document: {result.document_id}")
    print(f"Pipeline: Pipeline A / {result.ocr_backend}")

    if result.status is DocumentRunStatus.FAILED:
        print("Validation: FAILED (runtime error)")
        print(f"Error: {result.error_message}")
        _print_timings(result)
        return

    validation_label = (result.validation_status or "").replace("_", " ").upper()
    print(f"Validation: {validation_label}")

    if result.status is DocumentRunStatus.ACCEPTED:
        print(f"Issues: {len(result.issue_codes)}")
        if "json" in result.outputs:
            print(f"JSON: {result.outputs['json']}")
        if "csv" in result.outputs:
            print(f"CSV: {result.outputs['csv']}")
    else:
        print()
        print("Issues:")
        for code in result.issue_codes:
            print(f"- {code}")
        print()
        print(f"Review ID: {result.review_id}")
        print("Finalization: BLOCKED")

    _print_timings(result)


def _print_timings(result: DocumentRunResult) -> None:
    print()
    print(f"Model startup:   {result.model_startup_seconds:.2f}s")
    print(f"Document latency: {result.processing_latency_seconds:.2f}s")
    print(f"Total wall time: {result.total_duration_seconds:.2f}s")


def _exit_code_for(result: DocumentRunResult) -> int:
    if result.status is DocumentRunStatus.ACCEPTED:
        return EXIT_ACCEPTED
    if result.status is DocumentRunStatus.NEEDS_REVIEW:
        return EXIT_NEEDS_REVIEW
    return EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main())
