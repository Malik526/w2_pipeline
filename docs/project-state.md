# Project State

Last updated: 2026-09-04

## Current Phase

Phase 4D is complete: both controlled Tesseract main page-segmentation-mode
experiments within Pipeline A have been run and documented. Phase 4D did not
introduce a new pipeline and did not change canonical schema, ground truth
semantics, parser logic, evaluator matching, or annotation isolation; only the
main Tesseract PSM was the experimental variable.

Most recently completed:

- Phase 4C corrected the Box e employee-name semantic error end to end (ground
  truth regeneration plus reruns) and reran both the 150-document external
  clean benchmark and the 600-document external robustness benchmark against
  the corrected semantics. Both reruns are complete and are now the
  authoritative external Pipeline A benchmark numbers.
- Phase 4D.1 evaluated main Tesseract PSM 11 (with the same targeted
  supplemental PSM 6 SSN recovery pass) against the 150-document external
  clean-render set and documented the result. PSM 11 was **not** promoted to
  the incumbent configuration: it improved several weak fields but caused a
  complete regression on federal Boxes 1 and 2.
- Phase 4D.2 evaluated main Tesseract PSM 12 (same supplemental PSM 6 pass)
  against the same 150-document external clean-render set. PSM 12 was **not**
  promoted to the incumbent configuration either: it was a severe, broad
  regression, zeroing employee first/last name, employee SSN, employer EIN,
  and all of federal Boxes 1-6 (overall field accuracy 50.49%, worse than
  PSM 11's 91.04%).

The current Pipeline A incumbent configuration remains unchanged from
Phase 4B: main Tesseract **PSM 3** plus the targeted supplemental **PSM 6**
SSN-recovery pass. Both Phase 4D PSM experiments confirmed it as the
strongest configuration evaluated to date.

Phase 0 established the domain contract, architecture contract, official
reference-form handling, data separation, and evaluation foundation. Phase 1
added the typed canonical W-2 contract that future extractors must produce.
Phase 2 added local source-file intake, SHA-256 file metadata, MIME/type
reconciliation, lightweight PyMuPDF PDF inspection, and JPEG/PNG readability
checks before extraction. Phase 3 added deterministic synthetic canonical W-2
generation, W-2-like document rendering, document variants, a JSONL manifest,
and a pipeline-independent field-accuracy evaluator. Phase 3B added an
external Hugging Face synthetic 2026 W-2 adapter and an explicit extraction
input boundary that prevents answer-bearing annotation leakage.
Phase 4 added the first deterministic extraction pipeline with common
text/layout observations, PyMuPDF native PDF acquisition, Tesseract OCR
fallback, deterministic 2026 W-2 parsing rules, route-aware benchmark
integration, and baseline benchmark commands. Phase 4B installed and exercised
the OCR route end to end, hardened Tesseract/parser behavior against external
W-2 images, added per-field benchmark reporting, and recorded external clean
and degraded benchmark result artifacts. Phase 4C corrected employee Box e
name semantics in both the extractor and the external ground truth, then
reran the clean and robustness external benchmarks. Phase 4D added configurable
main-PSM support to Pipeline A and the benchmark CLI, and Phase 4D.1 evaluated
PSM 11 as the first controlled sparse-text experiment.

## Authoritative Reference

The initial target is Form W-2, tax year 2026.

Reference PDF:

```text
docs/references/irs/2026_W2.pdf
```

Phase 1 used that PDF as the source of truth for the canonical W-2 field
inventory.

Canonical schema:

```text
src/w2_pipeline/contracts/w2.py
docs/contracts/canonical-w2-schema.md
```

Ingestion boundary:

```text
src/w2_pipeline/ingestion/
docs/contracts/ingestion-contract.md
```

Evaluation harness:

```text
src/w2_pipeline/evaluation/
docs/contracts/evaluation-plan.md
data/evaluation/README.md
```

Pipeline A:

```text
src/w2_pipeline/extraction/
docs/contracts/extraction-pipeline-a.md
```

Experiment narrative (what was tested and learned, as opposed to current
state):

```text
docs/experiments/pipeline-a-extraction-history.md
```

## Current Pipeline A Configuration

- Incumbent/default: main Tesseract **PSM 3** + targeted supplemental
  **PSM 6** (top identifier region, SSN recovery).
- Configurable experiment modes via `--tesseract-psm`: `3` (default), `11`,
  and `12`. The supplemental PSM 6 pass is always enabled regardless of the
  selected main PSM, so experiments isolate the main full-page segmentation
  mode only.
- PSM 11 was evaluated in Phase 4D.1 and rejected as a default: it zeroed
  federal Box 1 and Box 2 extraction on all 150 clean-render documents despite
  improving employee first name, employee middle initial, employer EIN, Box 13
  retirement-plan detection, and federal Boxes 3/5/6.
- PSM 12 was evaluated in Phase 4D.2 and rejected as a default: it produced a
  broad regression (50.49% field accuracy) that zeroed employee first name,
  employee last name, employee SSN, employer EIN, and all of federal Boxes
  1-6, worse overall than PSM 11.
- Both Phase 4D main-PSM experiments are complete; no further PSM values are
  currently planned for evaluation.

## Encoded Assumptions

- The working user is an accounting or tax-preparation firm processing W-2s
  supplied by individual tax clients.
- The only required initial production schema is 2026.
- The architecture is tax-year aware but does not implement multi-year support.
- Inputs are PDF, JPEG, and PNG.
- The system ends with validated canonical W-2 data suitable for downstream
  JSON or CSV output.
- RAG is excluded from core extraction architecture.
- Extraction pipelines are replaceable and must converge on one canonical
  representation.
- Evaluation uses common ground truth and reports by tax year where applicable.
- The Phase 3 evaluator compares canonical `W2Document` predictions to
  canonical ground truth, independent of OCR, vision models, regex extraction,
  or future pipeline internals.
- Phase 3 repeated-field comparison is deterministic and index-sensitive.
- The Phase 3B external benchmark source is kept distinct from the internal
  synthetic benchmark in manifest provenance.
- Primary end-to-end benchmark extractors receive only `ExtractionInput`; FUNSD,
  COCO, YOLO, token, bounding-box, and NER annotations remain evaluator-side.
- Pipeline A uses PyMuPDF native text for text PDFs and Tesseract OCR for image
  inputs or image-only PDF pages.
- Pipeline A's main full-page Tesseract PSM is configurable for controlled
  experiments. The default remains PSM 3, with PSM 11 and PSM 12 supported as
  Phase 4D experiment modes while targeted supplemental PSM 6 SSN recovery
  remains enabled. Phase 4D.1 and Phase 4D.2 both confirmed PSM 3 should
  remain the incumbent: PSM 11 caused a complete Box 1/Box 2 regression, and
  PSM 12 caused a broader regression across identity fields and Boxes 1-6.
- Tesseract is a system runtime dependency; when absent, OCR documents fail
  explicitly and benchmark failure isolation records the failure.
- In the completed Phase 4B benchmark environment, Tesseract was present and
  Pipeline A completed external OCR runs with 0 document failures. Phase 4C
  and Phase 4D.1 reruns also completed with 0 document failures.
- Pipeline A is strong on clean and compressed external W-2 images, degrades
  moderately under rotation, and degrades substantially under blur.
- Employee Box e `Employee's first name and initial` maps to
  `employee.first_name` plus `employee.middle_initial`; last name and suffix
  remain independent canonical fields. This correction is implemented in both
  the Symage ground-truth adapter and Pipeline A's OCR name-zone parsing, and
  the Phase 4C reruns are the first external benchmark numbers computed under
  the corrected semantics.
- Evaluation compares employee-name strings exactly. Accents are not folded or
  transliterated during field accuracy scoring.
- Confidence scores remain exploratory.
- Real taxpayer data must not be committed.

## Immediate Next Experiment

```text
Phase 4E - PaddleOCR alternate OCR backend within Pipeline A
```

Phase 4D's Tesseract main-PSM comparison is finished (PSM 3 incumbent
confirmed against both PSM 11 and PSM 12). The next planned experiment is
Phase 4E: evaluating PaddleOCR as an alternate OCR backend behind the same
common observation boundary, parser, canonical schema, and evaluator used by
the Tesseract-based configurations. Unlike the Phase 4D PSM experiments,
Phase 4E requires implementation work first (a PaddleOCR adapter conforming
to the existing `TextObservation` boundary) before a benchmark can be run; it
has not been started.

## Future Phases (after Phase 4E)

```text
Phase 5 - Pipeline B: Document Vision / Schema-Constrained Extraction
```

Phase 5 is a genuinely different document-vision/VLM architecture and should
implement a model-based challenger that produces the same canonical
`W2Document` and runs against the existing evaluator without changing ground
truth or exposing annotations. Phase 5 is compared against whichever Pipeline
A configuration performs best across Phase 4D/4E, not automatically against
the Phase 4B/4C PSM 3 baseline.

## Completed Phase History

Completed Phase 1 brief:

```text
docs/briefs/phase-1-canonical-w2-schema.md
```

The Phase 1 implementation created the Pydantic contract layer, package
structure, tests, and schema documentation without adding extraction, validation
engines, export, persistence, or UI.

Completed Phase 2 implementation:

```text
src/w2_pipeline/ingestion/
tests/ingestion/
docs/contracts/ingestion-contract.md
```

The Phase 2 implementation created the ingestion service, typed intake result,
explicit ingestion errors, PyMuPDF PDF inspection, image readability checks,
and tests without adding OCR, field extraction, tax-year inference, validation
engines, export, persistence, UI, or RAG.

Completed Phase 3 implementation:

```text
src/w2_pipeline/evaluation/
tests/evaluation/
data/evaluation/README.md
```

The Phase 3 implementation created deterministic synthetic 2026 W-2 semantic
samples, ground-truth serialization, W-2-like PDF/PNG/JPEG document rendering,
clean/rotated/compressed/blurred variants, JSONL manifest contracts, canonical
field flattening, field accuracy, explicit missing/mismatch/unexpected failure
classifications, extractor failure handling, invalid canonical result handling,
and latency capture support.

Completed Phase 3B implementation:

```text
src/w2_pipeline/evaluation/external_symage.py
src/w2_pipeline/evaluation/inputs.py
src/w2_pipeline/evaluation/prepare_external_dataset.py
tests/evaluation/test_external_symage.py
```

The Phase 3B implementation added a Symage Hugging Face adapter for
`Symage/synthetic-us-forms-preview`, filters records to
`irs_w2_single_page_2026`, stores answer-bearing annotations evaluator-side,
maps supported FUNSD key-value annotations into canonical `W2Document` ground
truth, records external provenance and evaluated field coverage in the
manifest, prepares external clean-render PNGs and derived variants, and keeps
extractor inputs isolated from tokens, bounding boxes, NER tags, FUNSD, COCO,
and YOLO annotations.

Completed Phase 4 implementation:

```text
src/w2_pipeline/extraction/
src/w2_pipeline/evaluation/run_pipeline_a.py
tests/extraction/
docs/contracts/extraction-pipeline-a.md
```

The Phase 4 implementation added route-aware common observations, native PDF
text acquisition, Tesseract OCR integration with explicit missing-runtime
errors, deterministic parsing for identity fields, federal boxes, Box 12, Box
13, Box 14a/14b, and state/local rows, Pipeline A evaluation integration, and a
benchmark CLI. It also corrected internal synthetic fixtures so 2026 generated
documents no longer invent Box 9 verification-code content.

Baseline on 2026-09-03:

- internal generated clean PDFs, first 5 documents: `field_accuracy = 1.0`,
  `failure_rate = 0.0`, route `native_pdf`

Completed Phase 4B benchmark hardening and results:

```text
src/w2_pipeline/extraction/ocr.py
src/w2_pipeline/extraction/parser_2026.py
src/w2_pipeline/evaluation/run_pipeline_a.py
src/w2_pipeline/evaluation/reporting.py
tests/extraction/
tests/evaluation/test_reporting.py
data/evaluation/results/
data/evaluation/results/phase4b_external_clean_150.md
```

The Phase 4B work changed Tesseract OCR to use full-page segmentation by
default, added a supplemental targeted OCR pass for the top identifier region,
added OCR word-row reconstruction, deterministic full-page geometry/zone
fallbacks for key 2026 W-2 fields, Box 13 layout detection, and per-field
benchmark summary output. The follow-up reporting layer added structured
field-failure serialization and same-base Markdown companion reports for saved
benchmark JSON results.

Phase 4B external results (historical; predate the Phase 4C Box e semantic
correction below and are superseded for any employee-name accuracy claim):

- external Symage clean renders, 150 documents: `field_accuracy =
  0.9887878787878788`, `failure_rate = 0.0`, average 2.223 seconds/document,
  route `ocr`, with 37 structured incorrect field records
- all prepared external variants, 600 documents: `field_accuracy =
  0.8926515151515152`, `failure_rate = 0.0`, average 2.131 seconds/document,
  route `ocr`
- variant accuracy: clean 98.88%, compressed JPEG 97.97%, rotated PNG 92.45%,
  blurred PNG 67.76%

Post-Phase 4B employee-name correction:

- Symage external ground truth now splits `Employee's first name and initial`
  into `employee.first_name` and `employee.middle_initial`.
- Pipeline A OCR Box e fallback now orders name-zone words left-to-right,
  splits trailing uppercase initials, and filters tiny one- to three-character
  OCR fragments only when normal-size neighboring name tokens are present.
- Benchmark reports now include metadata for run timestamp, source datasets,
  variant scope, schema version, Git commit, and OCR configuration.
- Historical Phase 4B result artifacts predate this semantic correction and
  should not be used for corrected Box e name-accuracy claims; the Phase 4C
  reruns below are the corrected numbers.

Completed Phase 4C corrected Box e benchmark reruns:

```text
data/evaluation/results/phase4c_external_clean_150_name_semantics.json
data/evaluation/results/phase4c_external_clean_150_name_semantics.md
data/evaluation/results/phase4c_external_all_variants_600_name_semantics.json
data/evaluation/results/phase4c_external_all_variants_600_name_semantics.md
```

These are the current authoritative external Pipeline A benchmark results
(main PSM 3 + supplemental PSM 6 incumbent, corrected Box e semantics):

- external Symage clean renders, 150 documents: `field_accuracy =
  0.991304347826087` (3,420 / 3,450 correct), `failed_documents = 0`, average
  2.0517181199200363 seconds/document. Employee Box e breakdown:
  `employee.first_name` 93.33%, `employee.middle_initial` 94.0%,
  `employee.last_name` 100%, `employee.suffix` 100%.
- all prepared external variants, 600 documents: `field_accuracy =
  0.8846376811594203` (12,208 / 13,800 correct), `failed_documents = 0`,
  average 2.1994630620232782 seconds/document.
- variant accuracy: clean render 99.13%, compressed JPEG 98.20%, rotated PNG
  89.45%, blurred PNG 67.07%.

The corrected numbers are lower than the Phase 4B pre-correction numbers
primarily because `employee.middle_initial` is now scored as its own field
path across every document/variant, not because extraction quality regressed.

Completed Phase 4D.1 PSM 11 experiment:

```text
data/evaluation/results/phase4d_psm11_external_clean_150.json
data/evaluation/results/phase4d_psm11_external_clean_150.md
```

Main PSM 11 + targeted supplemental PSM 6, same 150 external clean-render
documents, corrected ground truth:

- `field_accuracy = 0.9104347826086957` (3,141 / 3,450 correct),
  `failed_documents = 0`, average 2.1542158065199692 seconds/document.
- Improved fields versus the Phase 4C PSM 3 incumbent: `employee.first_name`
  98.0%, `employee.middle_initial` 99.33%, `employer.ein` 100.0%,
  `box_13.retirement_plan` 100.0%, and federal Boxes 3/5/6 at 100.0%.
- Regressed fields: federal `box_1_wages_tips_other_compensation` and
  `box_2_federal_income_tax_withheld` both dropped to `0 / 150` correct
  (complete extraction failure on every clean-render document).
- Conclusion: PSM 11 is not a viable replacement for the incumbent main PSM 3
  configuration despite its sparse-field gains. It remains useful diagnostic
  evidence but is not deployed as a default.

Completed Phase 4D.2 PSM 12 experiment:

```text
data/evaluation/results/phase4d_psm12_external_clean_150.json
data/evaluation/results/phase4d_psm12_external_clean_150.md
```

Main PSM 12 + targeted supplemental PSM 6, same 150 external clean-render
documents, corrected ground truth:

- `field_accuracy = 0.504927536231884` (1,742 / 3,450 correct),
  `failed_documents = 0`, average 2.3475697785066707 seconds/document,
  `field_failure_count = 1,708`.
- Zeroed fields (0 / 150 correct): `employee.first_name`,
  `employee.last_name`, `employee.ssn`, `employer.ein`, and all six of
  `federal_wages_and_taxes.box_1_wages_tips_other_compensation` through
  `box_6_medicare_tax_withheld`.
- Also degraded well below the incumbent: `employee.middle_initial` (21.3%)
  and `box_13.retirement_plan` (40.0%).
- Only Box 7, Box 8, Box 13's other two flags, and non-financial metadata
  fields stayed fully correct.
- Conclusion: PSM 12 is not a viable Pipeline A configuration. Unlike PSM 11's
  narrow Box 1/2 regression, PSM 12 regressed broadly across identity and
  federal money fields with no offsetting gains, performing roughly half as
  well overall as the PSM 3 incumbent and worse than PSM 11 on every degraded
  field. Phase 4D's PSM comparison is complete; see "Immediate Next
  Experiment" for Phase 4E.

## Current Known Weaknesses

- Employee first name and middle initial remain the weakest fields under the
  incumbent PSM 3 + PSM 6 configuration (93.33% / 94.0% on the clean set).
- Box 13 retirement-plan checkbox detection remains a known weak field under
  the incumbent configuration.
- Employer EIN and employee SSN degrade under rotated/blurred variants.
- Blur is the dominant degradation case (67.07% aggregate field accuracy on
  the blurred variant); rotation is a moderate degradation case (89.45%).
- PSM 11 trades the above name/EIN/Box 13 weaknesses for a total loss of
  federal Boxes 1 and 2, so it is documented as a known failure mode rather
  than adopted.
- PSM 12 is a documented broad-failure mode: it trades none of the incumbent's
  weaknesses away and additionally zeroes federal Boxes 1-6, employee last
  name, and employer EIN, so it is rejected outright rather than considered a
  partial trade-off.

## Unimplemented Capabilities

- Phase 4E (PaddleOCR alternate OCR backend) has not been started.
- Phase 5 (Pipeline B document-vision/VLM challenger) has not been started.
- Review routing, confidence calibration, validation engines, persistence,
  FastAPI/API layer, frontend, CSV export, and cost tracking remain
  unimplemented future-phase work.

## Open Issues

- Review routing, confidence calibration, additional OCR optimization, model extraction,
  validation engines, persistence, frontend, export, and cost tracking remain
  unimplemented future-phase work.
