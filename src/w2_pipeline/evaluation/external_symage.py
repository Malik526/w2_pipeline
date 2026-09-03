"""Adapter for the Symage Hugging Face synthetic 2026 W-2 dataset."""

from __future__ import annotations

import json
import re
from io import BytesIO
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from PIL import Image
from pydantic import BaseModel, ConfigDict, Field

from w2_pipeline.contracts.w2 import (
    Address,
    Box13Flags,
    Employee,
    Employer,
    FederalWagesAndTaxes,
    SourceFileType,
    W2Document,
    W2Metadata,
)
from w2_pipeline.evaluation.manifest import (
    DatasetManifestEntry,
    DatasetSource,
    ExpectedQuality,
    VariantType,
)
from w2_pipeline.evaluation.rendering import (
    blur_and_resize_image,
    compress_image_to_jpeg,
    rotate_image,
)

HF_DATASET_NAME = "Symage/synthetic-us-forms-preview"
SYMAGE_W2_FORM_ID = "irs_w2_single_page_2026"
EXTERNAL_ADAPTER_VERSION = "symage-w2.phase3b.v1"

_ANSWER_BEARING_COLUMNS = (
    "tokens",
    "bboxes",
    "ner_tags",
    "funsd_json",
    "coco_json",
    "yolo_txt",
)


class ExternalDatasetError(ValueError):
    """Raised when an external record cannot be adapted safely."""


class ExternalAnnotationBundle(BaseModel):
    """Evaluator-side answer-bearing annotations withheld from extractors."""

    model_config = ConfigDict(extra="forbid")

    tokens: list[str] = Field(default_factory=list)
    bboxes: list[list[int]] = Field(default_factory=list)
    ner_tags: list[int | str] = Field(default_factory=list)
    funsd_json: dict[str, Any] = Field(default_factory=dict)
    coco_json: dict[str, Any] = Field(default_factory=dict)
    yolo_txt: str = ""


class ExternalGroundTruthResult(BaseModel):
    """Canonical ground truth plus coverage details derived from annotations."""

    model_config = ConfigDict(extra="forbid")

    document: W2Document
    evaluated_field_paths: list[str] = Field(default_factory=list)
    unmapped_questions: list[str] = Field(default_factory=list)
    coverage_gaps: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class PreparedExternalRecord:
    """Files and manifest entries produced for one external dataset record."""

    ground_truth: ExternalGroundTruthResult
    annotation_bundle: ExternalAnnotationBundle
    manifest_entries: list[DatasetManifestEntry]


class SymageW2Adapter:
    """Convert Symage W-2 records into Phase 3 evaluation abstractions."""

    dataset_name = HF_DATASET_NAME
    target_form_id = SYMAGE_W2_FORM_ID

    def is_target_record(self, record: dict[str, Any]) -> bool:
        """Return whether a Hugging Face row is the target 2026 W-2 form."""

        return record.get("form_id") == self.target_form_id

    def build_annotation_bundle(self, record: dict[str, Any]) -> ExternalAnnotationBundle:
        """Extract answer-bearing annotations into evaluator-side storage."""

        return ExternalAnnotationBundle(
            tokens=list(record.get("tokens") or []),
            bboxes=[list(box) for box in (record.get("bboxes") or [])],
            ner_tags=list(record.get("ner_tags") or []),
            funsd_json=_loads_json_field(record.get("funsd_json"), field_name="funsd_json"),
            coco_json=_loads_json_field(record.get("coco_json"), field_name="coco_json"),
            yolo_txt=str(record.get("yolo_txt") or ""),
        )

    def build_ground_truth(self, record: dict[str, Any]) -> ExternalGroundTruthResult:
        """Map FUNSD key-value annotations into a canonical W2Document."""

        if not self.is_target_record(record):
            raise ExternalDatasetError(
                f"Unsupported external form_id: {record.get('form_id')!r}"
            )

        bundle = self.build_annotation_bundle(record)
        values, unmapped_questions = _extract_funsd_values(bundle.funsd_json)
        document_id = stable_external_sample_id(record)
        federal = FederalWagesAndTaxes()
        employee = Employee(address=Address())
        employer = Employer(address=Address())
        box_13 = Box13Flags()
        evaluated_field_paths: set[str] = {
            "metadata.document_type",
            "metadata.tax_year",
            "metadata.schema_version",
        }

        for question, answer in values.items():
            field_path = _map_scalar_field(question)
            if field_path is None:
                unmapped_questions.append(question)
                continue
            converted = _convert_value(field_path, answer)
            _assign_field(employee, employer, federal, box_13, field_path, converted)
            evaluated_field_paths.add(field_path)

        if len(evaluated_field_paths) == 3:
            raise ExternalDatasetError(
                "External record did not contain mappable W-2 FUNSD annotations."
            )

        document = W2Document(
            metadata=W2Metadata(
                document_type="W-2",
                tax_year=2026,
                schema_version=2026,
                document_id=document_id,
                source_filename=f"{document_id}.png",
                source_file_type=SourceFileType.PNG,
            ),
            employee=employee,
            employer=employer,
            federal_wages_and_taxes=federal,
            box_13=box_13,
        )
        coverage_gaps = sorted(_KNOWN_CANONICAL_PATHS - evaluated_field_paths)
        return ExternalGroundTruthResult(
            document=document,
            evaluated_field_paths=sorted(evaluated_field_paths),
            unmapped_questions=sorted(set(unmapped_questions)),
            coverage_gaps=coverage_gaps,
        )

    def prepare_record(
        self,
        record: dict[str, Any],
        output_dir: str | Path,
        *,
        split: str,
        include_variants: bool = True,
    ) -> PreparedExternalRecord:
        """Persist one external record as Phase 3-compatible evaluation assets."""

        root = Path(output_dir)
        documents_dir = root / "documents"
        ground_truth_dir = root / "ground_truth"
        annotations_dir = root / "annotations"
        documents_dir.mkdir(parents=True, exist_ok=True)
        ground_truth_dir.mkdir(parents=True, exist_ok=True)
        annotations_dir.mkdir(parents=True, exist_ok=True)

        ground_truth = self.build_ground_truth(record)
        annotation_bundle = self.build_annotation_bundle(record)
        sample_id = ground_truth.document.metadata.document_id

        image_path = documents_dir / f"{sample_id}_external_clean_render.png"
        _save_record_image(record, image_path)
        ground_truth_path = ground_truth_dir / f"{sample_id}.json"
        annotations_path = annotations_dir / f"{sample_id}_annotations.json"
        ground_truth_path.write_text(
            ground_truth.document.model_dump_json(indent=2),
            encoding="utf-8",
        )
        annotations_path.write_text(
            annotation_bundle.model_dump_json(indent=2),
            encoding="utf-8",
        )

        manifest_entries = [
            _manifest_entry(
                record=record,
                sample_id=sample_id,
                split=split,
                document_path=image_path,
                root=root,
                ground_truth_path=ground_truth_path,
                annotations_path=annotations_path,
                variant_id=VariantType.EXTERNAL_CLEAN_RENDER.value,
                variant_type=VariantType.EXTERNAL_CLEAN_RENDER,
                expected_quality=ExpectedQuality.CLEAN,
                transformation_config={"source": "huggingface_image"},
                evaluated_field_paths=ground_truth.evaluated_field_paths,
            )
        ]

        if include_variants:
            manifest_entries.extend(
                _derive_external_variants(
                    record=record,
                    root=root,
                    source_image_path=image_path,
                    ground_truth_path=ground_truth_path,
                    annotations_path=annotations_path,
                    sample_id=sample_id,
                    split=split,
                    evaluated_field_paths=ground_truth.evaluated_field_paths,
                )
            )

        return PreparedExternalRecord(
            ground_truth=ground_truth,
            annotation_bundle=annotation_bundle,
            manifest_entries=manifest_entries,
        )


def stable_external_sample_id(record: dict[str, Any]) -> str:
    """Return a stable local ID from Hugging Face record metadata."""

    record_id = str(record.get("id") or "").strip()
    if record_id:
        safe_record_id = re.sub(r"[^a-zA-Z0-9_.-]+", "-", record_id)
        return f"symage_{safe_record_id}"
    identity_id = str(record.get("identity_id") or "unknown").strip()
    page = int(record.get("page") or 0)
    return f"symage_{identity_id}_{SYMAGE_W2_FORM_ID}_p{page}"


def _derive_external_variants(
    *,
    record: dict[str, Any],
    root: Path,
    source_image_path: Path,
    ground_truth_path: Path,
    annotations_path: Path,
    sample_id: str,
    split: str,
    evaluated_field_paths: list[str],
) -> list[DatasetManifestEntry]:
    documents_dir = root / "documents"
    rotated_path = documents_dir / f"{sample_id}_rotated.png"
    compressed_path = documents_dir / f"{sample_id}_compressed.jpg"
    blurred_path = documents_dir / f"{sample_id}_blurred.png"
    rotate_image(source_image_path, rotated_path, angle_degrees=2.0)
    compress_image_to_jpeg(source_image_path, compressed_path, quality=58)
    blur_and_resize_image(source_image_path, blurred_path, blur_radius=0.7, scale=0.75)

    return [
        _manifest_entry(
            record=record,
            sample_id=sample_id,
            split=split,
            document_path=rotated_path,
            root=root,
            ground_truth_path=ground_truth_path,
            annotations_path=annotations_path,
            variant_id=VariantType.ROTATED_PNG.value,
            variant_type=VariantType.ROTATED_PNG,
            expected_quality=ExpectedQuality.ROTATED,
            transformation_config={
                "source": VariantType.EXTERNAL_CLEAN_RENDER.value,
                "angle_degrees": 2.0,
            },
            evaluated_field_paths=evaluated_field_paths,
        ),
        _manifest_entry(
            record=record,
            sample_id=sample_id,
            split=split,
            document_path=compressed_path,
            root=root,
            ground_truth_path=ground_truth_path,
            annotations_path=annotations_path,
            variant_id=VariantType.COMPRESSED_JPEG.value,
            variant_type=VariantType.COMPRESSED_JPEG,
            expected_quality=ExpectedQuality.COMPRESSED,
            transformation_config={
                "source": VariantType.EXTERNAL_CLEAN_RENDER.value,
                "quality": 58,
            },
            evaluated_field_paths=evaluated_field_paths,
        ),
        _manifest_entry(
            record=record,
            sample_id=sample_id,
            split=split,
            document_path=blurred_path,
            root=root,
            ground_truth_path=ground_truth_path,
            annotations_path=annotations_path,
            variant_id=VariantType.BLURRED_PNG.value,
            variant_type=VariantType.BLURRED_PNG,
            expected_quality=ExpectedQuality.DEGRADED,
            transformation_config={
                "source": VariantType.EXTERNAL_CLEAN_RENDER.value,
                "blur_radius": 0.7,
                "scale": 0.75,
            },
            evaluated_field_paths=evaluated_field_paths,
        ),
    ]


def _manifest_entry(
    *,
    record: dict[str, Any],
    sample_id: str,
    split: str,
    document_path: Path,
    root: Path,
    ground_truth_path: Path,
    annotations_path: Path,
    variant_id: str,
    variant_type: VariantType,
    expected_quality: ExpectedQuality,
    transformation_config: dict[str, Any],
    evaluated_field_paths: list[str],
) -> DatasetManifestEntry:
    return DatasetManifestEntry(
        sample_id=sample_id,
        tax_year=2026,
        variant_id=variant_id,
        document_path=document_path.relative_to(root).as_posix(),
        ground_truth_path=ground_truth_path.relative_to(root).as_posix(),
        annotations_path=annotations_path.relative_to(root).as_posix(),
        variant_type=variant_type,
        expected_quality=expected_quality,
        source=DatasetSource.HUGGINGFACE,
        pii=False,
        synthetic=True,
        dataset=HF_DATASET_NAME,
        dataset_split=split,
        form_id=str(record.get("form_id") or ""),
        external_record_id=str(record.get("id") or ""),
        identity_id=str(record.get("identity_id") or ""),
        page=int(record.get("page") or 0),
        generator_version=EXTERNAL_ADAPTER_VERSION,
        transformation_config=transformation_config,
        evaluated_field_paths=evaluated_field_paths,
    )


def _save_record_image(record: dict[str, Any], output_path: Path) -> None:
    image = record.get("image")
    if isinstance(image, Image.Image):
        image.convert("RGB").save(output_path, format="PNG")
        return
    if isinstance(image, dict) and image.get("bytes"):
        with Image.open(BytesIO(image["bytes"])) as source:
            source.convert("RGB").save(output_path, format="PNG")
        return
    if isinstance(image, dict) and image.get("path"):
        with Image.open(image["path"]) as source:
            source.convert("RGB").save(output_path, format="PNG")
        return
    if isinstance(image, (str, Path)):
        with Image.open(image) as source:
            source.convert("RGB").save(output_path, format="PNG")
        return
    raise ExternalDatasetError("External record image is missing or unsupported.")


def _loads_json_field(value: Any, *, field_name: str) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ExternalDatasetError(f"Invalid {field_name} JSON.") from exc
        if not isinstance(loaded, dict):
            raise ExternalDatasetError(f"{field_name} JSON must decode to an object.")
        return loaded
    raise ExternalDatasetError(f"Unsupported {field_name} value.")


def _extract_funsd_values(funsd_json: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    form = funsd_json.get("form")
    if not isinstance(form, list):
        raise ExternalDatasetError("FUNSD annotation is missing a form array.")

    entities = {entity.get("id"): entity for entity in form if isinstance(entity, dict)}
    values: dict[str, str] = {}
    unmapped_questions: list[str] = []
    for entity in entities.values():
        if entity.get("label") != "question":
            continue
        question = _normalize_question(str(entity.get("text") or ""))
        answer_texts: list[str] = []
        for link in entity.get("linking") or []:
            if not isinstance(link, list) or len(link) != 2:
                continue
            answer = entities.get(link[1])
            if answer and answer.get("label") == "answer":
                answer_texts.append(str(answer.get("text") or ""))
        if answer_texts:
            values[question] = " ".join(answer_texts).strip()
        elif _map_scalar_field(question) is None:
            unmapped_questions.append(question)
    return values, unmapped_questions


def _normalize_question(value: str) -> str:
    normalized = value.lower().replace("’", "'")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _map_scalar_field(question: str) -> str | None:
    if "employee s social security number" in question:
        return "employee.ssn"
    if "employer identification number" in question or "ein" == question:
        return "employer.ein"
    if "control number" in question:
        return "employer.control_number"
    if "employee s first name" in question:
        return "employee.first_name"
    if question == "last name" or "employee last name" in question:
        return "employee.last_name"
    if question in {"suff", "suffix"}:
        return "employee.suffix"
    if "wages tips other compensation" in question:
        return "federal_wages_and_taxes.box_1_wages_tips_other_compensation"
    if "federal income tax withheld" in question:
        return "federal_wages_and_taxes.box_2_federal_income_tax_withheld"
    if "social security wages" in question:
        return "federal_wages_and_taxes.box_3_social_security_wages"
    if "social security tax withheld" in question:
        return "federal_wages_and_taxes.box_4_social_security_tax_withheld"
    if "medicare wages and tips" in question:
        return "federal_wages_and_taxes.box_5_medicare_wages_and_tips"
    if "medicare tax withheld" in question:
        return "federal_wages_and_taxes.box_6_medicare_tax_withheld"
    if "social security tips" in question:
        return "federal_wages_and_taxes.box_7_social_security_tips"
    if "allocated tips" in question:
        return "federal_wages_and_taxes.box_8_allocated_tips"
    if "verification code" in question:
        return "federal_wages_and_taxes.box_9_verification_code"
    if "dependent care benefits" in question:
        return "federal_wages_and_taxes.box_10_dependent_care_benefits"
    if "nonqualified plans" in question:
        return "federal_wages_and_taxes.box_11_nonqualified_plans"
    if "statutory employee" in question:
        return "box_13.statutory_employee"
    if "retirement plan" in question:
        return "box_13.retirement_plan"
    if "third party sick pay" in question:
        return "box_13.third_party_sick_pay"
    return None


def _convert_value(field_path: str, value: str) -> str | Decimal | bool | None:
    if field_path.startswith("federal_wages_and_taxes.") and not field_path.endswith(
        "box_9_verification_code"
    ):
        return _parse_decimal(value)
    if field_path.startswith("box_13."):
        return _parse_checkbox(value)
    return value.strip() or None


def _parse_decimal(value: str) -> Decimal | None:
    stripped = value.strip()
    if not stripped:
        return None
    normalized = stripped.replace("$", "").replace(",", "")
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ExternalDatasetError(f"Could not parse money value: {value!r}") from exc


def _parse_checkbox(value: str) -> bool:
    return value.strip().lower() in {"x", "checked", "true", "yes", "1"}


def _assign_field(
    employee: Employee,
    employer: Employer,
    federal: FederalWagesAndTaxes,
    box_13: Box13Flags,
    field_path: str,
    value: str | Decimal | bool | None,
) -> None:
    target_name, attribute = field_path.split(".", maxsplit=1)
    if target_name == "employee":
        setattr(employee, attribute, value)
    elif target_name == "employer":
        setattr(employer, attribute, value)
    elif target_name == "federal_wages_and_taxes":
        setattr(federal, attribute, value)
    elif target_name == "box_13":
        setattr(box_13, attribute, value)


_KNOWN_CANONICAL_PATHS = {
    "employee.ssn",
    "employee.first_name",
    "employee.last_name",
    "employee.suffix",
    "employer.ein",
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
