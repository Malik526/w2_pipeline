"""Benchmark result serialization and Markdown report generation."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
import json
from pathlib import Path
from typing import Any

from w2_pipeline.evaluation.manifest import DatasetManifestEntry
from w2_pipeline.evaluation.models import (
    DocumentEvaluation,
    DocumentEvaluationStatus,
    FieldEvaluation,
    FieldFailure,
)

DEFAULT_FAILURE_ROW_LIMIT = 100

_FIELD_LABELS = {
    "metadata.document_type": "Document type",
    "metadata.tax_year": "Tax year",
    "metadata.schema_version": "Schema version",
    "employee.first_name": "Employee first name",
    "employee.middle_initial": "Employee middle initial",
    "employee.last_name": "Employee last name",
    "employee.suffix": "Employee suffix",
    "employee.ssn": "Employee SSN",
    "employer.ein": "Employer EIN",
    "employer.name": "Employer name",
    "employer.control_number": "Employer control number",
    "box_13.statutory_employee": "Box 13 statutory employee",
    "box_13.retirement_plan": "Box 13 retirement plan",
    "box_13.third_party_sick_pay": "Box 13 third-party sick pay",
    "federal_wages_and_taxes.box_1_wages_tips_other_compensation": "Box 1 wages, tips, other compensation",
    "federal_wages_and_taxes.box_2_federal_income_tax_withheld": "Box 2 federal income tax withheld",
    "federal_wages_and_taxes.box_3_social_security_wages": "Box 3 Social Security wages",
    "federal_wages_and_taxes.box_4_social_security_tax_withheld": "Box 4 Social Security tax withheld",
    "federal_wages_and_taxes.box_5_medicare_wages_and_tips": "Box 5 Medicare wages and tips",
    "federal_wages_and_taxes.box_6_medicare_tax_withheld": "Box 6 Medicare tax withheld",
    "federal_wages_and_taxes.box_7_social_security_tips": "Box 7 Social Security tips",
    "federal_wages_and_taxes.box_8_allocated_tips": "Box 8 allocated tips",
    "federal_wages_and_taxes.box_10_dependent_care_benefits": "Box 10 dependent care benefits",
    "federal_wages_and_taxes.box_11_nonqualified_plans": "Box 11 nonqualified plans",
}

_VARIANT_LABELS = {
    "clean_pdf": "Clean PDF",
    "clean_png": "Clean PNG",
    "external_clean_render": "Clean render",
    "compressed_jpeg": "JPEG compressed",
    "rotated_png": "Rotated",
    "blurred_png": "Blurred",
}


def summarize_document_evaluations(
    evaluations: Sequence[DocumentEvaluation],
    *,
    pipeline_id: str,
    entries: Sequence[DatasetManifestEntry] | None = None,
    include_failure_values: bool = True,
    benchmark_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Serialize aggregate benchmark metrics and inspectable field failures."""

    total = len(evaluations)
    failed = sum(evaluation.status != DocumentEvaluationStatus.SUCCESS for evaluation in evaluations)
    total_fields = sum(evaluation.total_fields for evaluation in evaluations)
    correct_fields = sum(evaluation.correct_fields for evaluation in evaluations)
    durations = [
        evaluation.duration_seconds
        for evaluation in evaluations
        if evaluation.duration_seconds is not None
    ]
    by_variant = defaultdict(lambda: {"documents": 0, "correct_fields": 0, "total_fields": 0})
    by_route = defaultdict(lambda: {"documents": 0, "correct_fields": 0, "total_fields": 0})
    by_field = defaultdict(lambda: {"correct": 0, "total": 0})
    entry_lookup = _entry_lookup(entries)
    field_failures: list[FieldFailure] = []

    for evaluation in evaluations:
        variant_bucket = by_variant[evaluation.variant_id]
        variant_bucket["documents"] += 1
        variant_bucket["correct_fields"] += evaluation.correct_fields
        variant_bucket["total_fields"] += evaluation.total_fields
        route_bucket = by_route[evaluation.extraction_route or "failed_or_unknown"]
        route_bucket["documents"] += 1
        route_bucket["correct_fields"] += evaluation.correct_fields
        route_bucket["total_fields"] += evaluation.total_fields
        for field_evaluation in evaluation.field_evaluations:
            field_bucket = by_field[field_evaluation.field_path]
            field_bucket["total"] += 1
            if field_evaluation.correct:
                field_bucket["correct"] += 1
            else:
                field_failures.append(
                    _field_failure(
                        evaluation=evaluation,
                        field_evaluation=field_evaluation,
                        source_dataset=_source_dataset_for(entry_lookup, evaluation),
                        include_values=include_failure_values,
                    )
                )

    return {
        "pipeline_id": pipeline_id,
        "documents": total,
        "successful_documents": total - failed,
        "failed_documents": failed,
        "failure_rate": failed / total if total else 0.0,
        "field_accuracy": correct_fields / total_fields if total_fields else 0.0,
        "correct_fields": correct_fields,
        "total_fields": total_fields,
        "average_duration_seconds": sum(durations) / len(durations) if durations else 0.0,
        "benchmark_metadata": _benchmark_metadata(
            pipeline_id=pipeline_id,
            entries=entries,
            extra=benchmark_metadata,
        ),
        "source_datasets": _source_datasets(entries),
        "document_conditions": _document_conditions(evaluations),
        "accuracy_by_variant": _accuracy_buckets(by_variant),
        "accuracy_by_route": _accuracy_buckets(by_route),
        "per_field_accuracy": _field_accuracy_buckets(by_field),
        "field_failure_count": len(field_failures),
        "field_failures": [
            failure.model_dump(mode="json", exclude_none=True)
            for failure in sorted(
                field_failures,
                key=lambda failure: (
                    failure.variant_id,
                    failure.document_id,
                    failure.field_path,
                ),
            )
        ],
    }


def _benchmark_metadata(
    *,
    pipeline_id: str,
    entries: Sequence[DatasetManifestEntry] | None,
    extra: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_id": pipeline_id,
        "schema_version": 2026,
        "source_datasets": _source_datasets(entries),
        "variant_scope": _document_conditions_from_entries(entries),
    }
    if extra:
        metadata.update(extra)
    return metadata


def markdown_report_path_for_json(json_path: str | Path) -> Path:
    """Return the matching Markdown report path for a JSON result path."""

    return Path(json_path).with_suffix(".md")


def write_markdown_report_for_json(
    json_path: str | Path,
    *,
    markdown_path: str | Path | None = None,
    failure_row_limit: int = DEFAULT_FAILURE_ROW_LIMIT,
) -> Path:
    """Write a Markdown companion report for a benchmark JSON result."""

    source_path = Path(json_path)
    target_path = Path(markdown_path) if markdown_path is not None else markdown_report_path_for_json(source_path)
    result = json.loads(source_path.read_text(encoding="utf-8"))
    markdown = render_benchmark_markdown(
        result,
        benchmark_name=_benchmark_name_from_path(source_path),
        failure_row_limit=failure_row_limit,
    )
    target_path.write_text(markdown, encoding="utf-8")
    return target_path


def render_benchmark_markdown(
    result: Mapping[str, Any],
    *,
    benchmark_name: str = "Benchmark Result",
    failure_row_limit: int = DEFAULT_FAILURE_ROW_LIMIT,
) -> str:
    """Render a benchmark summary JSON payload as reviewer-friendly Markdown."""

    lines = [
        f"# {_escape_markdown(benchmark_name)}",
        "",
        "Field accuracy is the percentage of individual W-2 values that matched the known correct answer.",
        "A document failure means the pipeline could not complete extraction for the document at all.",
        "Failure inspection values are intended for synthetic evaluation data; future real-data reports should redact sensitive values.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Pipeline | {_escape_markdown(str(result.get('pipeline_id', 'Not recorded')))} |",
        f"| Dataset/source | {_escape_markdown(_source_summary(result))} |",
        f"| Document condition / variant scope | {_escape_markdown(_condition_summary(result))} |",
        f"| Documents tested | {_format_int(result.get('documents'))} |",
        f"| Successful documents | {_format_int(result.get('successful_documents', _successful_documents(result)))} |",
        f"| Failed documents | {_format_int(result.get('failed_documents'))} |",
        f"| Failure rate | {_format_percent(result.get('failure_rate'))} |",
        f"| Fields checked | {_format_int(result.get('total_fields'))} |",
        f"| Correct fields | {_format_int(result.get('correct_fields'))} |",
        f"| Field accuracy | {_format_percent(result.get('field_accuracy'))} |",
        f"| Average processing time per document | {_format_seconds(result.get('average_duration_seconds'))} |",
        "",
    ]

    if len(result.get("accuracy_by_variant", {})) > 1:
        lines.extend(_variant_section(result))
    lines.extend(_field_section(result))
    lines.extend(_failure_section(result, failure_row_limit=failure_row_limit))
    lines.extend(_interpretation_section(result))
    return "\n".join(lines).rstrip() + "\n"


def _field_failure(
    *,
    evaluation: DocumentEvaluation,
    field_evaluation: FieldEvaluation,
    source_dataset: str | None,
    include_values: bool,
) -> FieldFailure:
    if field_evaluation.failure_kind is None:
        raise ValueError("Cannot serialize a correct field as a failure.")
    return FieldFailure(
        document_id=evaluation.sample_id,
        variant_id=evaluation.variant_id,
        field_path=field_evaluation.field_path,
        expected=_json_safe_value(field_evaluation.expected) if include_values else "[redacted]",
        predicted=_json_safe_value(field_evaluation.predicted) if include_values else "[redacted]",
        route=evaluation.extraction_route,
        failure_kind=field_evaluation.failure_kind,
        source_dataset=source_dataset,
    )


def _accuracy_buckets(buckets: Mapping[str, Mapping[str, int]]) -> dict[str, dict[str, float | int]]:
    return {
        key: {
            **value,
            "field_accuracy": (
                value["correct_fields"] / value["total_fields"]
                if value["total_fields"]
                else 0.0
            ),
        }
        for key, value in sorted(buckets.items())
    }


def _field_accuracy_buckets(buckets: Mapping[str, Mapping[str, int]]) -> dict[str, dict[str, float | int]]:
    return {
        key: {
            **value,
            "incorrect": value["total"] - value["correct"],
            "field_accuracy": value["correct"] / value["total"] if value["total"] else 0.0,
        }
        for key, value in sorted(
            buckets.items(),
            key=lambda item: (item[1]["correct"] / item[1]["total"] if item[1]["total"] else 0.0, item[0]),
        )
    }


def _entry_lookup(
    entries: Sequence[DatasetManifestEntry] | None,
) -> dict[tuple[str, str], DatasetManifestEntry]:
    if entries is None:
        return {}
    return {(entry.sample_id, entry.variant_id): entry for entry in entries}


def _source_dataset_for(
    entry_lookup: Mapping[tuple[str, str], DatasetManifestEntry],
    evaluation: DocumentEvaluation,
) -> str | None:
    entry = entry_lookup.get((evaluation.sample_id, evaluation.variant_id))
    if entry is None:
        return None
    return entry.dataset or entry.source.value


def _source_datasets(entries: Sequence[DatasetManifestEntry] | None) -> list[str]:
    if entries is None:
        return []
    values = {entry.dataset or entry.source.value for entry in entries}
    return sorted(value for value in values if value)


def _document_conditions(evaluations: Sequence[DocumentEvaluation]) -> list[str]:
    return sorted({evaluation.variant_id for evaluation in evaluations})


def _document_conditions_from_entries(entries: Sequence[DatasetManifestEntry] | None) -> list[str]:
    if entries is None:
        return []
    return sorted({entry.variant_id for entry in entries})


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _variant_section(result: Mapping[str, Any]) -> list[str]:
    lines = [
        "## Accuracy by Variant",
        "",
        "| Document condition | Documents | Field accuracy |",
        "| --- | ---: | ---: |",
    ]
    for variant_id, bucket in sorted(result.get("accuracy_by_variant", {}).items()):
        lines.append(
            f"| {_escape_markdown(_variant_label(variant_id))} | "
            f"{_format_int(bucket.get('documents'))} | "
            f"{_format_percent(bucket.get('field_accuracy'))} |"
        )
    lines.append("")
    return lines


def _field_section(result: Mapping[str, Any]) -> list[str]:
    lines = [
        "## Accuracy by Field",
        "",
    ]
    per_field = result.get("per_field_accuracy")
    if not per_field:
        lines.extend(
            [
                "Per-field accuracy was not stored in this JSON result.",
                "",
            ]
        )
        return lines

    lines.extend(
        [
            "| Field | Canonical path | Correct | Incorrect | Accuracy |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for field_path, bucket in sorted(
        per_field.items(),
        key=lambda item: (item[1].get("field_accuracy", 0.0), item[0]),
    ):
        lines.append(
            f"| {_escape_markdown(_field_label(field_path))} | "
            f"`{_escape_backticks(field_path)}` | "
            f"{_format_int(bucket.get('correct'))} | "
            f"{_format_int(bucket.get('incorrect'))} | "
            f"{_format_percent(bucket.get('field_accuracy'))} |"
        )
    lines.append("")
    return lines


def _failure_section(
    result: Mapping[str, Any],
    *,
    failure_row_limit: int,
) -> list[str]:
    lines = [
        "## Failure Inspection",
        "",
    ]
    failures = result.get("field_failures")
    if failures is None:
        lines.extend(
            [
                "Structured field failure records were not stored in this JSON result.",
                "",
            ]
        )
        return lines
    if not failures:
        lines.extend(
            [
                "No incorrect field results were recorded for this benchmark.",
                "",
            ]
        )
        return lines

    by_field = Counter(str(failure.get("field_path", "unknown")) for failure in failures)
    lines.extend(
        [
            "| Field | Incorrect results |",
            "| --- | ---: |",
        ]
    )
    for field_path, count in sorted(by_field.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {_escape_markdown(_field_label(field_path))} (`{_escape_backticks(field_path)}`) | {count:,} |")
    lines.append("")

    visible_failures = list(failures)[:failure_row_limit]
    if len(failures) > failure_row_limit:
        lines.extend(
            [
                f"Showing {failure_row_limit:,} of {len(failures):,} incorrect field results.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                f"Showing all {len(failures):,} incorrect field results.",
                "",
            ]
        )

    lines.extend(
        [
            "| Document | Variant | Field | Expected | Predicted | Route |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for failure in visible_failures:
        field_path = str(failure.get("field_path", ""))
        lines.append(
            f"| {_escape_markdown(str(failure.get('document_id', '')))} | "
            f"{_escape_markdown(_variant_label(str(failure.get('variant_id', ''))))} | "
            f"{_escape_markdown(_field_label(field_path))} (`{_escape_backticks(field_path)}`) | "
            f"{_format_report_value(failure.get('expected'))} | "
            f"{_format_report_value(failure.get('predicted'))} | "
            f"{_escape_markdown(str(failure.get('route') or 'Not recorded'))} |"
        )
    lines.append("")
    return lines


def _interpretation_section(result: Mapping[str, Any]) -> list[str]:
    lines = [
        "## Interpretation",
        "",
    ]
    failed_documents = int(result.get("failed_documents") or 0)
    if failed_documents:
        lines.append(f"{failed_documents:,} document(s) could not be processed in this benchmark.")
    else:
        lines.append("No document-level failures were recorded in this benchmark.")

    weakest_variant = _lowest_accuracy_item(result.get("accuracy_by_variant", {}))
    if weakest_variant is not None and len(result.get("accuracy_by_variant", {})) > 1:
        variant_id, bucket = weakest_variant
        lines.append(
            f"{_variant_label(variant_id)} documents had the lowest field accuracy "
            f"at {_format_percent(bucket.get('field_accuracy'))}."
        )

    weakest_field = _lowest_accuracy_item(result.get("per_field_accuracy", {}))
    if weakest_field is not None and float(weakest_field[1].get("field_accuracy") or 0.0) < 1.0:
        field_path, bucket = weakest_field
        lines.append(
            f"{_field_label(field_path)} was the lowest-accuracy field "
            f"at {_format_percent(bucket.get('field_accuracy'))}."
        )

    lines.append("These results do not establish production readiness by themselves.")
    lines.append("")
    return lines


def _lowest_accuracy_item(
    buckets: Mapping[str, Mapping[str, Any]],
) -> tuple[str, Mapping[str, Any]] | None:
    if not buckets:
        return None
    return min(
        buckets.items(),
        key=lambda item: (float(item[1].get("field_accuracy") or 0.0), item[0]),
    )


def _source_summary(result: Mapping[str, Any]) -> str:
    sources = result.get("source_datasets") or result.get("source_dataset")
    if isinstance(sources, list) and sources:
        return ", ".join(str(source) for source in sources)
    if isinstance(sources, str) and sources:
        return sources
    return "Not recorded in JSON result"


def _condition_summary(result: Mapping[str, Any]) -> str:
    conditions = result.get("document_conditions")
    if isinstance(conditions, list) and conditions:
        return ", ".join(_variant_label(str(condition)) for condition in conditions)
    variants = result.get("accuracy_by_variant", {})
    if variants:
        return ", ".join(_variant_label(str(variant)) for variant in variants)
    return "Not recorded in JSON result"


def _successful_documents(result: Mapping[str, Any]) -> int | None:
    documents = result.get("documents")
    failed = result.get("failed_documents")
    if isinstance(documents, int) and isinstance(failed, int):
        return documents - failed
    return None


def _benchmark_name_from_path(path: Path) -> str:
    return path.stem.replace("_", " ").title()


def _field_label(field_path: str) -> str:
    if field_path in _FIELD_LABELS:
        return _FIELD_LABELS[field_path]
    label = field_path.replace("_", " ").replace(".", " ").replace("[", " ").replace("]", "")
    return " ".join(part.capitalize() for part in label.split())


def _variant_label(variant_id: str) -> str:
    return _VARIANT_LABELS.get(variant_id, variant_id.replace("_", " ").title())


def _format_int(value: Any) -> str:
    if isinstance(value, int):
        return f"{value:,}"
    return "Not recorded"


def _format_seconds(value: Any) -> str:
    if isinstance(value, (float, int)):
        return f"{value:.3f} seconds"
    return "Not recorded"


def _format_percent(value: Any) -> str:
    if isinstance(value, (float, int)):
        return f"{value * 100:.2f}%"
    return "Not recorded"


def _format_report_value(value: Any) -> str:
    if value is None:
        return "`null`"
    return _escape_markdown(str(value))


def _escape_markdown(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _escape_backticks(value: str) -> str:
    return value.replace("`", "\\`")
