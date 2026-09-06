# Phase 8A - Final Benchmark Coverage And Prediction Artifact Readiness

Preparation-only phase for the final Phase 8B/8C benchmark evidence pass.
**No 150/600-document OCR benchmark was run.** No Pipeline A/B extraction,
Phase 6 validation, or review behavior changed.

## Goal

1. Give `employer.name` an authoritative, deterministic, prediction-free
   ground-truth mapping in the Symage adapter.
2. Freeze the final evaluated field set and make it version-distinguishable
   from every historical benchmark.
3. Give the final benchmark runs a way to preserve complete per-document
   predictions, not just aggregate metrics/field failures.
4. Keep the benchmark/production boundary intact throughout.

## 1. `employer.name` Ground-Truth Mapping

`src/w2_pipeline/evaluation/external_symage.py`:

- `_map_scalar_field` now recognizes the normalized question `"employer s
  name ..."` (from the FUNSD question `Employer's name, address, and ZIP
  code`) and maps it to `employer.name`.
- `build_ground_truth`'s per-question loop gained a dedicated branch
  (parallel to the existing `employee.first_name` special case) that
  calls a new pure helper, `_first_line_of_combined_answer(answer: str) ->
  str | None`: splits the linked answer's text on `\n` and returns the
  first non-blank line, or `None` if the whole answer is blank.
- `employer.name` is only set, and only added to `evaluated_field_paths`,
  when that helper returns a real string -- a missing/blank/malformed
  answer is excluded from scoring for that record, never fabricated.
- `employer.address` (the second and third lines) is **not** mapped --
  explicitly out of scope; see "Explicitly Not Done" below.
- `employer.name` added to `_KNOWN_CANONICAL_PATHS` (the coverage-gap
  tracking set).
- `EXTERNAL_ADAPTER_VERSION` bumped `"symage-w2.phase3b.v1"` ->
  `"symage-w2.phase8a.v2"`, recorded in every
  `DatasetManifestEntry.generator_version` -- the mechanism that makes
  datasets/manifests prepared before and after this change structurally
  distinguishable.

**No extractor prediction or OCR output is consulted anywhere in this
path** -- `_first_line_of_combined_answer` takes only the raw FUNSD answer
string (confirmed by its signature and by a direct unit test that calls
it standalone, with no adapter/extractor/document object involved at
all).

## 2. Verification Against Real Documents

Regenerated a 5-document sample (not the full 150, not variants) into a
**new**, separate local directory,
`data/evaluation/external/symage-synthetic-us-forms-preview-final/`,
leaving the existing default-location dataset (used by every prior
phase's analysis) completely untouched:

```bash
python -m w2_pipeline.evaluation.prepare_external_dataset \
  --output-dir data/evaluation/external/symage-synthetic-us-forms-preview-final \
  --limit 5 --no-variants
```

For all 5 documents (`symage_900001`, `symage_900002`, `symage_900003`,
`symage_900004`, `symage_900006` -- the same 5 already used in the
Phase 6B investigation):

- New `employer.name` matches an **independently** re-derived expected
  value (parsed directly from the existing, untouched annotation files'
  raw FUNSD JSON in a separate script, not by calling the adapter code
  being verified) -- exact match on all 5:
  `Timberline Trading Co.`, `BlueWave Enterprises`,
  `Infinity Enterprises Inc.`, `Bright Horizons Corp`,
  `Evergreen Solutions LLC`. These are the same 5 values Phase 6B's real
  Pipeline A extraction independently confirmed.
- Every other ground-truth field is byte-identical between the old and
  new prepared documents for the same sample ID (`employer.name` is the
  only difference) -- confirmed by diffing the two ground-truth JSON
  objects with `employer.name` normalized out first.
- The new manifest's `generator_version` is `"symage-w2.phase8a.v2"`; the
  untouched old manifest's is still `"symage-w2.phase3b.v1"`.

## 3. Final Evaluated Field Set (Frozen)

24 canonical field paths (was 23): every field the Symage adapter already
scored, plus `employer.name`. (Verified by direct count against the
actual prepared manifest, not just the enumerated list below --
`len(entry.evaluated_field_paths)` is 24 on the new dataset and 23 on
the untouched old one, for the same document.)

```text
metadata.document_type, metadata.tax_year, metadata.schema_version
employee.ssn, employee.first_name, employee.middle_initial,
  employee.last_name, employee.suffix
employer.ein, employer.name, employer.control_number
federal_wages_and_taxes.box_1 .. box_8, box_10, box_11
  (box_9_verification_code is a known, pre-existing, unrelated coverage
  gap -- IRS instructions leave it blank; not addressed here)
box_13.statutory_employee, box_13.retirement_plan,
  box_13.third_party_sick_pay
```

`employer.address.*` is explicitly **not** in this frozen set (see below).
No other field was added or removed. The final Phase 8B/8C 600-document
benchmark must use exactly this set -- i.e., must be run against a
dataset prepared with `generator_version = "symage-w2.phase8a.v2"` (or
later), never the historical `"symage-w2.phase3b.v1"` dataset still
present at the default `prepare_external_dataset` output path.

## 4. Full-Prediction Artifact Readiness

New `src/w2_pipeline/evaluation/predictions.py`:

```python
class PredictionRecord(EvaluationModel):
    document_id: str
    variant_id: str
    pipeline_id: str
    status: str  # "success" | "extraction_failed" | "invalid_canonical_result"
    document: W2Document | None
    extraction_route: str | None
    duration_seconds: float | None
    message: str | None
    pipeline_metadata: dict[str, Any] | None
```

Written/read as JSONL (`write_prediction_records_jsonl`/
`load_prediction_records_jsonl`), matching this project's existing
`manifest.jsonl` convention for large per-document collections -- a
600-document final run would produce 600 lines, each a complete canonical
`W2Document` or an explicit failure record, never a reconstruction.

**No ground truth anywhere in a `PredictionRecord`** -- confirmed by a
direct schema-field test (`test_prediction_record_never_carries_ground_truth_fields`)
and, structurally, by `runner.py`'s new `predictions_out` parameter: it is
populated from exactly the same `predicted`/`raw_prediction` values the
existing scoring path already computed, never from `expected` (the
ground-truth document `_evaluate_entry` also loads for scoring). Passing
`predictions_out` does not extract a document twice -- the one extraction
call per entry now feeds both the existing `DocumentEvaluation` (for
aggregate scoring, unchanged) and, optionally, a `PredictionRecord` (new),
so a final 600-document run capturing full predictions costs no more
runtime than one that does not.

`run_pipeline_a.py`/`run_pipeline_b.py` both gained `--save-predictions
<path>`, backward compatible (omitting it changes nothing; existing
callers/tests are unaffected). Smoke-verified against 3 internally
generated documents (not the 600-document external set):

```bash
python -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/generated/manifest.jsonl --variant-id clean_pdf --limit 3 --save-predictions /tmp/preds_smoke.jsonl
```

produced exactly 3 JSONL lines, each with the complete predicted
`W2Document`, correct `status`, and no ground-truth field anywhere.

## 5. Benchmark/Production Boundary

New structural test, `tests/extraction/test_evaluation_boundary.py`: every
file under `src/w2_pipeline/extraction/` (including `pipeline_b/`) may
import only `w2_pipeline.evaluation.inputs` (the annotation-free
`ExtractionInput` contract Pipeline A/B already depended on before this
task) -- any other `w2_pipeline.evaluation` submodule import fails the
test. Confirms the pre-existing, already-correct boundary rather than
changing it. `tests/validation/test_isolation.py` and
`tests/review/test_dependency_isolation.py` (Phase 6/7) already forbid
`w2_pipeline.evaluation` entirely for `validation`/`review`/`downstream`,
unaffected by this task's changes to `w2_pipeline.evaluation` internals.

## Testing

17 new/updated tests:

- `tests/evaluation/test_external_symage.py` (+6): first-line mapping on
  the real combined answer text, address lines not mapped, multi-word
  name with punctuation, blank-answer non-fabrication, unlinked-question
  non-fabrication, the pure-function unit test, and the version/coverage
  distinguishability test.
- `tests/evaluation/test_predictions.py` (+5): schema shape (no
  ground-truth fields), JSONL round-trip, `evaluate_manifest` populating
  `predictions_out` on success and on extraction failure, and backward
  compatibility when `predictions_out` is omitted.
- `tests/extraction/test_evaluation_boundary.py` (+2): the
  extraction-package import boundary.

Full suite: **359 tests passing (346 baseline + 6 employer-name + 5
predictions + 2 boundary), zero regressions.**

## Explicitly Not Done

- `employer.address` extraction or ground-truth mapping -- both remain
  open, separate, already-documented gaps.
- No 150/600-document benchmark rerun of any kind.
- No historical result artifact or ground-truth file was modified; the
  default-location external dataset was left untouched. Historical
  accuracy numbers in `docs/architecture-decision-record.md` and
  `docs/project-state.md` still correctly describe a scope that excluded
  `employer.name` and are not rewritten.
- No change to Pipeline A, Pipeline B, or Phase 6 validation behavior.

## What Phase 8B Should Run Next

1. Prepare the full final external dataset (150 records, with variants),
   under a new, clearly-named directory so the historical dataset stays
   available for reference:
   ```bash
   python3 -m pip install '.[external]'
   python -m w2_pipeline.evaluation.prepare_external_dataset \
     --output-dir data/evaluation/external/symage-synthetic-us-forms-preview-final
   ```
2. Run the final PaddleOCR GPU and Tesseract CPU benchmarks against that
   new manifest, with `--save-predictions` to capture complete
   predictions for the later Phase 8C validator-effectiveness pass, e.g.:
   ```bash
   python -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/external/symage-synthetic-us-forms-preview-final/manifest.jsonl --ocr-backend paddleocr --paddle-device gpu --output-json data/evaluation/results/phase8b_paddleocr_gpu_final_clean_150.json --save-predictions data/evaluation/results/phase8b_paddleocr_gpu_final_clean_150_predictions.jsonl
   python -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/external/symage-synthetic-us-forms-preview-final/manifest.jsonl --output-json data/evaluation/results/phase8b_tesseract_final_clean_150.json --save-predictions data/evaluation/results/phase8b_tesseract_final_clean_150_predictions.jsonl
   ```
   (both per the project's long-running-command policy: background/
   detached, not run interactively).
3. These are 150-document (clean-render) runs; a full 600-document
   robustness rerun under the new field coverage is a separate, larger
   decision for the user, not implied by this list.
