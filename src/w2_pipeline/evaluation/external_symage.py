"""Adapter for the Symage Hugging Face synthetic 2026 W-2 dataset."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import BytesIO
import json
from pathlib import Path
import re
from typing import Any

from PIL import Image
from pydantic import BaseModel, ConfigDict, Field

from w2_pipeline.contracts.w2 import (
    Address,
    Box12Entry,
    Box13Flags,
    Employee,
    Employer,
    FederalWagesAndTaxes,
    SourceFileType,
    StateLocalEntry,
    W2Document,
    W2Metadata,
)
from w2_pipeline.contracts.employee_name import split_first_name_and_initial
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
# Phase 8A bumped this from "symage-w2.phase3b.v1": the evaluated field set
# changed (employer.name added, see _first_line_of_combined_answer below),
# so ground truth/manifests generated under this version are not
# byte-comparable to anything generated under the prior version. Every
# `DatasetManifestEntry.generator_version` records this string, making the
# two eras of prepared datasets structurally distinguishable. Historical
# committed benchmark result artifacts (data/evaluation/results/*.json)
# from before this change are untouched and still valid for what they
# measured -- they simply predate employer.name being in scope at all; see
# docs/experiments/phase8a-final-benchmark-coverage.md.
# Phase 8D.1A bumped this from "symage-w2.phase8a.v2": the annotation-
# coverage audit found the FUNSD source already carries employer.address,
# employee.address, box_12_entries, and state_local_entries -- previously
# discarded by this adapter (see
# docs/experiments/phase8d1a-annotation-coverage-and-full-field-remediation.md),
# the same "evaluation adapter gap, not a production defect" pattern
# Phase 8A found for employer.name. Maps them deterministically from the
# same FUNSD question/answer linking `_extract_funsd_values` already
# uses -- no new annotation source, no fabricated values, no change to
# any field this adapter already mapped: ground truth generated under
# this version is a strict superset of the prior version's coverage.
# Following the exact precedent the v1->v2 bump set: `generator_version`
# and `evaluated_field_paths` are regenerated in place across the
# existing manifest/ground-truth files (`regenerate_external_ground_truth.py`,
# no network access needed -- it replays the same FUNSD mapping this
# module already used to build them, against the already-committed
# annotation bundles), while every already-committed `data/evaluation/
# results/*.json` benchmark result artifact from before this change is
# left untouched and remains valid for the (narrower) field set it
# measured.
EXTERNAL_ADAPTER_VERSION = "symage-w2.phase8d1a.v3"

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
    bboxes: list[list[int | float]] = Field(default_factory=list)
    ner_tags: list[int | str] = Field(default_factory=list)
    funsd_json: list[dict[str, Any]] = Field(default_factory=list)
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
            tokens=_coerce_tokens(record.get("tokens")),
            bboxes=_coerce_bboxes(record.get("bboxes")),
            ner_tags=_coerce_ner_tags(record.get("ner_tags")),
            funsd_json=_loads_funsd_json(record.get("funsd_json")),
            coco_json=_loads_coco_json(record.get("coco_json")),
            yolo_txt=_coerce_yolo_txt(record.get("yolo_txt")),
        )

    def build_ground_truth(self, record: dict[str, Any]) -> ExternalGroundTruthResult:
        """Map FUNSD key-value annotations into a canonical W2Document."""

        if not self.is_target_record(record):
            raise ExternalDatasetError(
                f"Unsupported external form_id: {record.get('form_id')!r}"
            )

        bundle = self.build_annotation_bundle(record)
        document_id = stable_external_sample_id(record)
        return build_ground_truth_from_funsd(bundle.funsd_json, document_id=document_id)

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


def build_ground_truth_from_funsd(
    funsd_json: list[dict[str, Any]], *, document_id: str
) -> ExternalGroundTruthResult:
    """Map FUNSD key-value annotations into a canonical W2Document.

    Pure function of the FUNSD entity list and a document ID -- no raw
    Hugging Face `record` dependency (Phase 8D.1A), so it can run
    directly against an already-committed `annotations/*.json`
    (`ExternalAnnotationBundle.funsd_json`) without needing network
    access to re-fetch the source dataset. `SymageW2Adapter.build_ground_truth`
    is the live, record-driven caller; `regenerate_external_ground_truth.py`
    is the offline, already-committed-annotations caller -- both produce
    identical output for the same FUNSD content and document ID, since
    this is the only place the mapping is implemented.
    """

    values, unmapped_questions = _extract_funsd_values(funsd_json)
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
        if field_path == "employee.first_name":
            first_name, middle_initial = split_first_name_and_initial(answer)
            employee.first_name = first_name
            employee.middle_initial = middle_initial
            evaluated_field_paths.add("employee.first_name")
            evaluated_field_paths.add("employee.middle_initial")
            continue
        if field_path == "employer.name":
            # Box c's linked answer is combined: name, then street
            # address, then city/state/ZIP, one per line -- confirmed
            # (Phase 8D.1A annotation-coverage audit) uniformly 3 lines
            # across all 150 base documents, never more/fewer. The first
            # line is employer.name (unchanged mapping); lines 2-3 are
            # now also mapped to employer.address (Phase 8D.1A -- Phase
            # 6B/8A left this unmapped as a separate, then-out-of-scope
            # gap). Never fabricated: a missing/blank line leaves that
            # piece unset and out of evaluated_field_paths, the same
            # "excluded rather than treated as a failure" convention
            # every other unmapped field already follows.
            lines = [line.strip() for line in answer.split("\n")]
            name = _first_line_of_combined_answer(answer)
            if name is not None:
                employer.name = name
                evaluated_field_paths.add("employer.name")
            if len(lines) >= 3 and lines[1]:
                employer.address.address_line_1 = lines[1]
                evaluated_field_paths.add("employer.address.address_line_1")
                city, state, postal_code = _parse_combined_city_state_zip(lines[2])
                if city is not None:
                    employer.address.city = city
                    evaluated_field_paths.add("employer.address.city")
                if state is not None:
                    employer.address.state = state
                    evaluated_field_paths.add("employer.address.state")
                if postal_code is not None:
                    employer.address.postal_code = postal_code
                    evaluated_field_paths.add("employer.address.postal_code")
                if city or state or postal_code:
                    employer.address.country = "US"
                    evaluated_field_paths.add("employer.address.country")
            continue
        if field_path == "employee.address.address_line_1":
            # Box f's linked answer is "street\nCity, ST ZIP", confirmed
            # uniformly 2 lines across all 150 base documents (Phase
            # 8D.1A annotation-coverage audit).
            lines = [line.strip() for line in answer.split("\n")]
            if lines and lines[0]:
                employee.address.address_line_1 = lines[0]
                evaluated_field_paths.add("employee.address.address_line_1")
            if len(lines) >= 2:
                city, state, postal_code = _parse_combined_city_state_zip(lines[1])
                if city is not None:
                    employee.address.city = city
                    evaluated_field_paths.add("employee.address.city")
                if state is not None:
                    employee.address.state = state
                    evaluated_field_paths.add("employee.address.state")
                if postal_code is not None:
                    employee.address.postal_code = postal_code
                    evaluated_field_paths.add("employee.address.postal_code")
                if city or state or postal_code:
                    employee.address.country = "US"
                    evaluated_field_paths.add("employee.address.country")
            continue
        if field_path == "box_12_entries" or field_path.startswith("state_local_entries."):
            # Handled below via `_extract_box_12_entries`/
            # `_extract_state_local_entry` directly from the raw FUNSD
            # entities -- recognized here only so this loop does not
            # report a real, answered question as unmapped (see
            # `_map_scalar_field`'s docstring note for why).
            continue
        converted = _convert_value(field_path, answer)
        _assign_field(employee, employer, federal, box_13, field_path, converted)
        evaluated_field_paths.add(field_path)

    # `evaluated_field_paths` entries must be real leaf paths
    # `w2_pipeline.evaluation.comparison.flatten_w2_document` actually
    # produces (`box_12_entries[0].code`, not the bare collection name
    # `box_12_entries`) -- `compare_w2_documents` uses this list as a
    # literal lookup key into the flattened dicts, so a bare collection
    # name that never appears in either dict was silently scored as an
    # automatic `UNEXPECTED` failure on every document (caught during
    # this phase's own expanded-benchmark smoke test, fixed here before
    # it ever reached a committed result artifact).
    box_12_entries = _extract_box_12_entries(funsd_json)
    for index in range(len(box_12_entries)):
        evaluated_field_paths.add(f"box_12_entries[{index}].code")
        evaluated_field_paths.add(f"box_12_entries[{index}].amount")

    state_local_entry = _extract_state_local_entry(values)
    state_local_entries = [state_local_entry] if state_local_entry is not None else []
    if state_local_entry is not None:
        # Unlike Box 12 (where a blank code means no entry at all),
        # every state/local question is present on every document with
        # only its *answer* sometimes blank (confirmed by the
        # annotation-coverage audit) -- the same "question present,
        # value may legitimately be null" shape the scalar per-question
        # loop above already scores unconditionally once its question is
        # found, applied here per sub-field for consistency.
        for field_name in _STATE_LOCAL_QUESTION_TO_FIELD_NAME.values():
            evaluated_field_paths.add(f"state_local_entries[0].{field_name}")

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
        box_12_entries=box_12_entries,
        box_13=box_13,
        state_local_entries=state_local_entries,
    )
    coverage_gaps = sorted(_KNOWN_CANONICAL_PATHS - evaluated_field_paths)
    return ExternalGroundTruthResult(
        document=document,
        evaluated_field_paths=sorted(evaluated_field_paths),
        unmapped_questions=sorted(set(unmapped_questions)),
        coverage_gaps=coverage_gaps,
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


def _coerce_tokens(value: Any) -> list[str]:
    raw_tokens = _coerce_sequence(value, field_name="tokens")
    if not all(isinstance(token, str) for token in raw_tokens):
        raise ExternalDatasetError("tokens must be a sequence of strings.")
    return list(raw_tokens)


def _coerce_bboxes(value: Any) -> list[list[int | float]]:
    raw_bboxes = _coerce_sequence(value, field_name="bboxes")
    bboxes: list[list[int | float]] = []
    for bbox in raw_bboxes:
        coordinates = _coerce_sequence(bbox, field_name="bboxes item")
        if len(coordinates) != 4:
            raise ExternalDatasetError("Each bboxes item must contain four coordinates.")
        if not all(isinstance(coordinate, (int, float)) for coordinate in coordinates):
            raise ExternalDatasetError("Each bboxes coordinate must be numeric.")
        bboxes.append(list(coordinates))
    return bboxes


def _coerce_ner_tags(value: Any) -> list[int | str]:
    raw_tags = _coerce_sequence(value, field_name="ner_tags")
    if not all(isinstance(tag, (int, str)) for tag in raw_tags):
        raise ExternalDatasetError("ner_tags must be a sequence of integers or strings.")
    return list(raw_tags)


def _coerce_sequence(value: Any, *, field_name: str) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if hasattr(value, "tolist"):
        converted = value.tolist()
        if isinstance(converted, list):
            return converted
    raise ExternalDatasetError(f"{field_name} must be a list-like sequence.")


def _loads_funsd_json(value: Any) -> list[dict[str, Any]]:
    loaded = _loads_json(value, field_name="funsd_json")
    if not isinstance(loaded, list):
        raise ExternalDatasetError("funsd_json must decode to a FUNSD entity list.")
    if not all(isinstance(entity, dict) for entity in loaded):
        raise ExternalDatasetError("Every funsd_json entity must be an object.")
    return loaded


def _loads_coco_json(value: Any) -> dict[str, Any]:
    loaded = _loads_json(value, field_name="coco_json")
    if not isinstance(loaded, dict):
        raise ExternalDatasetError("coco_json must decode to a COCO object.")
    return loaded


def _loads_json(value: Any, *, field_name: str) -> Any:
    if value in (None, ""):
        return [] if field_name == "funsd_json" else {}
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise ExternalDatasetError(f"Invalid {field_name} JSON.") from exc
    raise ExternalDatasetError(f"Unsupported {field_name} value.")


def _coerce_yolo_txt(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ExternalDatasetError("yolo_txt must be a string.")
    return value


def _extract_funsd_values(funsd_json: list[dict[str, Any]]) -> tuple[dict[str, str], list[str]]:
    if not funsd_json:
        raise ExternalDatasetError("FUNSD annotation entity list is empty.")

    entities = {entity.get("id"): entity for entity in funsd_json}
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
    if "employer s name" in question:
        return "employer.name"
    if "employee s address" in question:
        return "employee.address.address_line_1"
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
    # Phase 8D.1A: these six are recognized here only so
    # `build_ground_truth_from_funsd`'s main loop does not report them as
    # `unmapped_questions` -- they carry real, non-blank answers on this
    # dataset (confirmed by the annotation-coverage audit) but are
    # deliberately assembled by `_extract_state_local_entry`/
    # `_extract_box_12_entries` directly from the raw FUNSD entities
    # instead of through this scalar per-question path: state/local
    # fields all belong to one shared `StateLocalEntry`, and Box 12's
    # "Code" question text repeats 4 times (one per 12a-12d slot) so a
    # flat question-text-keyed dict can only ever keep the last one.
    if question == "state":
        return "state_local_entries.box_15_state"
    if question == "employer s state id number":
        return "state_local_entries.box_15_employer_state_id_number"
    if question == "state wages tips etc":
        return "state_local_entries.box_16_state_wages_tips_etc"
    if question == "state income tax":
        return "state_local_entries.box_17_state_income_tax"
    if question == "local wages tips etc":
        return "state_local_entries.box_18_local_wages_tips_etc"
    if question == "local income tax":
        return "state_local_entries.box_19_local_income_tax"
    if question == "locality name":
        return "state_local_entries.box_20_locality_name"
    if question == "code" or "box 12" in question:
        return "box_12_entries"
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


def _first_line_of_combined_answer(answer: str) -> str | None:
    """Return the first non-blank line of a combined multi-line FUNSD answer.

    Box c's linked answer has the structure
    "<employer name>\\n<street address>\\n<city, state ZIP>" -- the first
    line is a deterministic, authoritative mapping to `employer.name`,
    independent of any Pipeline A/B prediction or OCR output (confirmed
    against 5 documents in
    docs/experiments/phase6b-employer-name-investigation.md). Returns
    `None` (never fabricates a value) if the answer is empty or
    whitespace-only.
    """

    for line in answer.split("\n"):
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _parse_combined_city_state_zip(value: str) -> tuple[str | None, str | None, str | None]:
    """Parse a "City, ST ZIP" line (Phase 8D.1A) -- the real W-2 form's
    combined-block convention, comma-separated, confirmed against all 150
    base documents' Box c/f annotations (never fewer than city + state +
    ZIP, city itself sometimes multiple words, e.g. "West Henrietta")."""

    without_comma = value.replace(",", " ")
    parts = without_comma.split()
    if len(parts) < 3:
        return None, None, None
    postal_code = parts[-1]
    state = parts[-2]
    city = " ".join(parts[:-2])
    return city or None, state or None, postal_code or None


_CODE_QUESTION_TEXT = "code"
_BOX_12_QUESTION_MARKER = "box 12"


def _extract_box_12_entries(funsd_json: list[dict[str, Any]]) -> list[Box12Entry]:
    """Reconstruct Box 12's up-to-four code/amount slots (Phase 8D.1A)
    directly from FUNSD entity linking, not from `_extract_funsd_values`'s
    flat question-text-keyed dict: the "Code" question text repeats once
    per slot (12a-12d), so a flat dict can only retain the last one.

    Slots are paired by geometric row order (each "Code" question's own
    vertical position), not list/id order -- confirmed robust across all
    150 base documents by the annotation-coverage audit, where a blank
    code slot still counts as its own "Code" question/answer pair (answer
    text `""`), so the count and order always line up with the amount
    answers' own linking order. A slot is only emitted when its code is
    non-blank.

    Per the 2026 Form W-2 instructions, Box 12 represents IRS-coded
    items -- a code paired with an amount -- not a fixed set of visually
    printed slots; a slot with no code is not a coded item, whatever it
    happens to print. Confirmed empirically, not merely inferred from
    the schema (Phase 8D.1B): a dedicated audit of all 600 real slots
    (`phase8d1b_box12_slot_semantics_audit.json`) found a blank code's
    amount is *always* either blank or exactly "$0.00" -- 0/600
    exceptions in either direction -- and a populated code's amount is
    *always* nonzero. A blank-code "$0.00" is therefore a rendering
    placeholder for an unused slot, not a real entry with a genuinely
    zero-dollar amount, and is correctly excluded. See
    docs/experiments/phase8d1b-address-safety-and-box12-slot-semantics.md.
    """

    entities = {entity.get("id"): entity for entity in funsd_json}

    def linked_answer_text(entity: dict[str, Any]) -> str:
        for link in entity.get("linking") or []:
            if isinstance(link, list) and len(link) == 2:
                answer = entities.get(link[1])
                if answer and answer.get("label") == "answer":
                    return str(answer.get("text") or "").strip()
        return ""

    code_questions = [
        entity
        for entity in funsd_json
        if entity.get("label") == "question"
        and _normalize_question(str(entity.get("text") or "")) == _CODE_QUESTION_TEXT
    ]
    code_questions.sort(key=lambda entity: (entity.get("box") or [0, 0, 0, 0])[1])
    codes = [linked_answer_text(entity) for entity in code_questions]

    box_12_question = next(
        (
            entity
            for entity in funsd_json
            if entity.get("label") == "question"
            and _BOX_12_QUESTION_MARKER in _normalize_question(str(entity.get("text") or ""))
        ),
        None,
    )
    amounts: list[str] = []
    if box_12_question is not None:
        for link in box_12_question.get("linking") or []:
            if not isinstance(link, list) or len(link) != 2:
                continue
            answer = entities.get(link[1])
            if answer and answer.get("label") == "answer":
                amounts.append(str(answer.get("text") or "").strip())

    entries: list[Box12Entry] = []
    for code, amount_text in zip(codes, amounts):
        if not code:
            continue
        amount = _parse_decimal(amount_text)
        if amount is None:
            continue
        entries.append(Box12Entry(code=code, amount=amount))
    return entries


_STATE_LOCAL_QUESTION_TO_FIELD_NAME = {
    "state": "box_15_state",
    "employer s state id number": "box_15_employer_state_id_number",
    "state wages tips etc": "box_16_state_wages_tips_etc",
    "state income tax": "box_17_state_income_tax",
    "local wages tips etc": "box_18_local_wages_tips_etc",
    "local income tax": "box_19_local_income_tax",
    "locality name": "box_20_locality_name",
}
_STATE_LOCAL_MONEY_FIELD_NAMES = frozenset(
    {
        "box_16_state_wages_tips_etc",
        "box_17_state_income_tax",
        "box_18_local_wages_tips_etc",
        "box_19_local_income_tax",
    }
)


def _extract_state_local_entry(values: dict[str, str]) -> StateLocalEntry | None:
    """Build the one `StateLocalEntry` this dataset ever has (Phase
    8D.1A) from `_extract_funsd_values`'s flat question-text-keyed dict
    -- unlike Box 12, every state/local question text here is unique, so
    the flat dict already carries every value correctly with no
    entity-linking needed. The annotation-coverage audit found exactly
    one state/local row on all 150 base documents, so this never needs
    to reconstruct multiple rows; `None` (never a spuriously-empty
    all-null entry) when nothing at all was found."""

    fields: dict[str, object] = {}
    for question, field_name in _STATE_LOCAL_QUESTION_TO_FIELD_NAME.items():
        raw_value = values.get(question, "").strip()
        if not raw_value:
            continue
        if field_name in _STATE_LOCAL_MONEY_FIELD_NAMES:
            amount = _parse_decimal(raw_value)
            if amount is not None:
                fields[field_name] = amount
        else:
            fields[field_name] = raw_value

    if not fields:
        return None
    return StateLocalEntry(**fields)


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
    # Phase 8D.1A additions -- see EXTERNAL_ADAPTER_VERSION's docstring.
    "employer.address.address_line_1",
    "employer.address.city",
    "employer.address.state",
    "employer.address.postal_code",
    "employer.address.country",
    "employee.address.address_line_1",
    "employee.address.city",
    "employee.address.state",
    "employee.address.postal_code",
    "employee.address.country",
    # box_12_entries/state_local_entries are deliberately absent here:
    # their real evaluated_field_paths are index-qualified
    # (`box_12_entries[0].code`, `state_local_entries[0].box_15_state`,
    # ...) and vary in count per document, so there is no single fixed
    # path to track as a coverage gap the way every scalar field above
    # has one.
}
