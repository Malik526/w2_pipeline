# Phase 8C.5 - Employer Name Address-Leak Heuristic Experiment

Offline validation experiment: can a simple, deterministic,
ground-truth-free plausibility signal -- "does this predicted
`employer.name` look like it has street address text appended to it?" --
detect the known row-merge residual (Phase 8C.1/8C.2/8C.3/8C.4) without
an unacceptable false-review cost? Nothing here is wired into
`w2_pipeline.validation`; this is evidence only.

No OCR was rerun, no parser/checkbox/routing logic was touched, and the
frozen Phase 8C.2 prediction artifact was used exactly as saved.

## Method

New code:
- `src/w2_pipeline/evaluation/employer_name_heuristics.py` -- the
  detector primitives and candidate-rule registry.
- `src/w2_pipeline/evaluation/run_employer_name_heuristic_analysis.py` --
  runs every candidate against all 600 frozen Phase 8C.2 predictions.

**Leakage boundary**: for every one of the 600 saved `PredictionRecord`
entries, each candidate rule is evaluated against
`record.document.employer.name` alone (flagged / not flagged). Only
*after* that decision is ground truth (loaded from the manifest's own
`ground_truth_path`) consulted, purely to label whether the prediction
was actually correct. Enforced by construction: every candidate rule
function's signature takes exactly one argument (the text), verified
directly (`test_candidate_rules_take_only_the_predicted_text_no_ground_truth_parameter`)
-- there is no parameter through which ground truth could be threaded in.

Source artifacts (read only, not modified):
```text
data/evaluation/results/phase8c2_final_paddleocr_gpu_all_variants_600_predictions.jsonl
data/evaluation/external/symage-synthetic-us-forms-preview-final/manifest.jsonl
```

Output artifacts:
```text
data/evaluation/results/phase8c5_employer_name_address_leak.json
data/evaluation/results/phase8c5_employer_name_address_leak_rows.jsonl
```

## Candidate Detector Primitives

- `contains_street_number`: a bare 1-5 digit number appears anywhere in
  the text.
- `contains_road_suffix`: a whole word (tokenized on letter runs, not
  substring search -- this is what keeps "Corp" from matching "Rd" or
  "Wayfair" from matching "Way") is a known road-suffix abbreviation.
  Tested in two variants:
  - **narrow**: exactly the brief's own example list (`St`, `Street`,
    `Ave`, `Avenue`, `Rd`, `Road`, `Blvd`, `Lane`, `Ln`, `Drive`, `Dr`,
    `Highway`, `Hwy`, `Court`, `Ct`, `Parkway`, `Pkwy`, `Terrace`, `Way`).
  - **expanded**: adds other standard, generic USPS-style street-suffix
    abbreviations (`Brg`/`Bridge`, `Cor`/`Corridor`, `Cir`, `Trl`, `Pl`,
    `Sq`, `Loop`, and others) -- chosen because they are standard address
    vocabulary that could appear in *any* future row-merge case, not
    because they appear in these four specific documents. Nothing was
    hard-coded from any document ID or company name.
- `contains_zip_pattern`: a 5-digit or ZIP+4 shaped number.

Seven candidates were compared (Section 6 of the brief):

| Candidate | Rule |
|---|---|
| A | `contains_street_number` alone |
| B (narrow / expanded) | `contains_road_suffix` alone, each suffix-list variant |
| C (narrow / expanded) | `contains_street_number` AND `contains_road_suffix` |
| D | `contains_zip_pattern` alone |
| E | `contains_street_number` AND (`contains_road_suffix` (expanded) OR `contains_zip_pattern`) |

## Results

All 600 documents, 596 correct / 4 erroneous (the same 4 documents Phase
8C.2/8C.3/8C.4 already identified: `symage_900033`, `symage_900045`,
`symage_900082`, `symage_900146`, all `rotated_png`).

| Candidate | TP | FP | FN | TN | Recall | Precision | False-review rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| A: street number alone | 4 | 0 | 0 | 596 | 100.0% | 100.0% | 0.0% |
| B narrow: suffix alone | 2 | 0 | 2 | 596 | 50.0% | 100.0% | 0.0% |
| B expanded: suffix alone | 4 | 16 | 0 | 580 | 100.0% | 20.0% | 2.68% |
| **C narrow: number AND suffix** | 2 | 0 | 2 | 596 | 50.0% | 100.0% | 0.0% |
| **C expanded: number AND suffix** | **4** | **0** | **0** | **596** | **100.0%** | **100.0%** | **0.0%** |
| D: ZIP alone | 0 | 0 | 4 | 596 | 0.0% | undefined | 0.0% |
| E: number AND (suffix OR ZIP), expanded | 4 | 0 | 0 | 596 | 100.0% | 100.0% | 0.0% |

**Best-performing heuristic: C expanded (`contains_street_number AND
contains_road_suffix`, expanded suffix list).** Catches all 4 known
errors with **zero** false positives among the 596 correct employer
names -- perfect recall, perfect precision, 0% false-review rate on this
dataset. E is identical (ZIP never fires on any of the 4 real failures --
see below -- so the `OR contains_zip_pattern` term is inert here).

## 4 Known Failures, Inspected Individually

| Document | Predicted `employer.name` | Street number? | Narrow suffix? | Expanded suffix? | Caught by C-expanded? |
|---|---|---:|---:|---:|---:|
| symage_900033 | `Elan Consulting Corp 2861 Geneva Ponce De Leon Rd` | yes | yes (`Rd`) | yes (`Rd`) | **yes** |
| symage_900045 | `Bespoke Designs LLC 6878 Normandy Tullahoma Rd` | yes | yes (`Rd`) | yes (`Rd`) | **yes** |
| symage_900082 | `FutureReady Services 875 Francis Case Memorial Brg` | yes | **no** | yes (`Brg`) | **yes** |
| symage_900146 | `Global Insights Corp 4522 Eastern Transportation Corridor` | yes | **no** | yes (`Corridor`) | **yes** |

**No document ID or company name was hard-coded into the heuristic.**
The gap this table exposes is real and reported honestly: the *narrow*
suffix list (the brief's own literal example set) misses 2 of 4 --
`Brg` (Bridge) and `Corridor` are genuine, standard USPS street-type
abbreviations that simply were not in that example list. The *expanded*
list catches all 4 using only generic, standard address vocabulary, not
anything specific to these documents. `contains_zip_pattern` never fires
on any of the 4: the parser's row-merge defect (Phase 8C.1) only pulls in
the *first* address line (street), not the following city/state/ZIP
line -- confirmed directly, not assumed.

## False-Positive Analysis (Critical, Per The Brief)

**C expanded (the recommended candidate): zero false positives.** No
further analysis needed for it.

**B expanded (suffix alone, no number requirement): 16 false-positive
rows, 4 unique correct employer names (each appearing across all 4
dataset variants)**:

| Employer name | Suffix word that fired | Why it's a false positive |
|---|---|---|
| `Neon Path Consulting` | `Path` | Ordinary English word, not a street reference here |
| `Infinite Loop Technologies` | `Loop` | Ordinary English word (also a real tech-culture reference, not an address) |
| `Infinite Loop Solutions` | `Loop` | Same as above |
| `Pristine Green Technologies LLC` | `Green` | Ordinary English word, not a street reference here |

**Grouped cause**: all 4 false positives share one root cause -- the
*expanded* suffix list includes a handful of words (`Path`, `Loop`,
`Green`, and by the same logic `Way`, `Run`, `View`, `Court`, `Square`
are similarly risky) that are simultaneously (a) legitimate standard USPS
street-suffix abbreviations and (b) common, unremarkable words in
ordinary company names. This is not a coding bug; it is the exact
tradeoff the brief predicted narrow, single-signal rules would make.

**This is precisely why the combined rule (C) matters and was
specifically requested**: none of these 4 false-positive company names
also contain a bare street number, so requiring both signals together
eliminates all 16 false-positive rows while keeping all 4 true positives.
Two additional realistic ambiguous cases were tested directly (not found
in this dataset, but real and worth confirming defensively):
`"St. Louis Trading Co"` and `"Dr. Smith Medical Group"` -- both contain a
road-suffix word (`St`, `Dr`) and would false-positive under the
suffix-alone rule, but neither contains a street number, so the combined
rule correctly leaves both unflagged
(`test_ambiguous_suffix_words_do_not_fire_without_a_street_number`).

Also verified: whole-word matching prevents substring false positives
that a naive `in` check would produce -- `"Wayfair Inc"`, `"Roadrunner
Corp"`, `"Broadway Consulting"`, and `"Driftwood Partners"` all contain a
road-suffix word as a **substring** (`way`, `road`, `way`, `drift`+`wood`
is not actually a substring match here, but `way`/`road` are) yet none
are flagged, because suffix matching only ever compares whole tokens.

## Candidate-Rule Comparison Summary

- **A (street number alone) shows a deceptively perfect 100%/100%/0% on
  this dataset** -- but only because none of the 596 correct employer
  names in this specific synthetic dataset happen to contain any digit.
  The brief's own warning ("legitimate company names may contain
  numbers... `3M`, `7-Eleven`, `20th Century`, `1-800-...`") is real and
  independently confirmed here
  (`test_legitimate_numbers_in_company_names_handled_conservatively`):
  A alone is not a safe standalone signal in general, even though it
  scores perfectly on this particular dataset. Its perfect score is a
  property of this dataset's vocabulary, not evidence that bare-number
  matching is safe in general.
- **B (suffix alone) is the clearest demonstration of "weak standalone
  signal, real false-review cost"**: expanded-list recall matches C, but
  at a 20% precision / 2.68% false-review rate that a real review queue
  would not tolerate for this one signal alone.
- **C (combined) is the strongest candidate**: perfect separation on this
  dataset, and its safety is not a dataset-specific accident the way A's
  is -- it works by construction (a legitimate company name needs to
  independently look like both "has a bare number" and "has a road word"
  to be flagged, which is a materially rarer coincidence than either
  alone, and the tests above confirm it directly against several
  deliberately adversarial names).
- **D (ZIP alone) provides no value here**: the specific row-merge defect
  never pulls in a ZIP.

## Interpretation

**Is address-leak plausibility strong enough on its own?** For the
*specific* defect class Phase 8C.1-8C.4 already diagnosed (a name-plus-street-line
merge under large rotation skew), yes, on this evidence: the combined
rule (C expanded) achieves perfect recall and precision with zero false
reviews on the full 600-document frozen run. This is a genuinely
promising, narrowly-scoped signal -- **candidate A. Strong signal**, per
the brief's decision framework: it catches all known errors, at
negligible false-review cost, and is a reasonable candidate for future
production validation consideration (not a production change made in
this phase).

**Caveats that keep this from being an unconditional endorsement**:
- Evaluated against only 4 positive examples. A signal with 100%
  precision/recall on 4 cases is encouraging but is a small sample; it
  should not be read as "solved" until it is checked against a wider or
  future dataset, particularly one that might include a legitimate
  employer name containing both a number and a road-suffix word (none
  happened to exist in this 600-document set, but the possibility is not
  eliminated by this evidence).
- It is scoped to this exact defect shape (name + immediately-following
  street line). It would not catch a hypothetical future variant where
  only a city/state/ZIP line merges in without a street portion (no
  street number or road suffix to detect) -- `contains_zip_pattern` was
  included specifically to hedge that case, but never got to prove
  itself since it never fires on the actual 4 failures.
- The suffix list itself carries real, demonstrated risk when used alone
  (Section "False-Positive Analysis") -- it is only safe here in
  combination with the street-number requirement.

**Should it eventually be promoted into validation?** Not automatically,
and not in this phase (explicitly out of scope per the brief). It is a
reasonable candidate for a future, separately-scoped decision, ideally
validated against a larger and/or real-world employer-name corpus first,
and should ship as the *combined* rule only -- never the bare suffix rule
alone.

**Is the next layout-span experiment still necessary?** Yes. This
heuristic is a targeted plausibility check for one specific,
already-diagnosed defect shape (name + street-line merge); it says
nothing about detecting a different residual (e.g. a name merged with a
non-address neighboring line, or a partial/truncated name) and provides
no general layout-consistency signal. It complements, but does not
replace, a structural layout-span analysis.

## What Was Deliberately Not Done

- No production validation rule was added or changed.
- No OCR, parser, or checkbox logic was touched.
- No combined confidence/weighted score was created -- each candidate's
  raw recall/precision/false-review numbers are reported separately, per
  the brief's explicit instruction.
- The frozen Phase 8B/8C.2/8C.3/8C.4 artifacts were not modified.
- Document IDs and company names were not hard-coded into any rule; the
  expanded suffix list is standard, generic USPS-style vocabulary.

## Verification

26 new tests across `tests/evaluation/test_employer_name_heuristics.py`
(24 tests: whole-word boundary behavior, case-insensitivity, punctuation
handling, ZIP detection, the narrow-list gap, conservative handling of
legitimate numeric/ambiguous-suffix company names, and the no-ground-truth-parameter
structural safeguard) and
`tests/evaluation/test_run_employer_name_heuristic_analysis.py` (2 tests:
end-to-end confusion-matrix correctness and leakage-boundary behavior on
a small synthetic fixture, plus safe handling of a failed/`None`
extraction). Full suite: **431 tests passing (405 baseline + 26 new),
zero regressions.**
