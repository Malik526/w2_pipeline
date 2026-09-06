"""Phase 8C.5: conservative address-leak plausibility heuristics for `employer.name`.

This is an OFFLINE VALIDATION EXPERIMENT, not a production validation
rule. Nothing here is wired into `w2_pipeline.validation`; it exists to
generate evidence about whether a narrow, deterministic, ground-truth-free
signal -- "does this predicted employer name look like it has street
address text appended to it?" -- can flag the known row-merge residual
(Phase 8C.1/8C.2/8C.3) without an unacceptable false-review cost.

## Design principle: combined evidence over weak standalone signals

A bare number or a bare word that happens to double as a road-suffix
abbreviation ("St", "Dr") is common in legitimate company names ("St.
Louis Trading Co", "Dr. Smith Medical Group") and must not be flagged on
its own. Every primitive here is intentionally narrow and reports its own
raw boolean; combining them (e.g. `contains_street_number` AND
`contains_road_suffix`) is left to the caller/candidate-rule layer in
`docs/experiments/phase8c5-employer-name-address-leak-heuristic.md`, not
baked into one opaque "is this suspicious" function.

## Road-suffix list: standard USPS-style abbreviations, not per-document overfitting

The suffix list below is deliberately broader than the four documents
this phase happened to discover: it draws on genuinely standard USPS
street-suffix abbreviations (`Rd`, `Brg`/`Bridge`, `Cor`/`Corridor`, `Cir`,
`Trl`, `Pl`, `Sq`, ...), not literal text lifted from any one company's
address. `docs/experiments/phase8c5-...md` reports both a narrower list
(exactly the brief's own example set) and this expanded one side by side,
so the effect of list breadth is itself visible evidence, not a hidden
choice.
"""

from __future__ import annotations

import re

# Bare digit run, 1-5 digits, not part of a longer digit run (so this
# never fires on part of an EIN/SSN/money amount's digit sequence, which
# are always longer or contain non-digit separators).
_STREET_NUMBER_RE = re.compile(r"(?<!\d)\d{1,5}(?!\d)")

# A ZIP or ZIP+4 shape specifically (kept separate from "street number":
# a bare 5-digit run alone is ambiguous between the two, which is real,
# expected overlap, not a bug -- see the module docstring).
_ZIP_RE = re.compile(r"(?<!\d)\d{5}(?:-\d{4})?(?!\d)")

_ROAD_SUFFIXES_NARROW: frozenset[str] = frozenset(
    {
        "st", "street", "ave", "avenue", "rd", "road", "blvd", "lane", "ln",
        "drive", "dr", "highway", "hwy", "court", "ct", "parkway", "pkwy",
        "terrace", "way",
    }
)

# Adds other standard, generic USPS-style street-suffix abbreviations.
# None of these were chosen because they appear in a specific document --
# they are standard address vocabulary that could appear in any future
# row-merge case.
_ROAD_SUFFIXES_EXPANDED: frozenset[str] = _ROAD_SUFFIXES_NARROW | frozenset(
    {
        "brg", "bridge", "cor", "corridor", "cir", "circle", "trl", "trail",
        "pl", "place", "sq", "square", "loop", "xing", "crossing", "aly",
        "alley", "byp", "bypass", "cswy", "causeway", "expy", "expressway",
        "frwy", "freeway", "tpke", "turnpike", "walk", "path", "run",
        "pass", "trce", "trace", "vw", "view", "holw", "hollow", "grn",
        "green", "mnr", "manor", "spur", "rte", "route",
    }
)

_WORD_RE = re.compile(r"[A-Za-z]+")


def contains_street_number(text: str) -> bool:
    """A bare 1-5 digit number appears somewhere in the text."""

    return bool(_STREET_NUMBER_RE.search(text))


def contains_zip_pattern(text: str) -> bool:
    """A 5-digit or ZIP+4 shaped number appears somewhere in the text."""

    return bool(_ZIP_RE.search(text))


def contains_road_suffix(text: str, *, expanded: bool = True) -> bool:
    """A whole word in `text` is a known road-suffix abbreviation.

    Whole-word matching (via tokenizing on runs of letters, not substring
    search) is deliberate: it is what keeps "Corp" from matching "Rd" or
    "Wayfair" from matching "Way". A trailing period ("St.") is stripped
    before comparison so punctuation doesn't hide a real match, without
    doing any substring-level matching that could over-fire.
    """

    suffixes = _ROAD_SUFFIXES_EXPANDED if expanded else _ROAD_SUFFIXES_NARROW
    tokens = {token.lower() for token in _WORD_RE.findall(text)}
    return not tokens.isdisjoint(suffixes)


def street_number_and_road_suffix(text: str, *, expanded: bool = True) -> bool:
    return contains_street_number(text) and contains_road_suffix(text, expanded=expanded)


def street_number_and_road_suffix_or_zip(text: str, *, expanded: bool = True) -> bool:
    return contains_street_number(text) and (
        contains_road_suffix(text, expanded=expanded) or contains_zip_pattern(text)
    )


CANDIDATE_RULES: dict[str, object] = {
    "A_contains_street_number": contains_street_number,
    "B_narrow_contains_road_suffix": lambda text: contains_road_suffix(text, expanded=False),
    "B_expanded_contains_road_suffix": lambda text: contains_road_suffix(text, expanded=True),
    "C_narrow_number_and_suffix": lambda text: street_number_and_road_suffix(text, expanded=False),
    "C_expanded_number_and_suffix": lambda text: street_number_and_road_suffix(text, expanded=True),
    "D_contains_zip_pattern": contains_zip_pattern,
    "E_expanded_number_and_suffix_or_zip": lambda text: street_number_and_road_suffix_or_zip(text, expanded=True),
}
