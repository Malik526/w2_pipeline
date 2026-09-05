import json

from w2_pipeline.contracts.w2 import (
    Box12Entry,
    Box13Flags,
    Box14Entry,
    Employee,
    Employer,
    FederalWagesAndTaxes,
    StateLocalEntry,
    TippedOccupationCode,
)
from w2_pipeline.extraction.pipeline_b.prompt import (
    CANONICAL_JSON_SHAPE,
    build_chat_messages,
    build_extraction_prompt,
)


def test_prompt_embeds_valid_json_schema_shape() -> None:
    prompt = build_extraction_prompt()
    schema_json_text = json.dumps(CANONICAL_JSON_SHAPE, indent=2)

    assert schema_json_text in prompt
    assert json.loads(schema_json_text) == CANONICAL_JSON_SHAPE


def test_prompt_schema_keys_match_canonical_employee_fields() -> None:
    assert set(CANONICAL_JSON_SHAPE["employee"]) - {"address"} == set(Employee.model_fields) - {
        "address"
    }
    assert set(CANONICAL_JSON_SHAPE["employer"]) - {"address"} == set(Employer.model_fields) - {
        "address"
    }
    assert set(CANONICAL_JSON_SHAPE["federal_wages_and_taxes"]) == set(
        FederalWagesAndTaxes.model_fields
    )
    assert set(CANONICAL_JSON_SHAPE["box_13"]) == set(Box13Flags.model_fields)


def test_prompt_never_mentions_ground_truth_or_specific_document_values() -> None:
    prompt = build_extraction_prompt().lower()

    for forbidden in ("ground truth", "expected value", "answer key", "symage"):
        assert forbidden not in prompt


def test_prompt_instructs_null_for_missing_and_no_inference() -> None:
    prompt = build_extraction_prompt()

    assert "null" in prompt
    assert "never infer" in prompt.lower() or "do not infer" in prompt.lower()


def test_build_chat_messages_attaches_image_and_text() -> None:
    from PIL import Image

    image = Image.new("RGB", (4, 4), color="white")
    messages = build_chat_messages(image, "custom prompt text")

    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    content_types = [item["type"] for item in messages[0]["content"]]
    assert content_types == ["image", "text"]
    assert messages[0]["content"][0]["image"] is image
    assert messages[0]["content"][1]["text"] == "custom prompt text"


def test_build_chat_messages_defaults_to_extraction_prompt() -> None:
    from PIL import Image

    image = Image.new("RGB", (4, 4), color="white")
    messages = build_chat_messages(image)

    assert messages[0]["content"][1]["text"] == build_extraction_prompt()


def test_box12_and_box14_entry_shapes_match_canonical_fields() -> None:
    assert set(Box12Entry.model_fields) == {"code", "amount"}
    assert set(Box14Entry.model_fields) == {"label", "amount", "value"}
    assert set(TippedOccupationCode.model_fields) == {"code"}
    assert set(StateLocalEntry.model_fields) == {
        "box_15_state",
        "box_15_employer_state_id_number",
        "box_16_state_wages_tips_etc",
        "box_17_state_income_tax",
        "box_18_local_wages_tips_etc",
        "box_19_local_income_tax",
        "box_20_locality_name",
    }


def test_prompt_module_has_no_pipeline_a_dependency() -> None:
    import w2_pipeline.extraction.pipeline_b.prompt as prompt_module

    source = prompt_module.__file__
    with open(source, encoding="utf-8") as file_obj:
        contents = file_obj.read()

    for forbidden in ("tesseract", "paddle", "parser_2026", "ocr"):
        assert forbidden not in contents.lower()
