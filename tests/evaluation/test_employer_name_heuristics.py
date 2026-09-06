import inspect

import pytest

from w2_pipeline.evaluation.employer_name_heuristics import (
    CANDIDATE_RULES,
    contains_road_suffix,
    contains_street_number,
    contains_zip_pattern,
    street_number_and_road_suffix,
)

KNOWN_ROW_MERGE_FAILURES = [
    "Elan Consulting Corp 2861 Geneva Ponce De Leon Rd",
    "Bespoke Designs LLC 6878 Normandy Tullahoma Rd",
    "FutureReady Services 875 Francis Case Memorial Brg",
    "Global Insights Corp 4522 Eastern Transportation Corridor",
]

OBVIOUSLY_VALID_NAMES = [
    "Advantage Recruiting LLC",
    "BlueWave Enterprises",
    "Infinity Enterprises Inc.",
    "Timberline Trading Co.",
    "Evergreen Solutions LLC",
]


@pytest.mark.parametrize("name", OBVIOUSLY_VALID_NAMES)
def test_obviously_valid_employer_names_are_not_flagged_by_combined_rule(name: str) -> None:
    assert not street_number_and_road_suffix(name)


@pytest.mark.parametrize("name", KNOWN_ROW_MERGE_FAILURES)
def test_known_address_leak_shapes_are_flagged_by_combined_rule(name: str) -> None:
    assert street_number_and_road_suffix(name, expanded=True)


def test_narrow_suffix_list_misses_brg_and_corridor_shapes() -> None:
    """Documents the real gap the analysis found: the brief's literal
    example suffix list does not include every real USPS abbreviation, so
    it under-catches relative to the expanded list. Not a bug -- a
    measured tradeoff reported in the experiment doc."""

    assert not street_number_and_road_suffix(
        "FutureReady Services 875 Francis Case Memorial Brg", expanded=False
    )
    assert not street_number_and_road_suffix(
        "Global Insights Corp 4522 Eastern Transportation Corridor", expanded=False
    )


@pytest.mark.parametrize(
    "name",
    [
        "3M Corporation",
        "7-Eleven Inc.",
        "20th Century Solutions",
        "1-800 Accountants LLC",
    ],
)
def test_legitimate_numbers_in_company_names_handled_conservatively(name: str) -> None:
    """A bare number alone (candidate A) would flag every one of these --
    exactly the risk the brief warned about. The combined rule must not
    flag them, since none also contains a road-suffix word."""

    assert contains_street_number(name)
    assert not street_number_and_road_suffix(name)


@pytest.mark.parametrize(
    "name",
    [
        "Wayfair Inc",
        "Roadrunner Corp",
        "Broadway Consulting",
        "Driftwood Partners",
    ],
)
def test_road_suffix_matching_uses_whole_word_boundaries(name: str) -> None:
    """None of these contain a road-suffix word on its own -- "way" is
    inside "Wayfair", "road" is inside "Roadrunner", etc. Substring
    matching would wrongly fire on all of them; whole-word matching must
    not."""

    assert not contains_road_suffix(name)


@pytest.mark.parametrize(
    "name",
    [
        "St. Louis Trading Co",
        "Dr. Smith Medical Group",
    ],
)
def test_ambiguous_suffix_words_do_not_fire_without_a_street_number(name: str) -> None:
    """"St" (Saint) and "Dr" (Doctor) are real, common, legitimate uses
    that happen to collide with road-suffix abbreviations -- exactly why
    the combined rule (requiring a street number too) exists. The bare
    suffix rule alone DOES fire on these (documented, expected weakness of
    using it standalone); the combined rule must not."""

    assert contains_road_suffix(name)
    assert not street_number_and_road_suffix(name)


def test_zip_pattern_detects_five_digit_and_zip_plus_four() -> None:
    assert contains_zip_pattern("Springfield, IL 62704")
    assert contains_zip_pattern("Springfield, IL 62704-1234")
    assert not contains_zip_pattern("Timberline Trading Co.")


def test_road_suffix_matching_is_case_insensitive() -> None:
    assert contains_road_suffix("123 Main RD")
    assert contains_road_suffix("123 main rd")
    assert contains_road_suffix("123 Main Rd")


def test_road_suffix_matching_handles_trailing_punctuation() -> None:
    assert contains_road_suffix("123 Main St.")
    assert contains_road_suffix("123 Main St,")


def test_candidate_rules_take_only_the_predicted_text_no_ground_truth_parameter() -> None:
    """Structural safeguard against ground-truth leakage: every candidate
    rule's signature accepts exactly the text to test, nothing else -- so
    there is no parameter through which ground truth could ever be
    threaded into a flagging decision."""

    for name, rule in CANDIDATE_RULES.items():
        signature = inspect.signature(rule)
        required_params = [
            parameter
            for parameter in signature.parameters.values()
            if parameter.default is inspect.Parameter.empty
        ]
        assert len(required_params) == 1, f"{name} does not take exactly one required argument"
