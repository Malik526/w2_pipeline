"""Phase 8D.1A: annotation-coverage audit for the external Symage benchmark.

Answers, for each canonical field, how many of the 150 base documents'
FUNSD source annotations actually carry a value, vs. how many the
ground-truth adapter (before/after Phase 8D.1A) reports as evaluated --
the gap between those two numbers is exactly the blind spot this phase
investigates and repairs. Runs entirely from the already-committed
`annotations/*.json` bundles, no network access needed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from w2_pipeline.evaluation.external_symage import (
    ExternalAnnotationBundle,
    _extract_funsd_values,
    _normalize_question,
    build_ground_truth_from_funsd,
)

DEFAULT_ANNOTATIONS_DIR = Path(
    "data/evaluation/external/symage-synthetic-us-forms-preview-final/annotations"
)

_TRACKED_QUESTIONS = {
    "employee.ssn": ("employee s social security number",),
    "employee.first_name": ("employee s first name",),
    "employee.last_name": ("last name",),
    "employee.suffix": ("suff", "suffix"),
    "employer.ein": ("employer identification number", "ein"),
    "employer.name_and_address_block": ("employer s name",),
    "employee.address_block": ("employee s address",),
    "employer.control_number": ("control number",),
    "box_1": ("wages tips other compensation",),
    "box_2": ("federal income tax withheld",),
    "box_3": ("social security wages",),
    "box_4": ("social security tax withheld",),
    "box_5": ("medicare wages and tips",),
    "box_6": ("medicare tax withheld",),
    "box_7": ("social security tips",),
    "box_8": ("allocated tips",),
    "box_10": ("dependent care benefits",),
    "box_11": ("nonqualified plans",),
    "box_12_code": ("code",),
    "box_12_amount": ("box 12",),
    "box_13_statutory_employee": ("statutory employee",),
    "box_13_retirement_plan": ("retirement plan",),
    "box_13_third_party_sick_pay": ("third party sick pay",),
    "box_15_state": ("state",),
    "box_15_employer_state_id": ("employer s state id number",),
    "box_16_state_wages": ("state wages tips etc",),
    "box_17_state_income_tax": ("state income tax",),
    "box_18_local_wages": ("local wages tips etc",),
    "box_19_local_income_tax": ("local income tax",),
    "box_20_locality_name": ("locality name",),
}


def run_audit(annotations_dir: str | Path = DEFAULT_ANNOTATIONS_DIR) -> dict[str, Any]:
    annotations_dir = Path(annotations_dir)
    files = sorted(annotations_dir.glob("*_annotations.json"))

    source_coverage = {key: 0 for key in _TRACKED_QUESTIONS}
    repaired_gt_coverage: dict[str, int] = {}
    box_12_entry_count_distribution: dict[int, int] = {}
    state_local_entry_count_distribution: dict[int, int] = {}
    documents = 0
    errors: list[str] = []

    for annotation_path in files:
        document_id = annotation_path.name.removesuffix("_annotations.json")
        bundle = ExternalAnnotationBundle.model_validate_json(annotation_path.read_text(encoding="utf-8"))
        documents += 1

        entities = {entity.get("id"): entity for entity in bundle.funsd_json}
        values, _unmapped = _extract_funsd_values(bundle.funsd_json)

        def any_linked_answer_non_blank(markers: tuple[str, ...]) -> bool:
            for entity in bundle.funsd_json:
                if entity.get("label") != "question":
                    continue
                question = _normalize_question(str(entity.get("text") or ""))
                # Exact match here, not substring: "code" as a substring
                # would also match Box 14b's "Treasury Tipped Occupation
                # Code(s)" question.
                if question not in markers:
                    continue
                for link in entity.get("linking") or []:
                    if not isinstance(link, list) or len(link) != 2:
                        continue
                    answer = entities.get(link[1])
                    if answer and answer.get("label") == "answer" and str(answer.get("text") or "").strip():
                        return True
            return False

        for field, markers in _TRACKED_QUESTIONS.items():
            if field == "box_12_code":
                # `values` collapses "Code"'s 4 repeated question-text
                # occurrences to the last one (see `_extract_box_12_entries`'s
                # own docstring) -- scan entities directly instead, so
                # "at least one populated code slot" is counted correctly.
                if any_linked_answer_non_blank(markers):
                    source_coverage[field] += 1
                continue
            question_texts = {
                _normalize_question(str(entity.get("text") or ""))
                for entity in bundle.funsd_json
                if entity.get("label") == "question"
            }
            matched_question = next(
                (question for question in question_texts if any(marker in question for marker in markers)),
                None,
            )
            if matched_question is not None and values.get(matched_question, "").strip():
                source_coverage[field] += 1

        try:
            result = build_ground_truth_from_funsd(bundle.funsd_json, document_id=document_id)
        except Exception as exc:  # noqa: BLE001 - audit must survive one bad record
            errors.append(f"{document_id}: {exc}")
            continue

        for path in result.evaluated_field_paths:
            repaired_gt_coverage[path] = repaired_gt_coverage.get(path, 0) + 1

        box_12_entry_count_distribution[len(result.document.box_12_entries)] = (
            box_12_entry_count_distribution.get(len(result.document.box_12_entries), 0) + 1
        )
        state_local_entry_count_distribution[len(result.document.state_local_entries)] = (
            state_local_entry_count_distribution.get(len(result.document.state_local_entries), 0) + 1
        )

    pre_8d1a_covered_paths = {
        "metadata.document_type",
        "metadata.tax_year",
        "metadata.schema_version",
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
    }
    newly_covered_paths = sorted(set(repaired_gt_coverage) - pre_8d1a_covered_paths)

    return {
        "annotations_dir": str(annotations_dir),
        "documents": documents,
        "errors": errors,
        "source_annotation_coverage": {
            field: {"documents_with_value": count, "of": documents}
            for field, count in sorted(source_coverage.items())
        },
        "repaired_ground_truth_coverage": {
            field: {"documents_with_value": count, "of": documents}
            for field, count in sorted(repaired_gt_coverage.items())
        },
        "fields_newly_covered_by_phase_8d1a": newly_covered_paths,
        "box_12_entry_count_distribution": box_12_entry_count_distribution,
        "state_local_entry_count_distribution": state_local_entry_count_distribution,
        "summary": (
            f"{len(newly_covered_paths)} canonical field paths gained ground-truth "
            f"coverage that the pre-8D.1A adapter discarded, across the same "
            f"{documents} base documents whose annotations already carried them."
        ),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations-dir", type=Path, default=DEFAULT_ANNOTATIONS_DIR)
    parser.add_argument("--output-json", type=Path, default=None)
    args = parser.parse_args(argv)

    report = run_audit(args.annotations_dir)
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
