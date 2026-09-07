import json
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from pydantic import ValidationError

from w2_pipeline.contracts.w2 import Box12Entry, W2Document
from w2_pipeline.evaluation.external_symage import (
    HF_DATASET_NAME,
    SYMAGE_W2_FORM_ID,
    ExternalDatasetError,
    SymageW2Adapter,
    _first_line_of_combined_answer,
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
        _entity(18, "Employer’s name, address, and ZIP code", "question", [[18, 19]]),
        _entity(19, "Timberline Trading Co.\n105 Penland St\nMurphy, NC 28906", "answer"),
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
    assert document.employer.name == "Timberline Trading Co."
    assert "employee.ssn" in result.evaluated_field_paths
    assert "employee.first_name" in result.evaluated_field_paths
    assert "employee.middle_initial" in result.evaluated_field_paths
    assert "employer.name" in result.evaluated_field_paths
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


def test_external_adapter_maps_employer_address_lines() -> None:
    """Phase 8D.1A: the combined Box c answer's 2nd/3rd lines (street,
    "City, ST ZIP") are now mapped to employer.address -- the
    annotation-coverage audit found this was an evaluation-adapter gap
    (Phase 6B/8A had left it unmapped as then-out-of-scope), not a
    missing annotation."""

    result = SymageW2Adapter().build_ground_truth(sample_record())

    assert result.document.employer.address.address_line_1 == "105 Penland St"
    assert result.document.employer.address.city == "Murphy"
    assert result.document.employer.address.state == "NC"
    assert result.document.employer.address.postal_code == "28906"
    assert result.document.employer.address.country == "US"
    assert "employer.address.address_line_1" in result.evaluated_field_paths
    assert "employer.address.city" in result.evaluated_field_paths


def test_external_adapter_maps_multiword_employer_name_with_punctuation() -> None:
    record = sample_record()
    form = json.loads(record["funsd_json"])
    employer_answer = next(entity for entity in form if entity["id"] == 19)
    employer_answer["text"] = "Smith, Jones & Associates, Inc.\n1 Main St\nAnytown, CA 90001"
    record["funsd_json"] = json.dumps(form)

    result = SymageW2Adapter().build_ground_truth(record)

    assert result.document.employer.name == "Smith, Jones & Associates, Inc."


def test_external_adapter_does_not_fabricate_employer_name_when_answer_blank() -> None:
    record = sample_record()
    form = json.loads(record["funsd_json"])
    employer_answer = next(entity for entity in form if entity["id"] == 19)
    employer_answer["text"] = "   \n   \n   "
    record["funsd_json"] = json.dumps(form)

    result = SymageW2Adapter().build_ground_truth(record)

    assert result.document.employer.name is None
    assert "employer.name" not in result.evaluated_field_paths


def test_external_adapter_does_not_map_employer_name_when_question_unlinked() -> None:
    """No linked answer at all (not even a blank one) -- must not fabricate
    a value, and the question is simply absent from both `values` and
    `unmapped_questions`, the same behavior every other already-mapped
    field has when its answer is missing entirely."""

    record = sample_record()
    form = json.loads(record["funsd_json"])
    form = [entity for entity in form if entity["id"] not in {18, 19}]
    record["funsd_json"] = json.dumps(form)

    result = SymageW2Adapter().build_ground_truth(record)

    assert result.document.employer.name is None
    assert "employer.name" not in result.evaluated_field_paths


# --- Phase 8D.1A: employee.address, box_12_entries, state_local_entries ---


def _full_coverage_record() -> dict:
    """A `sample_record()` extended with the field families Phase 8D.1A
    added: Box f (employee address), two Box 12 code/amount slots (one
    populated with a blank-code "$0.00" artifact -- confirmed a real
    pattern in the annotation-coverage audit -- one genuinely populated),
    and one state/local row. Geometry (`box`) matches real relative
    top-to-bottom ordering so `_extract_box_12_entries`'s row-order
    sort behaves the same way it does on real documents."""

    record = sample_record()
    form = json.loads(record["funsd_json"])
    form.extend(
        [
            _entity(20, "Employee's address and ZIP code", "question", [[20, 21]]),
            _entity(21, "709 Mountain Island Hwy\nCharlotte, NC 28273", "answer"),
            _entity(22, "Code", "question", [[22, 23]], ),
            _entity(23, "", "answer"),
            _entity(24, "Code", "question", [[24, 25]]),
            _entity(25, "DD", "answer"),
            _entity(26, "See instructions for box 12", "question", [[26, 27], [26, 28]]),
            _entity(27, "$0.00", "answer"),
            _entity(28, "$2,994.37", "answer"),
            _entity(29, "State", "question", [[29, 30]]),
            _entity(30, "NC", "answer"),
            _entity(31, "Employer's state ID number", "question", [[31, 32]]),
            _entity(32, "35-6152316", "answer"),
            _entity(33, "State wages, tips, etc.", "question", [[33, 34]]),
            _entity(34, "$114,858.00", "answer"),
            _entity(35, "State income tax", "question", [[35, 36]]),
            _entity(36, "$4,339.59", "answer"),
        ]
    )
    # Geometric row order for the two "Code" questions: entity 22 (blank)
    # above entity 24 (DD), matching the 12a-then-12b top-to-bottom shape
    # `_extract_box_12_entries` sorts by.
    for entity in form:
        if entity["id"] == 22:
            entity["box"] = [0, 100, 10, 110]
        elif entity["id"] == 24:
            entity["box"] = [0, 200, 10, 210]
    record["funsd_json"] = json.dumps(form)
    return record


def test_external_adapter_maps_employee_address() -> None:
    result = SymageW2Adapter().build_ground_truth(_full_coverage_record())

    address = result.document.employee.address
    assert address.address_line_1 == "709 Mountain Island Hwy"
    assert address.city == "Charlotte"
    assert address.state == "NC"
    assert address.postal_code == "28273"
    assert address.country == "US"
    assert "employee.address.address_line_1" in result.evaluated_field_paths
    assert "employee.address.postal_code" in result.evaluated_field_paths


def test_external_adapter_maps_box_12_second_slot_only() -> None:
    """The first Code slot is blank with only a "$0.00" placeholder
    amount -- not a valid Box12Entry (the schema requires a code) -- so
    only the second, genuinely-coded slot should be emitted."""

    result = SymageW2Adapter().build_ground_truth(_full_coverage_record())

    assert result.document.box_12_entries == [Box12Entry(code="DD", amount=Decimal("2994.37"))]
    # Index-qualified paths (compare_w2_documents uses these as literal
    # flatten_w2_document lookup keys -- a bare "box_12_entries" is never
    # produced by flattening and would score as an automatic failure).
    assert "box_12_entries[0].code" in result.evaluated_field_paths
    assert "box_12_entries[0].amount" in result.evaluated_field_paths
    assert "box_12_entries[1].code" not in result.evaluated_field_paths


def test_external_adapter_maps_box_12_multiple_real_entries() -> None:
    record = _full_coverage_record()
    form = json.loads(record["funsd_json"])
    next(entity for entity in form if entity["id"] == 23)["text"] = "D"
    next(entity for entity in form if entity["id"] == 27)["text"] = "$7,142.00"
    record["funsd_json"] = json.dumps(form)

    result = SymageW2Adapter().build_ground_truth(record)

    assert result.document.box_12_entries == [
        Box12Entry(code="D", amount=Decimal("7142.00")),
        Box12Entry(code="DD", amount=Decimal("2994.37")),
    ]


def test_external_adapter_box_12_all_slots_blank_yields_no_entries() -> None:
    record = _full_coverage_record()
    form = json.loads(record["funsd_json"])
    next(entity for entity in form if entity["id"] == 25)["text"] = ""
    record["funsd_json"] = json.dumps(form)

    result = SymageW2Adapter().build_ground_truth(record)

    assert result.document.box_12_entries == []
    assert not any(path.startswith("box_12_entries[") for path in result.evaluated_field_paths)


def test_external_adapter_maps_state_local_entry() -> None:
    result = SymageW2Adapter().build_ground_truth(_full_coverage_record())

    entries = result.document.state_local_entries
    assert len(entries) == 1
    entry = entries[0]
    assert entry.box_15_state == "NC"
    assert entry.box_15_employer_state_id_number == "35-6152316"
    assert entry.box_16_state_wages_tips_etc == Decimal("114858.00")
    assert entry.box_17_state_income_tax == Decimal("4339.59")
    assert entry.box_18_local_wages_tips_etc is None
    assert entry.box_19_local_income_tax is None
    # Index-qualified paths, same reasoning as Box 12 above; every
    # state/local sub-field is scored even when null, since the question
    # itself is present on every document (unlike Box 12's per-slot
    # presence, which is itself the ground-truth signal).
    assert "state_local_entries[0].box_15_state" in result.evaluated_field_paths
    assert "state_local_entries[0].box_18_local_wages_tips_etc" in result.evaluated_field_paths


def test_external_adapter_state_local_missing_employer_id_still_maps_rest() -> None:
    """Confirmed a real pattern (114/150 base documents in the
    annotation-coverage audit have a blank employer state ID): a missing
    optional piece must not block the rest of the row."""

    record = _full_coverage_record()
    form = json.loads(record["funsd_json"])
    next(entity for entity in form if entity["id"] == 32)["text"] = ""
    record["funsd_json"] = json.dumps(form)

    result = SymageW2Adapter().build_ground_truth(record)

    entry = result.document.state_local_entries[0]
    assert entry.box_15_employer_state_id_number is None
    assert entry.box_15_state == "NC"


def test_external_adapter_no_state_local_questions_yields_no_entries() -> None:
    result = SymageW2Adapter().build_ground_truth(sample_record())

    assert result.document.state_local_entries == []
    assert not any(path.startswith("state_local_entries[") for path in result.evaluated_field_paths)


def test_external_adapter_employee_address_missing_second_line_maps_street_only() -> None:
    record = _full_coverage_record()
    form = json.loads(record["funsd_json"])
    next(entity for entity in form if entity["id"] == 21)["text"] = "709 Mountain Island Hwy"
    record["funsd_json"] = json.dumps(form)

    result = SymageW2Adapter().build_ground_truth(record)

    address = result.document.employee.address
    assert address.address_line_1 == "709 Mountain Island Hwy"
    assert address.city is None
    assert "employee.address.address_line_1" in result.evaluated_field_paths
    assert "employee.address.city" not in result.evaluated_field_paths


def test_first_line_of_combined_answer_is_a_pure_string_function() -> None:
    """Direct unit test of the exact mapping mechanism: takes only the raw
    FUNSD answer string, nothing else -- no extractor, OCR output, or
    document object anywhere in its signature or body, so it structurally
    cannot depend on a Pipeline A/B prediction."""

    assert _first_line_of_combined_answer(
        "Timberline Trading Co.\n105 Penland St\nMurphy, NC 28906"
    ) == "Timberline Trading Co."
    assert _first_line_of_combined_answer("Single Line Only") == "Single Line Only"
    assert _first_line_of_combined_answer("\n\nSecond line first") == "Second line first"
    assert _first_line_of_combined_answer("") is None
    assert _first_line_of_combined_answer("   \n  ") is None


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


def test_adapter_version_distinguishes_new_field_coverage_from_historical(
    tmp_path: Path,
) -> None:
    """Phase 8A bumped EXTERNAL_ADAPTER_VERSION when employer.name was
    added to evaluated field coverage, so datasets/manifests prepared
    under the two eras are structurally distinguishable via
    `generator_version` -- required to keep historical benchmark
    comparability explicit rather than silent."""

    from w2_pipeline.evaluation.external_symage import EXTERNAL_ADAPTER_VERSION

    assert EXTERNAL_ADAPTER_VERSION != "symage-w2.phase3b.v1"

    prepared = SymageW2Adapter().prepare_record(
        sample_record(), tmp_path, split="train", include_variants=False
    )

    assert prepared.manifest_entries[0].generator_version == EXTERNAL_ADAPTER_VERSION


def test_stable_external_sample_identity_prefers_record_id() -> None:
    assert (
        stable_external_sample_id(sample_record())
        == "symage_900001-irs_w2_single_page_2026-p0"
    )
