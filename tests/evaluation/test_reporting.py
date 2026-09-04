import json
from pathlib import Path

from w2_pipeline.evaluation.manifest import (
    DatasetManifestEntry,
    DatasetSource,
    ExpectedQuality,
    VariantType,
)
from w2_pipeline.evaluation.models import (
    DocumentEvaluation,
    EvaluationFailureKind,
    FieldEvaluation,
)
from w2_pipeline.evaluation.reporting import (
    markdown_report_path_for_json,
    render_benchmark_markdown,
    summarize_document_evaluations,
    write_markdown_report_for_json,
)


def _evaluation(
    *,
    sample_id: str = "doc-1",
    variant_id: str = "external_clean_render",
    route: str = "ocr",
    fields: list[FieldEvaluation] | None = None,
) -> DocumentEvaluation:
    field_evaluations = fields or [
        FieldEvaluation(field_path="employee.first_name", expected="Jordan", predicted="Jordan", correct=True),
        FieldEvaluation(field_path="employee.ssn", expected="242-48-4959", predicted="242-48-4959", correct=True),
    ]
    correct_fields = sum(field.correct for field in field_evaluations)
    return DocumentEvaluation(
        sample_id=sample_id,
        variant_id=variant_id,
        tax_year=2026,
        pipeline_id="pipeline_x",
        total_fields=len(field_evaluations),
        correct_fields=correct_fields,
        field_accuracy=correct_fields / len(field_evaluations),
        field_evaluations=field_evaluations,
        duration_seconds=1.25,
        extraction_route=route,
    )


def _entry(sample_id: str, variant_id: str) -> DatasetManifestEntry:
    return DatasetManifestEntry(
        sample_id=sample_id,
        tax_year=2026,
        variant_id=variant_id,
        document_path=f"documents/{sample_id}.png",
        ground_truth_path=f"ground_truth/{sample_id}.json",
        variant_type=VariantType.EXTERNAL_CLEAN_RENDER,
        expected_quality=ExpectedQuality.CLEAN,
        source=DatasetSource.HUGGINGFACE,
        dataset="Symage/synthetic-us-forms-preview",
    )


def test_summarize_document_evaluations_serializes_field_failures() -> None:
    evaluation = _evaluation(
        fields=[
            FieldEvaluation(
                field_path="employee.first_name",
                expected="Jordan",
                predicted="Jordon",
                correct=False,
                failure_kind=EvaluationFailureKind.MISMATCH,
            ),
            FieldEvaluation(field_path="employee.ssn", expected="242-48-4959", predicted="242-48-4959", correct=True),
        ]
    )

    summary = summarize_document_evaluations(
        [evaluation],
        pipeline_id="pipeline_x",
        entries=[_entry("doc-1", "external_clean_render")],
    )

    assert summary["field_failure_count"] == 1
    assert summary["field_failures"] == [
        {
            "document_id": "doc-1",
            "variant_id": "external_clean_render",
            "field_path": "employee.first_name",
            "expected": "Jordan",
            "predicted": "Jordon",
            "route": "ocr",
            "failure_kind": "mismatch",
            "source_dataset": "Symage/synthetic-us-forms-preview",
        }
    ]


def test_markdown_report_formats_percentages_and_single_variant_summary() -> None:
    summary = summarize_document_evaluations(
        [
            _evaluation(
                fields=[
                    FieldEvaluation(field_path="employee.first_name", expected="Jordan", predicted="Jordan", correct=True),
                    FieldEvaluation(
                        field_path="employee.last_name",
                        expected="Lee",
                        predicted="Li",
                        correct=False,
                        failure_kind=EvaluationFailureKind.MISMATCH,
                    ),
                    FieldEvaluation(field_path="employee.ssn", expected="242-48-4959", predicted="242-48-4959", correct=True),
                ]
            )
        ],
        pipeline_id="pipeline_x",
    )

    markdown = render_benchmark_markdown(summary, benchmark_name="Tiny Benchmark")

    assert "# Tiny Benchmark" in markdown
    assert "| Field accuracy | 66.67% |" in markdown
    assert "## Accuracy by Variant" not in markdown
    assert "| Employee last name | `employee.last_name` | 0 | 1 | 0.00% |" in markdown
    assert "| doc-1 | Clean render | Employee last name (`employee.last_name`) | Lee | Li | ocr |" in markdown


def test_multi_variant_report_includes_variant_table() -> None:
    summary = summarize_document_evaluations(
        [
            _evaluation(sample_id="doc-1", variant_id="external_clean_render"),
            _evaluation(
                sample_id="doc-1",
                variant_id="blurred_png",
                fields=[
                    FieldEvaluation(
                        field_path="employee.first_name",
                        expected="Jordan",
                        predicted=None,
                        correct=False,
                        failure_kind=EvaluationFailureKind.MISSING,
                    ),
                    FieldEvaluation(field_path="employee.ssn", expected="242-48-4959", predicted="242-48-4959", correct=True),
                ],
            ),
        ],
        pipeline_id="pipeline_x",
    )

    markdown = render_benchmark_markdown(summary)

    assert "## Accuracy by Variant" in markdown
    assert "| Clean render | 1 | 100.00% |" in markdown
    assert "| Blurred | 1 | 50.00% |" in markdown
    assert "Blurred documents had the lowest field accuracy at 50.00%." in markdown


def test_failure_inspection_is_deterministically_truncated() -> None:
    fields = [
        FieldEvaluation(
            field_path=f"employee.first_name_{index:03}",
            expected=f"Name{index}",
            predicted=f"Narne{index}",
            correct=False,
            failure_kind=EvaluationFailureKind.MISMATCH,
        )
        for index in range(3)
    ]
    summary = summarize_document_evaluations(
        [_evaluation(fields=fields)],
        pipeline_id="pipeline_x",
    )

    markdown = render_benchmark_markdown(summary, failure_row_limit=2)

    assert "Showing 2 of 3 incorrect field results." in markdown
    assert "Name0" in markdown
    assert "Name1" in markdown
    assert "Name2" not in markdown


def test_zero_failure_benchmark_reports_no_incorrect_fields() -> None:
    summary = summarize_document_evaluations(
        [_evaluation()],
        pipeline_id="pipeline_x",
    )

    markdown = render_benchmark_markdown(summary)

    assert summary["field_failures"] == []
    assert "No incorrect field results were recorded for this benchmark." in markdown


def test_output_filename_pairing_and_report_write(tmp_path: Path) -> None:
    json_path = tmp_path / "foo.json"
    summary = summarize_document_evaluations(
        [_evaluation()],
        pipeline_id="pipeline_dynamic",
    )
    json_path.write_text(json.dumps(summary), encoding="utf-8")

    markdown_path = write_markdown_report_for_json(json_path)

    assert markdown_report_path_for_json(json_path) == tmp_path / "foo.md"
    assert markdown_path == tmp_path / "foo.md"
    assert "# Foo" in markdown_path.read_text(encoding="utf-8")
    assert "pipeline_dynamic" in markdown_path.read_text(encoding="utf-8")
