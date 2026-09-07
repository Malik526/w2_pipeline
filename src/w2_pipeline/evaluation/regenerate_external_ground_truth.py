"""Phase 8D.1A: regenerate external Symage ground truth from committed annotations.

Repairs the evaluation-adapter blind spot the annotation-coverage audit
found (`docs/experiments/phase8d1a-annotation-coverage-and-full-field-remediation.md`):
`employer.address`, `employee.address`, `box_12_entries`, and
`state_local_entries` are present in the FUNSD source annotations but
were discarded by the pre-Phase-8D.1A ground-truth adapter, the same
"evaluation gap, not a production defect" pattern Phase 8A already found
and fixed once for `employer.name`.

Runs entirely from the already-committed `annotations/*.json` bundles
(`ExternalAnnotationBundle`) -- no Hugging Face network access needed,
since `build_ground_truth_from_funsd` (the exact mapping
`SymageW2Adapter.build_ground_truth` itself calls) is a pure function of
FUNSD content and a document ID, both already available locally. Each
base document's existing `ground_truth/<id>.json` is overwritten in
place with the repaired document; the manifest's `evaluated_field_paths`
and `generator_version` are updated in place for every variant entry
that shares that ground truth (following the exact precedent
`EXTERNAL_ADAPTER_VERSION`'s v1->v2 bump already set) -- everything
else (document_path, variant_id, transformation_config, ...) is left
untouched.

Never overwrites `data/evaluation/results/*.json` benchmark artifacts:
those remain historically valid for the (narrower) field set they
measured under the prior adapter version.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from w2_pipeline.evaluation.external_symage import (
    EXTERNAL_ADAPTER_VERSION,
    ExternalAnnotationBundle,
    ExternalDatasetError,
    build_ground_truth_from_funsd,
)
from w2_pipeline.evaluation.manifest import load_manifest_jsonl, write_manifest_jsonl


def regenerate(
    *,
    dataset_dir: str | Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    dataset_dir = Path(dataset_dir)
    annotations_dir = dataset_dir / "annotations"
    ground_truth_dir = dataset_dir / "ground_truth"
    manifest_path = dataset_dir / "manifest.jsonl"

    manifest = load_manifest_jsonl(manifest_path, validate_paths=False)
    evaluated_field_paths_by_gt_path: dict[str, list[str]] = {}
    field_coverage_deltas: list[dict[str, Any]] = []
    errors: list[str] = []

    annotation_files = sorted(annotations_dir.glob("*_annotations.json"))
    for annotation_path in annotation_files:
        document_id = annotation_path.name.removesuffix("_annotations.json")
        ground_truth_path = ground_truth_dir / f"{document_id}.json"
        if not ground_truth_path.exists():
            errors.append(f"{document_id}: no existing ground_truth file at {ground_truth_path}")
            continue

        old_payload = json.loads(ground_truth_path.read_text(encoding="utf-8"))
        old_document_id = old_payload.get("metadata", {}).get("document_id", document_id)

        bundle = ExternalAnnotationBundle.model_validate_json(annotation_path.read_text(encoding="utf-8"))
        try:
            result = build_ground_truth_from_funsd(bundle.funsd_json, document_id=old_document_id)
        except ExternalDatasetError as exc:
            errors.append(f"{document_id}: {exc}")
            continue

        new_paths = set(result.evaluated_field_paths)
        old_paths_guess = _guess_old_evaluated_field_paths(old_payload)
        field_coverage_deltas.append(
            {
                "document_id": document_id,
                "fields_added": sorted(new_paths - old_paths_guess),
                "unmapped_questions": result.unmapped_questions,
                "coverage_gaps": result.coverage_gaps,
            }
        )

        relative_gt_path = ground_truth_path.relative_to(dataset_dir).as_posix()
        evaluated_field_paths_by_gt_path[relative_gt_path] = result.evaluated_field_paths

        if not dry_run:
            ground_truth_path.write_text(result.document.model_dump_json(indent=2), encoding="utf-8")

    updated_entries = 0
    for entry in manifest.entries:
        new_field_paths = evaluated_field_paths_by_gt_path.get(entry.ground_truth_path)
        if new_field_paths is None:
            continue
        if not dry_run:
            entry.evaluated_field_paths = new_field_paths
            entry.generator_version = EXTERNAL_ADAPTER_VERSION
        updated_entries += 1

    if not dry_run:
        write_manifest_jsonl(manifest_path, manifest.entries)

    return {
        "dataset_dir": str(dataset_dir),
        "dry_run": dry_run,
        "annotation_files_found": len(annotation_files),
        "ground_truth_files_regenerated": len(field_coverage_deltas),
        "manifest_entries_updated": updated_entries,
        "errors": errors,
        "field_coverage_deltas": field_coverage_deltas,
    }


def _guess_old_evaluated_field_paths(old_payload: dict[str, Any]) -> set[str]:
    """Best-effort reconstruction of what the pre-8D.1A adapter would
    have reported as evaluated for this document, purely for the
    human-readable "fields_added" delta in the report -- never used to
    decide what the new ground truth actually contains."""

    paths: set[str] = {"metadata.document_type", "metadata.tax_year", "metadata.schema_version"}
    scalar_paths = (
        "employee.ssn",
        "employee.first_name",
        "employee.middle_initial",
        "employee.last_name",
        "employee.suffix",
        "employer.ein",
        "employer.name",
        "employer.control_number",
        "federal_wages_and_taxes.box_1_wages_tips_other_compensation",
        "federal_wages_and_taxes.box_2_federal_income_tax_withheld",
        "federal_wages_and_taxes.box_3_social_security_wages",
        "federal_wages_and_taxes.box_4_social_security_tax_withheld",
        "federal_wages_and_taxes.box_5_medicare_wages_and_tips",
        "federal_wages_and_taxes.box_6_medicare_tax_withheld",
        "federal_wages_and_taxes.box_7_social_security_tips",
        "federal_wages_and_taxes.box_8_allocated_tips",
        "federal_wages_and_taxes.box_9_verification_code",
        "federal_wages_and_taxes.box_10_dependent_care_benefits",
        "federal_wages_and_taxes.box_11_nonqualified_plans",
        "box_13.statutory_employee",
        "box_13.retirement_plan",
        "box_13.third_party_sick_pay",
    )
    for path in scalar_paths:
        target, attribute = path.split(".", maxsplit=1)
        section = old_payload.get(target, {})
        if isinstance(section, dict) and section.get(attribute) is not None:
            paths.add(path)
    return paths


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dataset_dir",
        type=Path,
        default=Path("data/evaluation/external/symage-synthetic-us-forms-preview-final"),
        nargs="?",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing files.")
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--no-deltas", action="store_true", help="Omit the per-document delta list from output.")
    args = parser.parse_args(argv)

    report = regenerate(dataset_dir=args.dataset_dir, dry_run=args.dry_run)
    if args.no_deltas:
        report = {key: value for key, value in report.items() if key != "field_coverage_deltas"}

    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
