import pytest

from w2_pipeline.extraction.pipeline_b.errors import MalformedModelOutputError
from w2_pipeline.extraction.pipeline_b.response_parsing import (
    parse_model_json,
    strip_code_fences,
)


def test_strip_code_fences_removes_json_fence() -> None:
    raw = '```json\n{"a": 1}\n```'

    assert strip_code_fences(raw) == '{"a": 1}'


def test_strip_code_fences_removes_bare_fence() -> None:
    raw = '```\n{"a": 1}\n```'

    assert strip_code_fences(raw) == '{"a": 1}'


def test_strip_code_fences_is_noop_without_fence() -> None:
    raw = '{"a": 1}'

    assert strip_code_fences(raw) == '{"a": 1}'


def test_parse_model_json_parses_fenced_object() -> None:
    raw = '```json\n{"employee": {"first_name": "Ada"}}\n```'

    parsed = parse_model_json(raw)

    assert parsed == {"employee": {"first_name": "Ada"}}


def test_parse_model_json_parses_plain_object() -> None:
    parsed = parse_model_json('{"box_13": {"retirement_plan": true}}')

    assert parsed == {"box_13": {"retirement_plan": True}}


def test_parse_model_json_rejects_invalid_json() -> None:
    with pytest.raises(MalformedModelOutputError, match="not valid JSON"):
        parse_model_json("this is not json at all")


def test_parse_model_json_rejects_truncated_json() -> None:
    with pytest.raises(MalformedModelOutputError):
        parse_model_json('{"employee": {"first_name": "Ada"')


def test_parse_model_json_rejects_non_object_top_level() -> None:
    with pytest.raises(MalformedModelOutputError, match="must be an object"):
        parse_model_json("[1, 2, 3]")


def test_parse_model_json_rejects_scalar_top_level() -> None:
    with pytest.raises(MalformedModelOutputError, match="must be an object"):
        parse_model_json('"just a string"')


def test_parse_model_json_preserves_unicode() -> None:
    parsed = parse_model_json('{"employee": {"first_name": "Jos\\u00e9"}}')

    assert parsed["employee"]["first_name"] == "José"


def test_parse_model_json_handles_prose_wrapped_fence_with_prefix_text() -> None:
    raw = 'Here is the JSON:\n```json\n{"employee": {}}\n```'

    with pytest.raises(MalformedModelOutputError):
        parse_model_json(raw)
