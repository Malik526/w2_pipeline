# Phase 7 - Human Review Workflow And Downstream Output

Implementation record for Phase 7, matching the role the other
`docs/experiments/*.md` files play. Full architecture:
`docs/contracts/review-and-downstream-output.md`.

## Goal

Formalize what happens after Phase 6's `accepted`/`needs_review`
decision: pass accepted documents to downstream output directly, and give
`needs_review` documents a durable, auditable path through human
correction and revalidation back to `accepted`.

## What Was Implemented

`src/w2_pipeline/review/` and `src/w2_pipeline/downstream/` -- see the
contract doc for full detail. Summary:

- `review/models.py` -- `ReviewStatus`, `Correction`, `ReviewRecord`
  (immutable `original_document`, append-only `corrections`, both
  pre-review and post-correction `ValidationResult`s preserved).
- `review/field_paths.py` -- `get_field`/`set_field_value`, safe by-path
  read/write against the canonical schema's own structure (an unknown
  path is structurally impossible to satisfy, given `extra="forbid"`).
- `review/transitions.py` -- `transition_review`, a small explicit state
  machine (`pending -> in_review -> resolved`, `resolved` terminal).
- `review/workflow.py` -- `start_review`/`apply_correction`/`revalidate`,
  orchestrating the above; `revalidate` calls the unmodified Phase 6
  `validate_w2_document` directly.
- `review/repository.py` -- `ReviewRepository` protocol +
  `FileReviewRepository` (one JSON file per record, named by review ID
  only).
- `review/cli.py` -- one orchestrating CLI covering both flows end to end.
- `downstream/models.py`, `finalize.py` -- `FinalizedW2` +
  `finalize_document`, the single enforcement point for "only accepted
  documents reach downstream output."
- `downstream/json_output.py`, `csv_output.py`, `adapter.py` -- the two
  shipped output adapters plus a `Protocol` documenting the extension
  boundary for future adapters (database, tax software, REST API,
  webhook, accounting platform -- none implemented).
- New `data/review/` directory (gitignored, `README.md` added) for
  `FileReviewRepository`'s default location, matching the existing
  `data/documents/` PII-handling convention.

65 new tests (`tests/review/`, `tests/downstream/`): field-path get/set
(scalars, indexed lists, Unicode, null, unknown-path rejection,
invalid-value rejection), state transitions (every legal/illegal edge),
workflow orchestration (creation, correction, multi-correction,
revalidation in both directions, the full Flow B end to end), repository
round-tripping and PII-safe filenames, structural AST-based isolation
checks (no `w2_pipeline.evaluation`/`w2_pipeline.extraction` dependency),
`FinalizedW2` gating, both output adapters (Unicode, repeated-structure
JSON-encoding, empty lists, `Protocol` conformance), and the CLI driving
both flows end to end. Full suite: **340 tests passing (275 baseline +
65 new), zero regressions.**

## Integration Verification

Both required flows are committed tests, not just manually run once:

**Flow A (accepted)**:
`tests/downstream/test_finalize.py::test_finalize_accepted_document` --
a known-good synthetic document validates `accepted` and finalizes
directly; `tests/review/test_workflow.py`'s
`test_start_review_rejects_accepted_result` additionally confirms the
review workflow refuses to create a record for it at all.

**Flow B (review)**:
`tests/review/test_workflow.py::test_full_flow_b_end_to_end` and, driven
entirely through the CLI, `tests/review/test_cli.py::test_cli_full_review_flow`
-- a document missing `employee.ssn` validates `needs_review`; a
`ReviewRecord` is created (`pending`); a correction is applied
(`employee.ssn -> "123-45-6789"`, transitioning to `in_review`);
revalidation succeeds (transitioning to `resolved`); the corrected
document exports cleanly with the new SSN present. Both tests diff the
original and corrected document and confirm only the corrected field
changed.

Manually re-ran both flows directly through the CLI against a temporary
`data/review`-style directory during implementation (not committed, since
it used a scratch path) to confirm the demonstration commands in the
contract doc work exactly as documented, before writing the committed
CLI tests.

## Design Decisions Worth Recording

- **Revalidation uses fresh `ExtractionSignals`, not the original
  signals.** Once a human has corrected a document, the original
  extraction pipeline's reported outcome/warnings no longer describe what
  is being judged -- the corrected content is. Reusing the stale signals
  would have meant a document could never reach `resolved` if the
  original extraction had reported, say, `extraction_failed`, even after
  a human fixed every field by hand.
- **`apply_correction` always starts from `corrected_document or
  original_document`.** This makes corrections composable: a second
  correction builds on the first, rather than each correction re-deriving
  from the untouched original and losing prior fixes.
- **CSV chose JSON-string-encoding (option A) for repeated structures**,
  not separate related files (option B): a document's Box 12/14/state-
  local entry count varies per document, and one-row-per-document is the
  simplest invariant to keep stable across every document shape.
- **`resolved` has no reopen workflow.** Out of scope for this phase;
  flagged as a known limitation rather than guessed at.

## What Was Not Attempted (Explicitly Out Of Scope)

- Any frontend, authentication, or production database.
- Any new AI/LLM-based reviewer or auto-correction mechanism -- every
  correction in this phase is an explicit, human-supplied value.
- QuickBooks or any vendor-specific downstream integration.
- Reopening a `resolved` review record.
- Changes to Pipeline A, Pipeline B, or Phase 6 validation rules.
- Any 150/600-document extraction benchmark.
