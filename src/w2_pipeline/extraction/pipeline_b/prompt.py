"""Schema-guided extraction prompt for Pipeline B's Qwen3-VL runtime.

The prompt describes 2026 Form W-2 semantics and the canonical output shape
only. It must never include benchmark ground truth, expected values, or any
document-specific answers -- the same annotation-isolation rule
`docs/contracts/evaluation-plan.md` and `data/evaluation/README.md` apply to
Pipeline A applies here: the VLM runtime path must never see answers.
"""

from __future__ import annotations

import json

from PIL import Image

# Mirrors the substantive (non-metadata) shape of `w2_pipeline.contracts.w2.W2Document`.
# `metadata` and `field_observations` are deliberately excluded: metadata is
# operational (document_id, source filename) or fixed by this pipeline's
# scope (tax_year/schema_version 2026) rather than a visual observation, and
# `field_observations` is out of scope for this feasibility spike.
CANONICAL_JSON_SHAPE: dict = {
    "employee": {
        "ssn": None,
        "first_name": None,
        "middle_initial": None,
        "last_name": None,
        "suffix": None,
        "address": {
            "address_line_1": None,
            "address_line_2": None,
            "city": None,
            "state": None,
            "postal_code": None,
            "country": None,
        },
    },
    "employer": {
        "ein": None,
        "name": None,
        "address": {
            "address_line_1": None,
            "address_line_2": None,
            "city": None,
            "state": None,
            "postal_code": None,
            "country": None,
        },
        "control_number": None,
    },
    "federal_wages_and_taxes": {
        "box_1_wages_tips_other_compensation": None,
        "box_2_federal_income_tax_withheld": None,
        "box_3_social_security_wages": None,
        "box_4_social_security_tax_withheld": None,
        "box_5_medicare_wages_and_tips": None,
        "box_6_medicare_tax_withheld": None,
        "box_7_social_security_tips": None,
        "box_8_allocated_tips": None,
        "box_9_verification_code": None,
        "box_10_dependent_care_benefits": None,
        "box_11_nonqualified_plans": None,
    },
    "box_12_entries": [],
    "box_13": {
        "statutory_employee": False,
        "retirement_plan": False,
        "third_party_sick_pay": False,
    },
    "box_14_entries": [],
    "tipped_occupation_codes": [],
    "state_local_entries": [],
}

_SYSTEM_PROMPT_TEMPLATE = """You are a precise, careful information-extraction assistant reading an image of a single United States Form W-2, tax year 2026.

Your task is to transcribe ONLY the values visibly printed on THIS document image into a strict JSON object. Rules:

- Read only values that are actually visible on this document. Never infer, guess, calculate, or invent a value that is not visible.
- Use JSON `null` for any field that is blank, unreadable, or absent from this document.
- Preserve Unicode characters exactly as printed (accents, diacritics, other special characters) -- do not transliterate or normalize them.
- Box e shows the employee's name as three parts: "Employee's first name and initial", "Last name", and "Suff." (suffix). Split the first part into `first_name` and, only if a separate initial letter is shown, `middle_initial`. Keep `last_name` and `suffix` as their own independent values.
- Preserve SSN and EIN punctuation as printed (e.g. `123-45-6789` for SSN, `12-3456789` for EIN) when visible.
- Transcribe every monetary box exactly as printed, as a plain decimal string with no currency symbol and no thousands separator (e.g. `"1234.56"`, not `"$1,234.56"`), or `null` if the box is blank.
- Box 13 has three checkboxes: "Statutory employee", "Retirement plan", and "Third-party sick pay". Report each as a JSON boolean: `true` only if that specific box is visibly checked/marked, `false` otherwise (Box 13 flags are never `null`).
- Box 12 may show zero or more code/amount entries (e.g. "D 500.00"); report each as its own object with the one- or two-letter `code` and the `amount` decimal string.
- Box 14(a) may show zero or more free-form label/value entries; report each as its own object with a `label` and either an `amount` (decimal string) or `value` (free text), whichever the entry is. Box 14(b) may show zero or more Treasury tipped occupation codes; report each as its own `{{"code": "..."}}` object.
- Boxes 15-20 (state/local) may repeat for more than one state or locality; report each row as its own object.
- Return ONLY the JSON object below. No prose, no explanations, no markdown code fences, no text before or after the JSON.

Return exactly this JSON shape (use `null` for any missing/unreadable field, `[]` for a section with no entries, and keep every key present even when its value is `null`):

{schema_json}
"""


def build_extraction_prompt() -> str:
    """Return the static schema-guided extraction prompt text.

    Contains 2026 Form W-2 field semantics and the canonical output shape
    only -- no document-specific content, ground truth, or expected values.
    """

    return _SYSTEM_PROMPT_TEMPLATE.format(schema_json=json.dumps(CANONICAL_JSON_SHAPE, indent=2))


def build_chat_messages(image: Image.Image, prompt_text: str | None = None) -> list[dict]:
    """Build a single-turn Qwen3-VL chat message list for one page image."""

    text = prompt_text if prompt_text is not None else build_extraction_prompt()
    return [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": text},
            ],
        }
    ]
