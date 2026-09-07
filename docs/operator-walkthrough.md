# Operator Walkthrough (Phase 8D.2)

A copy/paste runbook proving the current backend runs end-to-end exactly
as an operator would run it: ingestion -> extraction -> validation ->
accept/review -> correction -> revalidation -> finalization -> JSON/CSV
export. Every command below is a real, currently-supported command --
none were invented for this document. All example documents come from
the **synthetic** Symage evaluation dataset
(`data/evaluation/external/symage-synthetic-us-forms-preview-final/`);
no real taxpayer data is used anywhere in this walkthrough.

This is a demonstration of operability, not a new feature. See
[Known Limitations](#known-limitations) for everything this walkthrough
does *not* claim.

## Commands used

| Step | Command |
| --- | --- |
| Pipeline execution (extraction) | direct `PipelineAExtractor` API call -- see [Known Limitations](#known-limitations), no single-document CLI wrapper exists yet |
| Validation | `python -m w2_pipeline.review.cli validate` |
| Start review | `python -m w2_pipeline.review.cli review-create` |
| View pending review state | `cat <repo-dir>/<review_id>.json` (`FileReviewRepository` persists one file per review, named by review ID) |
| Apply a correction | `python -m w2_pipeline.review.cli review-correct` |
| Revalidate | `python -m w2_pipeline.review.cli review-revalidate` |
| Finalize + export JSON | `python -m w2_pipeline.review.cli export-document` (direct) / `export-review` (post-review) `--format json` |
| Export CSV | same commands, `--format csv` |

All `review/cli.py` commands are run with `PYTHONPATH=src` from the repo
root in this walkthrough; an installed package would not need it.

### The `--signals-json` flag (Phase 8D.2 fix)

`review/cli.py`'s `validate`, `review-create`, and `export-document`
commands originally only accepted `--pipeline-id`/`--route` as
`ExtractionSignals` inputs. Real `PipelineAExtractor` OCR-route
extractions also carry checkbox-detector and address-extraction evidence
(Phases 8C.12 / 8D.1B) that route-scoped validator rules require in order
to judge a document correctly. Without a way to supply that evidence, the
CLI could not faithfully validate a real OCR-route document: running
`validate --route ocr` on a perfectly-extracted document incorrectly
produced `needs_review` (`retirement_plan_checkbox_evidence_missing`)
purely because the CLI had nowhere to put the evidence that route's rules
need -- not because of any actual extraction defect. See
[Tests](#tests) for the root-cause fix.

`--signals-json <path>` loads a full `ExtractionSignals` JSON document
(as dumped from a real extraction) instead of only the bare
`--pipeline-id`/`--route` pair; explicit `--pipeline-id`/`--route` flags,
if also passed, override the corresponding fields loaded from the file.

## Path A: Happy Path

Document: `symage_900001-irs_w2_single_page_2026-p0` /
`external_clean_render` (synthetic). Expect: accepted, zero validation
issues, clean finalize + export.

**1. Pipeline execution (extraction).** No single-document extraction CLI
exists yet (see [Known Limitations](#known-limitations)); the documented
equivalent is a direct call to the same extractor class every benchmark
script in this project uses:

```python
from w2_pipeline.extraction.pipeline_a import PipelineAExtractor
from w2_pipeline.extraction.acquisition import ObservationAcquirer
from w2_pipeline.extraction.ocr_paddle import PaddleOcrAdapter, PaddleOcrConfig

extractor = PipelineAExtractor(
    observation_acquirer=ObservationAcquirer(
        ocr_adapter=PaddleOcrAdapter(config=PaddleOcrConfig(device="gpu"))
    )
)
ingested = extractor.ingestion_service.ingest(
    "path/to/document.png",
    document_id="symage_900001-irs_w2_single_page_2026-p0:external_clean_render",
)
result = extractor.extract_ingested(ingested)

# Write the two files the CLI commands below consume:
open("document.json", "w").write(result.document.model_dump_json(indent=2))

# ExtractionSignals mirrors ExtractionResult's evidence fields as
# primitives (see w2_pipeline.evaluation.run_address_evidence_validator_effectiveness._signals_for_result
# for the exact field-by-field mapping used to build this walkthrough's
# signals files).
```

**2. Validate.**

```bash
PYTHONPATH=src python3 -m w2_pipeline.review.cli validate document.json \
  --pipeline-id pipeline_a --route ocr --signals-json signals.json
```

Result: `"status": "accepted"`, `"issues": []`, `"checks_run": 16`.

**3. Export JSON and CSV** (no review needed -- goes straight to export):

```bash
PYTHONPATH=src python3 -m w2_pipeline.review.cli export-document document.json \
  --pipeline-id pipeline_a --route ocr --signals-json signals.json \
  --format json --output phase8d2_happy_path.json

PYTHONPATH=src python3 -m w2_pipeline.review.cli export-document document.json \
  --pipeline-id pipeline_a --route ocr --signals-json signals.json \
  --format csv --output phase8d2_happy_path.csv
```

Result: exits 0, both files written. `data/evaluation/results/phase8d2_happy_path.json`
and `.csv` are the actual output of these two commands.

Extracted values validated in this run: employer "Timberline Trading
Co." (EIN 75-5696876), employee "Steven D Armstrong", Box 12 `D /
7142.00`, Box 13 `retirement_plan = true`, state/local row NC /
35-6152316 / 114858.00 / 4339.59 -- all present with zero validation
issues.

## Path B: Review Path

Document: `symage_900021-irs_w2_single_page_2026-p0` / `rotated_png`
(synthetic). Expect: `needs_review` on both addresses, finalization
blocked, corrected via the real review workflow, then accepted and
exported.

**1. Pipeline execution + 2. Validate** (same two commands as Path A,
against the rotated-image variant):

```bash
PYTHONPATH=src python3 -m w2_pipeline.review.cli validate document.json \
  --pipeline-id pipeline_a --route ocr --signals-json signals.json
```

Result (`phase8d2_review_before.json`):

```json
{
  "status": "needs_review",
  "issues": [
    {
      "code": "employer_address_extraction_incomplete",
      "field_path": "employer.address.address_line_1",
      "severity": "error",
      "metadata": {"region_observation_count": 4}
    },
    {
      "code": "employee_address_extraction_incomplete",
      "field_path": "employee.address.address_line_1",
      "severity": "error",
      "metadata": {"region_observation_count": 3}
    }
  ]
}
```

Both addresses came back entirely `null` from OCR/parsing on the rotated
scan; the evidence-based validator rule (Phase 8D.1B) tells `needs_review`
apart from "this document has no address" because it saw real OCR
observations in the address region (4 and 3 respectively) that could not
be assembled into a complete address -- an incomplete extraction, not an
absent one.

**3. Prove finalization is blocked.** Attempting to export a
`needs_review` document fails, by design (`finalize_document` raises
`NotAcceptedError`):

```bash
PYTHONPATH=src python3 -m w2_pipeline.review.cli export-document document.json \
  --pipeline-id pipeline_a --route ocr --signals-json signals.json --format json
```

```
w2_pipeline.downstream.errors.NotAcceptedError: Cannot finalize a
document with validation status 'needs_review'; only 'accepted'
documents may become downstream output.
```

Exit code is non-zero. No file is written.

**4. Start review.**

```bash
PYTHONPATH=src python3 -m w2_pipeline.review.cli review-create document.json \
  --repo-dir data/review --pipeline-id pipeline_a --route ocr --signals-json signals.json
```

Prints the new `ReviewRecord` (`"status": "pending"`) and saves it to
`data/review/<review_id>.json`.

**5. View pending review state.** `FileReviewRepository` persists one
JSON file per review, named by review ID -- an operator can read it back
directly at any time without mutating it:

```bash
cat data/review/<review_id>.json
```

**6. Apply corrections.** One `review-correct` call per field, using the
generic dotted field-path convention (`w2_pipeline/review/field_paths.py`
-- no field allowlist; any path that resolves against `W2Document`'s own
structure works). Ten corrections in total (`address_line_2` is left
`null` for both -- the source document has no second address line):

```bash
PYTHONPATH=src python3 -m w2_pipeline.review.cli review-correct <review_id> \
  --repo-dir data/review --field-path employer.address.address_line_1 \
  --new-value '"288 E-470"' --reason "verified against source document"

PYTHONPATH=src python3 -m w2_pipeline.review.cli review-correct <review_id> \
  --repo-dir data/review --field-path employer.address.city \
  --new-value '"Grand Junction"' --reason "verified against source document"

PYTHONPATH=src python3 -m w2_pipeline.review.cli review-correct <review_id> \
  --repo-dir data/review --field-path employer.address.state \
  --new-value '"CO"' --reason "verified against source document"

PYTHONPATH=src python3 -m w2_pipeline.review.cli review-correct <review_id> \
  --repo-dir data/review --field-path employer.address.postal_code \
  --new-value '"81501"' --reason "verified against source document"

PYTHONPATH=src python3 -m w2_pipeline.review.cli review-correct <review_id> \
  --repo-dir data/review --field-path employer.address.country \
  --new-value '"US"' --reason "verified against source document"

PYTHONPATH=src python3 -m w2_pipeline.review.cli review-correct <review_id> \
  --repo-dir data/review --field-path employee.address.address_line_1 \
  --new-value '"9099 Zerex St"' --reason "verified against source document"

PYTHONPATH=src python3 -m w2_pipeline.review.cli review-correct <review_id> \
  --repo-dir data/review --field-path employee.address.city \
  --new-value '"Colorado Springs"' --reason "verified against source document"

PYTHONPATH=src python3 -m w2_pipeline.review.cli review-correct <review_id> \
  --repo-dir data/review --field-path employee.address.state \
  --new-value '"CO"' --reason "verified against source document"

PYTHONPATH=src python3 -m w2_pipeline.review.cli review-correct <review_id> \
  --repo-dir data/review --field-path employee.address.postal_code \
  --new-value '"80949"' --reason "verified against source document"

PYTHONPATH=src python3 -m w2_pipeline.review.cli review-correct <review_id> \
  --repo-dir data/review --field-path employee.address.country \
  --new-value '"US"' --reason "verified against source document"
```

Each call prints the updated record (`"status": "in_review"`) with its
growing `corrections` history and returns the file to disk after each
step -- there is exactly one on-disk copy of the record at all times, so
there is no split-brain between "what the CLI printed" and "what is
saved."

**7. Revalidate.**

```bash
PYTHONPATH=src python3 -m w2_pipeline.review.cli review-revalidate <review_id> \
  --repo-dir data/review
```

Result: `"status": "resolved"`,
`"revalidation_result": {"status": "accepted", "issues": []}`.

**8. Export JSON and CSV.**

```bash
PYTHONPATH=src python3 -m w2_pipeline.review.cli export-review <review_id> \
  --repo-dir data/review --format json --output phase8d2_review_after.json

PYTHONPATH=src python3 -m w2_pipeline.review.cli export-review <review_id> \
  --repo-dir data/review --format csv --output phase8d2_review_after.csv
```

Exit code 0. `data/evaluation/results/phase8d2_review_after.json` and
`.csv` are the actual output, with both corrected addresses present:

- Employer: 288 E-470, Grand Junction, CO 81501, US
- Employee: 9099 Zerex St, Colorado Springs, CO 80949, US

## Determinism

Each export command above was run twice against the same input; the
byte content of `phase8d2_happy_path.json`/`.csv` and
`phase8d2_review_after.json`/`.csv` was compared against a second,
independent run of the identical command. All four exports were
byte-identical across runs (see
`data/evaluation/results/phase8d2_walkthrough_summary.json`'s
`json_export_deterministic`/`csv_export_deterministic` fields, both
`true` for both paths).

## Known Limitations

These are pre-existing, already-documented limitations, restated here
rather than reopened:

- The benchmark this walkthrough draws its two documents from is
  **synthetic** (Symage-generated), not real taxpayer W-2s.
- Two residual unsafe-acceptance errors remain in the wider 600-document
  benchmark; both are OCR character-recognition substitutions (not
  address- or checkbox-related), and are not addressed by this phase.
- The expanded benchmark does not populate every optional canonical
  field (e.g. Box 14, local tax rows) on every document.
- Image-only/mixed-route vs. native-PDF evidence parity remains a known
  limitation, documented in earlier phases.
- There is no global calibrated OCR confidence score anywhere in this
  system (a deliberate Phase 8C.4 architectural decision) -- all
  evidence-based validator rules use structural signals (observation
  counts, row counts, detection method), never a confidence number.
- There is no batch export command; `export-document`/`export-review`
  operate on one document/review at a time.
- **No single-document pipeline-execution CLI exists.** Every existing
  script that calls `PipelineAExtractor` (`run_pipeline_a.py` and its
  variants) operates over a batch manifest, not one arbitrary input
  file with a `--output` flag. This walkthrough's "pipeline execution"
  step therefore documents the direct Python API call as the current
  equivalent rather than inventing a new CLI command, per this phase's
  scope. Building a single-document extraction CLI (mirroring
  `review/cli.py`'s `validate`/`export-document` ergonomics) would be a
  reasonable, separately-scoped follow-up.
- No frontend/operator GUI exists or is required for this system.

## Tests

**Root cause:** `review/cli.py`'s `_add_signal_flags`/`_load_document`
only ever constructed `ExtractionSignals(pipeline_id=..., route=...)`,
with no way to attach the checkbox-evidence / address-evidence /
employer-name-observation-count fields a real `pipeline_a` OCR-route
extraction actually produces. Any route-scoped validator rule that
depends on that evidence (Phase 8C.12's checkbox rule, Phase 8D.1B's
address rules) would therefore misfire when the CLI was driven with the
real `--route ocr` value and a genuinely well-extracted document,
reporting `needs_review` for a reason unrelated to the document's actual
extraction quality.

**Fix:** added an additive, backward-compatible `--signals-json <path>`
flag to `validate`, `review-create`, and `export-document` that loads a
full `ExtractionSignals` JSON document via
`ExtractionSignals.model_validate_json` and uses it as the base signals
object; explicit `--pipeline-id`/`--route` flags override the
corresponding fields when also passed. No existing behavior changed when
`--signals-json` is omitted.

**New tests** (`tests/review/test_cli.py`):
- `test_cli_route_ocr_without_signals_json_flags_missing_checkbox_evidence`
  -- documents the pre-fix gap still applies when no evidence is supplied.
- `test_cli_signals_json_supplies_full_route_evidence` -- confirms a
  document with full evidence supplied via `--signals-json` validates as
  accepted under `--route ocr`.
- `test_cli_signals_json_overridden_by_explicit_pipeline_flags` --
  confirms `--pipeline-id`/`--route` take precedence over the
  `--signals-json` file's values.

**Total:** 600 passed (597 baseline + 3 new).

## Artifacts

- `docs/operator-walkthrough.md` (this file)
- `data/evaluation/results/phase8d2_happy_path.json` / `.csv`
- `data/evaluation/results/phase8d2_review_before.json`
- `data/evaluation/results/phase8d2_review_after.json` / `.csv`
- `data/evaluation/results/phase8d2_walkthrough_summary.json`
