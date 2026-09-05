"""Defensive parsing of Qwen3-VL's raw text response into a JSON dict.

Pipeline B must stand on its own: this module strips a Markdown code fence
and parses JSON, nothing else. It must never OCR the image, regex-extract
values from free text, or otherwise repair a malformed response using
Pipeline A's deterministic parser -- that would blur the two pipelines'
extraction architectures together and invalidate the A/B comparison.
"""

from __future__ import annotations

import json
import re

from w2_pipeline.extraction.pipeline_b.errors import MalformedModelOutputError

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?|\n?```\s*$", re.IGNORECASE | re.MULTILINE)


def strip_code_fences(raw_text: str) -> str:
    """Remove a leading/trailing Markdown code fence, if present."""

    stripped = raw_text.strip()
    if stripped.startswith("```"):
        stripped = _CODE_FENCE_RE.sub("", stripped).strip()
    return stripped


def parse_model_json(raw_text: str) -> dict:
    """Parse the model's raw text response into a JSON object.

    Raises `MalformedModelOutputError` for anything that is not valid JSON,
    or that parses to something other than a JSON object at the top level.
    """

    candidate = strip_code_fences(raw_text)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise MalformedModelOutputError(f"Model response was not valid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise MalformedModelOutputError(
            f"Model response JSON must be an object, got {type(parsed).__name__}."
        )
    return parsed
