"""Phase 7 review/downstream-output demonstration CLI.

    python -m w2_pipeline.review.cli validate <w2.json>
    python -m w2_pipeline.review.cli review-create <w2.json> --repo-dir <dir>
    python -m w2_pipeline.review.cli review-correct <review_id> --repo-dir <dir> --field-path <path> --new-value <value>
    python -m w2_pipeline.review.cli review-revalidate <review_id> --repo-dir <dir>
    python -m w2_pipeline.review.cli export-document <w2.json> --format json|csv
    python -m w2_pipeline.review.cli export-review <review_id> --repo-dir <dir> --format json|csv

One orchestrating CLI covering the whole accepted-path and review-path
workflow (`docs/contracts/review-and-downstream-output.md`), matching this
project's existing single-purpose CLI convention
(`validate_w2.py`, `run_pipeline_a.py`, `run_pipeline_b.py`).

`--new-value` is parsed as JSON when possible (so `true`/`false`/numbers/
`null` behave as expected for boolean/numeric fields), falling back to the
raw string otherwise. Pass an explicitly quoted JSON string
(e.g. `--new-value '"1234.56"'`) to force an exact-precision money string
rather than a JSON number.

`--signals-json <path>` loads a full `ExtractionSignals` JSON document (as
produced by dumping `ExtractionSignals` for a real extraction) instead of
only the bare `--pipeline-id`/`--route` pair. This is required to
faithfully validate a real `pipeline_a` OCR-route extraction from this CLI,
since route-scoped validator rules (checkbox/address evidence) need
evidence fields that `--pipeline-id`/`--route` alone cannot carry.
`--pipeline-id`/`--route`, if also passed, override the corresponding
fields from `--signals-json`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.downstream.csv_output import export_csv
from w2_pipeline.downstream.finalize import finalize_document
from w2_pipeline.downstream.json_output import export_json
from w2_pipeline.downstream.models import FinalizedW2
from w2_pipeline.review.repository import FileReviewRepository
from w2_pipeline.review.workflow import apply_correction, revalidate, start_review
from w2_pipeline.validation.models import ExtractionOutcome, ExtractionSignals, ValidationStatus
from w2_pipeline.validation.validator import validate_w2_document

DEFAULT_REPO_DIR = "data/review"


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    args.handler(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate a W2Document JSON file.")
    validate_parser.add_argument("w2_document_path", type=Path)
    _add_signal_flags(validate_parser)
    validate_parser.set_defaults(handler=_handle_validate)

    create_parser = subparsers.add_parser(
        "review-create", help="Validate a document and create a review record if it needs review."
    )
    create_parser.add_argument("w2_document_path", type=Path)
    create_parser.add_argument("--repo-dir", default=DEFAULT_REPO_DIR, type=Path)
    _add_signal_flags(create_parser)
    create_parser.set_defaults(handler=_handle_review_create)

    correct_parser = subparsers.add_parser("review-correct", help="Apply one correction to a review record.")
    correct_parser.add_argument("review_id")
    correct_parser.add_argument("--repo-dir", default=DEFAULT_REPO_DIR, type=Path)
    correct_parser.add_argument("--field-path", required=True)
    correct_parser.add_argument("--new-value", required=True)
    correct_parser.add_argument("--reason", default=None)
    correct_parser.add_argument("--reviewer-id", default=None)
    correct_parser.set_defaults(handler=_handle_review_correct)

    revalidate_parser = subparsers.add_parser(
        "review-revalidate", help="Revalidate a review record's latest document snapshot."
    )
    revalidate_parser.add_argument("review_id")
    revalidate_parser.add_argument("--repo-dir", default=DEFAULT_REPO_DIR, type=Path)
    revalidate_parser.set_defaults(handler=_handle_review_revalidate)

    export_document_parser = subparsers.add_parser(
        "export-document", help="Validate then export a W2Document JSON file as downstream output."
    )
    export_document_parser.add_argument("w2_document_path", type=Path)
    export_document_parser.add_argument("--format", choices=("json", "csv"), default="json")
    export_document_parser.add_argument("--output", default=None, type=Path)
    _add_signal_flags(export_document_parser)
    export_document_parser.set_defaults(handler=_handle_export_document)

    export_review_parser = subparsers.add_parser(
        "export-review", help="Export a resolved review record's corrected document."
    )
    export_review_parser.add_argument("review_id")
    export_review_parser.add_argument("--repo-dir", default=DEFAULT_REPO_DIR, type=Path)
    export_review_parser.add_argument("--format", choices=("json", "csv"), default="json")
    export_review_parser.add_argument("--output", default=None, type=Path)
    export_review_parser.set_defaults(handler=_handle_export_review)

    return parser


def _add_signal_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pipeline-id", default=None)
    parser.add_argument("--route", default=None)
    parser.add_argument(
        "--signals-json",
        default=None,
        type=Path,
        help="Path to a full ExtractionSignals JSON document (see module docstring).",
    )


def _handle_validate(args: argparse.Namespace) -> None:
    document, signals = _load_document(args.w2_document_path, args.pipeline_id, args.route, args.signals_json)
    result = validate_w2_document(document, signals=signals)
    print(result.model_dump_json(indent=2))


def _handle_review_create(args: argparse.Namespace) -> None:
    document, signals = _load_document(args.w2_document_path, args.pipeline_id, args.route, args.signals_json)
    result = validate_w2_document(document, signals=signals)
    if result.status == ValidationStatus.ACCEPTED:
        print(json.dumps({"status": "accepted", "message": "No review needed."}, indent=2))
        return
    if document is None:
        print(result.model_dump_json(indent=2))
        raise SystemExit(
            f"{args.w2_document_path} did not parse as a canonical W2Document at all; "
            "there is no document to attach a review record to. See the validation "
            "issues above for why."
        )

    record = start_review(
        document,
        result,
        document_id=document.metadata.document_id,
        pipeline_metadata={"pipeline_id": args.pipeline_id, "route": args.route}
        if (args.pipeline_id or args.route)
        else None,
    )
    FileReviewRepository(args.repo_dir).save(record)
    print(record.model_dump_json(indent=2))


def _handle_review_correct(args: argparse.Namespace) -> None:
    repository = FileReviewRepository(args.repo_dir)
    record = repository.get(args.review_id)
    new_value = _parse_new_value(args.new_value)
    updated = apply_correction(
        record,
        field_path=args.field_path,
        new_value=new_value,
        reason=args.reason,
        reviewer_id=args.reviewer_id,
    )
    repository.save(updated)
    print(updated.model_dump_json(indent=2))


def _handle_review_revalidate(args: argparse.Namespace) -> None:
    repository = FileReviewRepository(args.repo_dir)
    record = repository.get(args.review_id)
    updated = revalidate(record)
    repository.save(updated)
    print(updated.model_dump_json(indent=2))


def _handle_export_document(args: argparse.Namespace) -> None:
    document, signals = _load_document(args.w2_document_path, args.pipeline_id, args.route, args.signals_json)
    result = validate_w2_document(document, signals=signals)
    finalized = finalize_document(document, result)
    _export(finalized, args.format, args.output)


def _handle_export_review(args: argparse.Namespace) -> None:
    record = FileReviewRepository(args.repo_dir).get(args.review_id)
    document = record.corrected_document or record.original_document
    result = record.revalidation_result or record.validation_result
    finalized = finalize_document(document, result)
    _export(finalized, args.format, args.output)


def _export(finalized: FinalizedW2, output_format: str, output_path: Path | None) -> None:
    text = export_csv(finalized, output_path) if output_format == "csv" else export_json(finalized, output_path)
    print(text)


def _parse_new_value(raw: str) -> object:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _load_document(
    path: Path,
    pipeline_id: str | None,
    route: str | None,
    signals_json_path: Path | None = None,
) -> tuple[W2Document | None, ExtractionSignals]:
    try:
        document = W2Document.model_validate_json(path.read_text(encoding="utf-8"))
        signals = _build_signals(pipeline_id, route, signals_json_path)
        return document, signals
    except (OSError, ValidationError, ValueError) as exc:
        signals = ExtractionSignals(
            pipeline_id=pipeline_id,
            route=route,
            outcome=ExtractionOutcome.INVALID_CANONICAL_RESULT,
            warnings=[f"Could not load {path.name} as a canonical W2Document: {exc}"],
        )
        return None, signals


def _build_signals(
    pipeline_id: str | None,
    route: str | None,
    signals_json_path: Path | None,
) -> ExtractionSignals:
    if signals_json_path is None:
        return ExtractionSignals(pipeline_id=pipeline_id, route=route)
    base = ExtractionSignals.model_validate_json(signals_json_path.read_text(encoding="utf-8"))
    overrides = {}
    if pipeline_id is not None:
        overrides["pipeline_id"] = pipeline_id
    if route is not None:
        overrides["route"] = route
    return base.model_copy(update=overrides) if overrides else base


if __name__ == "__main__":
    main()
