# Phase 6 - Validation, Confidence Signals, And Human Review Routing

This is the "what did we test and learn" record for Phase 6, matching the
role `pipeline-a-extraction-history.md` and
`phase5a-pipeline-b-feasibility.md` play for the extraction pipelines.
Architecture/contract detail lives in
`docs/contracts/validation-and-routing.md`; current status lives in
`docs/project-state.md`.

## Goal

Implement a deterministic, explainable, backend-neutral validation layer
that judges an already-produced canonical `W2Document` -- using only the
canonical contract and its own rules, never ground truth -- and routes it
to `accepted` or `needs_review` with machine-readable reasons.

## What Was Implemented

`src/w2_pipeline/validation/` -- see
`docs/contracts/validation-and-routing.md` for full detail. Summary:

- `models.py` -- `ValidationSeverity` (info/warning/error),
  `ValidationStatus` (accepted/needs_review), `ExtractionOutcome`,
  `ExtractionSignals` (pipeline-agnostic quality metadata, deliberately no
  unified confidence score), `ValidationIssue`, `ValidationResult`.
- `redaction.py` -- SSN/EIN last-4-digit masking, full redaction for
  name/address fields, used wherever a rule would otherwise attach a raw
  PII value to an issue.
- `rules.py` -- 10 named rule functions: extraction signals, supported
  metadata (document type/tax year/schema version), employee identity
  required fields, SSN format, employer identity required fields, EIN
  format, core wage/tax fields required, monetary field validity
  (non-negative, <=2 decimal places), Box 12 code format, empty
  state/local entries.
- `routing.py` -- `RoutingPolicy`/`decide_status`, kept structurally
  separate from rule evaluation.
- `validator.py` -- `validate_w2_document`, the single backend-neutral
  entry point; handles the `document is None` (extraction produced nothing
  usable) case explicitly.
- `validate_w2.py` -- CLI, `python -m w2_pipeline.validation.validate_w2`.

56 new focused unit tests (`tests/validation/`): redaction (masking,
full-redaction, passthrough, sensitivity classification), rules (happy
path, each required-field/format/domain check, optional-field
non-triggering, multi-issue non-short-circuiting), routing (default vs.
conservative policy), validator (None-document handling, signal handling,
pipeline-metadata recording, backend-neutrality between Pipeline
A-shaped and Pipeline B-shaped signals), the CLI (valid/invalid/missing
file handling, flag plumbing), and structural AST-based isolation checks
(no `w2_pipeline.evaluation`/`w2_pipeline.extraction`/`w2_pipeline.ingestion`
import anywhere under `src/w2_pipeline/validation/`). Full suite: 268
tests passing (212 baseline + 56 new), zero regressions.

## Required-Field Decisions

See `docs/contracts/validation-and-routing.md`'s "Required-Field
Decisions" section for the full evidence trail. In short: required fields
were derived from `src/w2_pipeline/evaluation/synthetic.py`'s own
generation logic (which fields it always populates vs. conditionally
leaves `None`), not invented. Box 3/4 (Social Security wages/tax) were
deliberately left optional despite being "core" federal boxes, since the
generator itself models a real, legitimate exemption scenario for those
two fields specifically.

## Small Integration Verification

Per the brief, this used existing fixtures rather than running new
OCR/VLM inference:

1. **Known-good document, Pipeline-A-shaped signals**: the Phase 3
   synthetic generator's sample 1
   (`generate_synthetic_w2_documents()[0]`) validated with
   `ExtractionSignals(pipeline_id="pipeline_a", route="native_pdf")` ->
   `accepted`, zero issues.
2. **Known-good document, Pipeline-B-shaped signals**: the same document
   validated with `ExtractionSignals(pipeline_id="pipeline_b", route="vlm")`
   -> `accepted`, identical issue list (empty) -- confirming the validator
   does not branch on pipeline identity. A real Pipeline B canonical
   prediction was not readily available as a committed fixture (the Phase
   5A smoke-test JSON summaries record field-level comparisons, not the
   full predicted document) and re-running VLM inference just to produce
   one would violate the brief's "do NOT run inference merely to generate
   these" instruction, so this case relies on backend-neutrality-by-
   construction instead (enforced by `test_isolation.py` and the
   Pipeline-A/B-signal-equivalence test in `test_validator.py`).
3. **Intentionally corrupted document**: SSN/EIN replaced with garbage
   strings and a negative Box 1 value -> `needs_review`, with
   `invalid_ssn_format`, `invalid_ein_format`, and `invalid_money_value`
   all present.
4. **Intentionally missing critical fields**: SSN and last name both
   nulled -> `needs_review`, both `employee.ssn` and `employee.last_name`
   flagged as `required_field_missing`.

**Unplanned real-artifact finding.** While additionally running the CLI
against real, already-on-disk fixtures (not part of the committed test
suite, since these directories are gitignored/not guaranteed present in a
fresh clone) --
`data/evaluation/generated/ground_truth/w2_2026_0001.json` (internal
generator output) and
`data/evaluation/external/symage-synthetic-us-forms-preview/ground_truth/symage_900001-irs_w2_single_page_2026-p0.json`
(external Symage ground truth) -- the internal-generator artifact was
`accepted` with zero issues, but the Symage ground-truth artifact was
flagged `needs_review` for `employer.name` being `null`. Since that file
is *ground truth*, not a prediction, this first looked like a possible
ground-truth gap rather than an extraction problem. Checking further:

- The Symage manifest's `evaluated_field_paths` for that record does not
  include `employer.name` at all -- confirming the external adapter has
  never authoritatively mapped `employer.name` from the FUNSD annotations
  for Symage records, so ground truth is `null` there by construction, not
  by mistake.
- Running **actual Pipeline A extraction** (not ground truth) on the
  corresponding image
  (`symage_900001-irs_w2_single_page_2026-p0_external_clean_render.png`)
  also produced `employer.name = null` -- and the same held across 5
  documents checked (`symage_900001` through `symage_900006`, skipping
  `symage_900005`).

**Conclusion**: Pipeline A does not currently populate `employer.name` for
external Symage clean-render documents, and because this field has never
been in any Symage record's `evaluated_field_paths`, no benchmark result
reported anywhere in `docs/project-state.md` has ever measured or surfaced
this gap -- it has been invisible to every accuracy number reported to
date. Phase 6 validation caught it immediately, on the very first real
document checked, precisely because it does not depend on
`evaluated_field_paths` or any other ground-truth-scoping mechanism -- it
judges the document `W2Document` produced, not what a benchmark happened
to score. This is reported as a discovered issue, not fixed: changing
Pipeline A's extraction behavior is explicitly out of Phase 6's scope. A
future task should investigate why `_parse_employer` (`parser_2026.py`)
does not recover the employer name on these documents and whether
`employer.name` should be added to the Symage adapter's
`evaluated_field_paths` once a reliable ground-truth mapping exists.

## Rules Deliberately Not Implemented

- Any cross-field numeric relationship (e.g. Box 1 vs. Box 5, state wages
  vs. federal wages) -- no such rule is already documented in this
  project's contracts, and the brief explicitly directs against inventing
  one.
- Address field format/requiredness checks -- no existing project
  documentation calls out a specific address field as critical, and
  address formats vary too widely to check safely without inventing rules.
- A Box 12/14/tipped-code "known valid code list" check -- would require
  an authoritative IRS code list not currently present in this repository;
  adding one is future work, not invented here.
- Duplicate Box 12 entries (same code appearing twice) -- plausible in
  principle but not clearly documented as invalid, so left unimplemented
  rather than risk a false positive on a legitimately repeated code.

## Stop Condition

All Phase 6 completion criteria from the brief are met: a backend-neutral
validator exists, returns a typed `ValidationResult`, represents issues as
explainable codes, routes deterministically, does not flag legitimate
optional fields, has no ground-truth dependency (structurally enforced),
works identically regardless of which pipeline's signals are attached,
268 tests pass, integration verification passed (and surfaced one real,
out-of-scope-to-fix finding), and documentation/project state are updated.
