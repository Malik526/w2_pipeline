import json
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from pydantic import ValidationError

from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.evaluation.external_symage import (
    HF_DATASET_NAME,
    SYMAGE_W2_FORM_ID,
    ExternalDatasetError,
    SymageW2Adapter,
    stable_external_sample_id,
)
from w2_pipeline.evaluation.inputs import ExtractionInput
from w2_pipeline.evaluation.manifest import (
    BenchmarkMode,
    DatasetSource,
    VariantType,
    load_manifest_jsonl,
    write_manifest_jsonl,
)
from w2_pipeline.evaluation.runner import evaluate_manifest


def _entity(
    entity_id: int,
    text: str,
    label: str,
    linking: list[list[int]] | None = None,
    *,
    words: list[str] | None = None,
) -> dict:
    return {
        "id": entity_id,
        "text": text,
        "label": label,
        "box": [0, 0, 10, 10],
        "words": words or [],
        "linking": linking or [],
    }


def sample_record() -> dict:
    form = [
        _entity(0, "Employee's social security number", "question", [[0, 1]]),
        _entity(1, "242-48-4959", "answer"),
        _entity(2, "Employee's first name and initial", "question", [[2, 3]]),
        _entity(3, "Jordan Q", "answer", words=["Jordan", "Q"]),
        _entity(4, "Last name", "question", [[4, 5]]),
        _entity(5, "Lee", "answer"),
        _entity(6, "Suff.", "question", [[6, 7]]),
        _entity(7, "Jr", "answer"),
        _entity(8, "Employer identification number (EIN)", "question", [[8, 9]]),
        _entity(9, "75-5696876", "answer"),
        _entity(10, "Wages, tips, other compensation", "question", [[10, 11]]),
        _entity(11, "52,001.42", "answer"),
        _entity(12, "Federal income tax withheld", "question", [[12, 13]]),
        _entity(13, "8,100.00", "answer"),
        _entity(14, "Retirement plan", "question", [[14, 15]]),
        _entity(15, "X", "answer"),
        _entity(16, "Dataset-only unsupported field", "question", [[16, 17]]),
        _entity(17, "answer text", "answer"),
    ]
    return {
        "id": "900001-irs_w2_single_page_2026-p0",
        "identity_id": 900001,
        "form_id": SYMAGE_W2_FORM_ID,
        "page": 0,
        "image": Image.new("RGB", (120, 80), color="white"),
        "tokens": ["Employee's", "social", "security", "number", "242-48-4959"],
        "bboxes": [[0, 0, 10, 10]],
        "ner_tags": [3, 4, 4, 4, 5],
        "funsd_json": json.dumps(form),
        "coco_json": json.dumps({"images": [{"file_name": "typed_p0.png"}]}),
        "yolo_txt": "5 0.5 0.5 0.1 0.1",
    }


def test_external_adapter_maps_funsd_annotations_to_canonical_ground_truth() -> None:
    result = SymageW2Adapter().build_ground_truth(sample_record())

    document = result.document
    assert isinstance(document, W2Document)
    assert document.employee.ssn == "242-48-4959"
    assert document.employee.first_name == "Jordan"
    assert document.employee.middle_initial == "Q"
    assert document.employee.last_name == "Lee"
    assert document.employee.suffix == "Jr"
    assert document.employer.ein == "75-5696876"
    assert (
        document.federal_wages_and_taxes.box_1_wages_tips_other_compensation
        == Decimal("52001.42")
    )
    assert document.box_13.retirement_plan is True
    assert "employee.ssn" in result.evaluated_field_paths
    assert "employee.first_name" in result.evaluated_field_paths
    assert "employee.middle_initial" in result.evaluated_field_paths
    assert "dataset only unsupported field" in result.unmapped_questions


@pytest.mark.parametrize(
    ("answer", "expected_first", "expected_initial"),
    [
        ("Nicole", "Nicole", None),
        ("Jesús D", "Jesús", "D"),
        ("Óliver", "Óliver", None),
    ],
)
def test_external_adapter_splits_box_e_first_name_and_initial_variants(
    answer: str,
    expected_first: str,
    expected_initial: str | None,
) -> None:
    record = sample_record()
    form = json.loads(record["funsd_json"])
    form[3]["text"] = answer
    form[3]["words"] = answer.split()
    record["funsd_json"] = json.dumps(form)

    result = SymageW2Adapter().build_ground_truth(record)

    assert result.document.employee.first_name == expected_first
    assert result.document.employee.middle_initial == expected_initial


def test_extraction_input_rejects_answer_bearing_annotations() -> None:
    with pytest.raises(ValidationError):
        ExtractionInput.model_validate(
            {
                "document_path": "/tmp/sample.png",
                "document_id": "doc",
                "tax_year_hint": 2026,
                "source": "huggingface",
                "tokens": ["answer leakage"],
            }
        )


def test_prepare_record_keeps_annotations_evaluator_side_and_links_variants(tmp_path: Path) -> None:
    prepared = SymageW2Adapter().prepare_record(sample_record(), tmp_path, split="train")
    write_manifest_jsonl(tmp_path / "manifest.jsonl", prepared.manifest_entries)
    manifest = load_manifest_jsonl(tmp_path / "manifest.jsonl")

    assert len(manifest.entries) == 4
    first = manifest.entries[0]
    assert first.source == DatasetSource.HUGGINGFACE
    assert first.synthetic is True
    assert first.dataset == HF_DATASET_NAME
    assert first.form_id == SYMAGE_W2_FORM_ID
    assert first.external_record_id == "900001-irs_w2_single_page_2026-p0"
    assert first.variant_type == VariantType.EXTERNAL_CLEAN_RENDER
    assert first.benchmark_mode == BenchmarkMode.END_TO_END
    assert first.annotations_path is not None
    assert first.evaluated_field_paths is not None
    assert all(entry.ground_truth_path == first.ground_truth_path for entry in manifest.entries)
    assert all(entry.annotations_path == first.annotations_path for entry in manifest.entries)
    annotations = json.loads((tmp_path / first.annotations_path).read_text(encoding="utf-8"))
    assert annotations["tokens"] == sample_record()["tokens"]
    assert isinstance(annotations["funsd_json"], list)
    assert annotations["funsd_json"][0]["label"] == "question"


def test_prepare_record_accepts_pandas_style_image_bytes(tmp_path: Path) -> None:
    image_buffer = BytesIO()
    Image.new("RGB", (64, 32), color="white").save(image_buffer, format="PNG")
    record = sample_record()
    record["image"] = {"bytes": image_buffer.getvalue(), "path": None}

    prepared = SymageW2Adapter().prepare_record(
        record,
        tmp_path,
        split="train",
        include_variants=False,
    )

    document_path = tmp_path / prepared.manifest_entries[0].document_path
    assert document_path.exists()
    with Image.open(document_path) as image:
        assert image.size == (64, 32)


def test_runner_passes_only_image_input_to_external_extractor(tmp_path: Path) -> None:
    prepared = SymageW2Adapter().prepare_record(
        sample_record(),
        tmp_path,
        split="train",
        include_variants=False,
    )
    entry = prepared.manifest_entries[0]

    class AssertingExtractor:
        def extract(self, extraction_input: ExtractionInput) -> W2Document:
            assert extraction_input.document_path.exists()
            assert extraction_input.tax_year_hint == 2026
            assert not hasattr(extraction_input, "tokens")
            assert not hasattr(extraction_input, "funsd_json")
            return prepared.ground_truth.document

    result = evaluate_manifest(
        entries=[entry],
        manifest_base_dir=tmp_path,
        extractor=AssertingExtractor(),
        pipeline_id="external-ground-truth-stub",
    )

    assert result.field_accuracy == 1.0


def test_external_partial_ground_truth_does_not_penalize_unannotated_fields(tmp_path: Path) -> None:
    prepared = SymageW2Adapter().prepare_record(
        sample_record(),
        tmp_path,
        split="train",
        include_variants=False,
    )
    expected = prepared.ground_truth.document
    predicted = expected.model_copy(deep=True)
    predicted.employee.address.city = "ShouldNotMatter"

    class PartialExtractor:
        def extract(self, extraction_input: ExtractionInput) -> W2Document:
            return predicted

    result = evaluate_manifest(
        entries=[prepared.manifest_entries[0]],
        manifest_base_dir=tmp_path,
        extractor=PartialExtractor(),
        pipeline_id="partial",
    )

    assert "employee.address.city" not in prepared.manifest_entries[0].evaluated_field_paths
    assert result.field_accuracy == 1.0


def test_unsupported_or_incomplete_external_annotations_fail_clearly() -> None:
    record = sample_record()
    record["form_id"] = "irs_1040_modern_2024"

    with pytest.raises(ExternalDatasetError):
        SymageW2Adapter().build_ground_truth(record)

    incomplete = sample_record()
    incomplete["funsd_json"] = json.dumps([])

    with pytest.raises(ExternalDatasetError):
        SymageW2Adapter().build_ground_truth(incomplete)


def test_external_annotation_shape_validation_is_field_specific() -> None:
    adapter = SymageW2Adapter()

    wrong_funsd = sample_record()
    wrong_funsd["funsd_json"] = json.dumps({"form": []})
    with pytest.raises(ExternalDatasetError, match="funsd_json must decode"):
        adapter.build_annotation_bundle(wrong_funsd)

    wrong_coco = sample_record()
    wrong_coco["coco_json"] = json.dumps([])
    with pytest.raises(ExternalDatasetError, match="coco_json must decode"):
        adapter.build_annotation_bundle(wrong_coco)

    wrong_yolo = sample_record()
    wrong_yolo["yolo_txt"] = ["not", "text"]
    with pytest.raises(ExternalDatasetError, match="yolo_txt must be a string"):
        adapter.build_annotation_bundle(wrong_yolo)

    wrong_bbox = sample_record()
    wrong_bbox["bboxes"] = [[0, 1, 2]]
    with pytest.raises(ExternalDatasetError, match="four coordinates"):
        adapter.build_annotation_bundle(wrong_bbox)


def test_stable_external_sample_identity_prefers_record_id() -> None:
    assert (
        stable_external_sample_id(sample_record())
        == "symage_900001-irs_w2_single_page_2026-p0"
    )
