"""Run Phase 6 validation against one canonical W2Document JSON artifact.

Usage:

    python -m w2_pipeline.validation.validate_w2 path/to/w2.json

Prints a `ValidationResult` as JSON. A source file that cannot be read or
that fails canonical `W2Document` validation is treated the same way a
failed extraction would be -- validated as a `None` document with an
`invalid_canonical_result` signal -- rather than raising, since judging an
already-broken artifact is exactly this command's job.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pydantic import ValidationError

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.validation.models import ExtractionOutcome, ExtractionSignals
from w2_pipeline.validation.validator import validate_w2_document


def main(argv: list[str] | None = None) -> None:
    """Validate one canonical W2Document JSON file and print the result."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    document, signals = _load_document(
        args.w2_document_path, pipeline_id=args.pipeline_id, route=args.route
    )
    result = validate_w2_document(document, signals=signals)
    print(result.model_dump_json(indent=2))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("w2_document_path", type=Path, help="Path to a W2Document JSON file.")
    parser.add_argument(
        "--pipeline-id",
        default=None,
        help="Optional extraction pipeline identifier to attach as a validation signal.",
    )
    parser.add_argument(
        "--route",
        default=None,
        help="Optional extraction route (e.g. ocr, native_pdf, vlm) to attach as a signal.",
    )
    return parser


def _load_document(
    path: Path,
    *,
    pipeline_id: str | None,
    route: str | None,
) -> tuple[W2Document | None, ExtractionSignals]:
    try:
        document = W2Document.model_validate_json(path.read_text(encoding="utf-8"))
        return document, ExtractionSignals(pipeline_id=pipeline_id, route=route)
    except (OSError, ValidationError, ValueError) as exc:
        signals = ExtractionSignals(
            pipeline_id=pipeline_id,
            route=route,
            outcome=ExtractionOutcome.INVALID_CANONICAL_RESULT,
            warnings=[f"Could not load {path.name} as a canonical W2Document: {exc}"],
        )
        return None, signals


if __name__ == "__main__":
    main()
