# Known Limitations

The single canonical list of what this system does **not** currently do,
as of Phase 8D.3 (final freeze), updated in Phase 8D.4 to mark item 6
resolved and in Phase 8D.5 to mark item 7 resolved, rather than silently
dropped. Every item below is either
restated from an earlier phase, newly identified during the Phase 8D.2
operator walkthrough, or marked resolved inline once a later phase
closed it. This document does not propose fixes -- see each item's
"Production follow-up" line for what a future phase would look like,
and `docs/final-decisions.md` for why the current tradeoff was accepted.

---

### 1. Benchmark is synthetic, not a real taxpayer corpus

**What it is**: every accuracy/validator number in this project
(`docs/final-evaluation-summary.md`) is measured against the Symage
synthetic W-2 dataset (`Symage/synthetic-us-forms-preview`), not real
filed W-2s.
**Impact**: real-world documents carry scanner noise, handwriting,
non-standard layouts, and damage patterns a synthetic generator does not
reproduce; production accuracy on real documents is unmeasured.
**Correctness-critical**: no -- it does not make any measured number
wrong, it bounds what the number can claim.
**Production follow-up**: benchmark against a real (properly consented,
access-controlled) W-2 sample before any production accuracy claim.

### 2. Two residual OCR character-recognition unsafe-acceptance errors

**What it is**: 2 of 600 benchmark documents (`symage_900027`/
`blurred_png`, `symage_900061`/`compressed_jpeg`) are accepted with a
wrong address field because PaddleOCR misread a character (e.g. "Ave"
read as "Áve") under blur/compression -- a plausible-looking wrong value,
not a missing one, so Phase 8D.1B's evidence-based address rule (which
looks for incomplete/missing extraction, not wrong-but-complete
extraction) does not catch it.
**Impact**: unsafe acceptance rate is 0.33% overall (2/600), not 0%.
**Correctness-critical**: yes, but narrow and already measured, not
hidden -- see `docs/final-evaluation-summary.md`.
**Production follow-up**: either a content-plausibility check (e.g.
flag non-ASCII characters in a printed US address) or a calibrated
OCR-confidence signal -- the latter is a boundary this project has
deliberately not crossed (Phase 8C.4; see `docs/final-decisions.md`).

### 3. Optional canonical fields without a populated benchmark example

**What it is**: `W2Document` supports fields the Symage dataset's
annotations never populate with a positive example -- e.g. `box_14_entries`,
`box_18-20` local tax rows, `address_line_2`, and `statutory_employee`/
`third_party_sick_pay` are schema-complete but only exercised as `false`/
absent, never as a true positive, in the benchmark.
**Impact**: these fields are implemented and structurally validated
(schema, format) but have no measured extraction-accuracy number.
**Correctness-critical**: no -- they are not claimed as benchmarked; see
the field-coverage table in `docs/final-evaluation-summary.md`.
**Production follow-up**: source or construct documents that actually
populate these fields before claiming accuracy on them.

### 4. Image-only / mixed-route OCR evidence parity

**What it is**: the evidence-based validator rules (checkbox, address)
are scoped to `route in ("ocr", "mixed")` and exempt `native_pdf`
deliberately -- native PDF text extraction has no OCR observations to
build evidence from, and needs its own (currently unbuilt) parity
mechanism.
**Impact**: a `native_pdf`-route document with an incomplete address or
checkbox extraction is not caught by these two rules today.
**Correctness-critical**: no -- documented since Phase 8D.1B; the
`native_pdf` route already has a different, working extraction mechanism
(direct text layer, not OCR), just not yet its own dedicated evidence
signal.
**Production follow-up**: build a `native_pdf`-specific evidence signal
(e.g. based on native PDF text-layer completeness) mirroring the OCR
evidence pattern.

### 5. No global calibrated OCR confidence

**What it is**: a deliberate Phase 8C.4 architectural decision -- no
validator rule anywhere in this system uses a single collapsed
OCR-confidence score as a decision input. Evidence-based rules use
structural signals (observation counts, row counts, detection method)
instead.
**Impact**: some real, low-quality-scan errors that a confidence score
might catch are outside this design's reach (see limitation 2).
**Correctness-critical**: no -- a considered tradeoff, not an oversight;
Tesseract and PaddleOCR have no comparable confidence semantics, and
Phase 8C.4 found native confidence uninformative for this document type.
**Production follow-up**: none planned; would require re-litigating the
Phase 8C.4 decision with new evidence.

### 6. ~~No single-document pipeline-execution CLI~~ RESOLVED (Phase 8D.4)

**What it was**: every script that runs `PipelineAExtractor`
(`run_pipeline_a.py` and its variants) operates over a batch manifest,
not one arbitrary input file with a `--output` flag. The Phase 8D.2
operator walkthrough documented a direct Python API call
(`PipelineAExtractor.extract_ingested`) as the then-current equivalent
for "extract this one document."
**Resolved by**: `python -m w2_pipeline.cli.run_document <file>`
(`w2_pipeline.application.run_document.run_document()` is the reusable
service function behind it) -- ingests one file, extracts it, threads
the real extraction evidence into validation, and either finalizes +
exports or persists a review record, all in one command. See
[`docs/single-document-runner.md`](single-document-runner.md).
**Correctness-critical**: no -- was always purely an
operator-ergonomics gap; the underlying extraction is unchanged.

### 7. ~~No batch export command~~ RESOLVED (Phase 8D.5)

**What it was**: `review/cli.py`'s `export-document`/`export-review`
operate on one document/review at a time; there was no "run/export
every document in a directory" command, and every CLI invocation paid
OCR backend startup (PaddleOCR model loading) per file.
**Resolved by**: `python -m w2_pipeline.cli.run_batch <files...>`
(`w2_pipeline.application.run_batch.run_batch()` is the reusable
service function behind it) -- builds one Pipeline A extractor, warms
it up once, then runs every input file through the same production
workflow `run_document()` runs one file through, and writes an
accepted-only aggregate CSV plus a machine-readable
`batch_summary.json`. See [`docs/batch-runner.md`](batch-runner.md).
**Correctness-critical**: no -- was always purely an
operator-ergonomics/throughput gap; the underlying extraction,
validation, finalize, and export logic is unchanged and unduplicated.

### 8. No frontend / operator GUI

**What it is**: the entire review and downstream workflow is exposed
only via `review/cli.py` (a demonstration/operator CLI) and the
underlying Python API (`start_review`, `apply_correction`, `revalidate`,
`finalize_document`, `export_json`, `export_csv`). No web UI exists.
**Impact**: a non-technical reviewer cannot use this system directly
today.
**Correctness-critical**: no -- not required for this take-home's scope;
the backend workflow itself is complete and independently exercised via
the CLI (Phase 8D.2).
**Production follow-up**: a review front-end consuming the existing
`ReviewRecord`/`review.cli` API, as already noted in the architecture
decision record.

### 9. Benchmark and schema are scoped to the 2026 tax-year W-2

**What it is**: `W2Document.schema_version` and every parser/layout
constant target the 2026 IRS W-2 form. Other tax years or other form
types (W-2G, 1099s, etc.) are unsupported.
**Impact**: feeding a different form/year through this pipeline is
unvalidated and unsupported, not merely lower-accuracy.
**Correctness-critical**: no -- explicitly out of scope, not a defect.
**Production follow-up**: none planned within this project's current
scope; a broader document-type platform is a distinct, larger effort
(see the system boundary in `docs/final-architecture.md`).

---

## What is NOT a limitation (already fully closed)

For contrast, the following were open limitations in earlier phases and
are now closed, so they are intentionally absent from the list above:
`employer.name` rotation extraction (Phase 8C.1), `employer.name`
validation blind spot (Phase 8C.5-8C.8), `box_13.retirement_plan`
checkbox rotation robustness (Phase 8C.10-8C.12, anchor-relative
detector promoted to default), `employer.address`/`employee.address`
OCR-fallback and unsafe-acceptance gap (Phase 8D.1A/8D.1B), Box 12
blank-slot semantics ambiguity (Phase 8D.1B, confirmed as an IRS coded-
item contract, not a bug), the `review/cli.py` signal-threading gap
that made real OCR-route documents misvalidate through the CLI
(Phase 8D.2, fixed with `--signals-json`), and the lack of a
single-document pipeline-execution CLI (Phase 8D.4, resolved by
`w2_pipeline.cli.run_document`).
