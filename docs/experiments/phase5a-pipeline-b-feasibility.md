# Phase 5A - Pipeline B (Qwen3-VL) Feasibility Spike

This is the "what did we test and learn" record for Phase 5A, matching the
role `pipeline-a-extraction-history.md` plays for Pipeline A. Current status
and the next-step pointer live in `docs/project-state.md`; the architecture
contract lives in `docs/contracts/extraction-pipeline-b.md`.

## Goal

Establish whether `Qwen/Qwen3-VL-4B-Instruct` can take the same rendered W-2
page image Pipeline A's OCR route consumes and produce a canonical
`W2Document` through a genuinely different extraction architecture (a single
vision-language model call, no OCR, no deterministic parser). This is an
evidence-driven feasibility check, not a claim that Pipeline B wins or loses
against the Pipeline A incumbent.

## What Was Held Constant

- Source documents: the same external Symage clean-render (and, if the
  clean path worked, one degraded/rotated) documents already prepared under
  `data/evaluation/external/symage-synthetic-us-forms-preview/`.
- Canonical schema (`W2Document`), the evaluator/comparison logic, and
  ground truth -- entirely unchanged.
- Annotation isolation: Pipeline B receives only `ExtractionInput` (document
  path, document ID, source metadata, optional tax-year hint), the same
  boundary Pipeline A uses. No tokens, bounding boxes, NER tags, FUNSD/COCO/
  YOLO, or ground truth reach the extraction runtime.

## What Was Implemented

`src/w2_pipeline/extraction/pipeline_b/` -- see
`docs/contracts/extraction-pipeline-b.md` for the full architecture writeup.
Summary:

- `config.py` -- `PipelineBConfig` (model ID, device/dtype, default
  `"auto"`/`"auto"`), `describe_gpu_availability()` (model-free VRAM/CUDA
  diagnostic, mirrors `ocr_paddle.describe_paddle_gpu_availability()`).
- `image_prep.py` -- reuses `pdf_rendering.rendered_pdf_pages` (page
  rasterization only, no OCR) for PDFs; uses the ingested file directly for
  JPEG/PNG.
- `prompt.py` -- static schema-guided extraction prompt (2026 W-2 field
  semantics + the canonical output shape), no ground truth or
  document-specific content.
- `model_runtime.py` -- `QwenVlRuntime`, lazy `Qwen3VLForConditionalGeneration`
  + `AutoProcessor` load (cached per instance), single-image single-turn
  `generate()` under `torch.inference_mode()`.
- `response_parsing.py` -- strips a Markdown code fence, parses JSON, no
  OCR/regex repair of malformed output.
- `mapping.py` -- the only place canonical types are constructed; fills
  `W2Metadata` itself, defaults a missing `address` key, otherwise passes
  parsed sections straight to canonical Pydantic validation.
- `models.py` -- `PipelineBExtractionResult` (separate from Pipeline A's
  `ExtractionResult`; `route` is the plain string `"vlm"`, not
  `AcquisitionRoute`).
- `extractor.py` -- `PipelineBExtractor`, the same `extract_ingested`/
  `extract` two-method shape as `PipelineAExtractor`.
- `src/w2_pipeline/evaluation/run_pipeline_b.py` -- benchmark CLI mirroring
  `run_pipeline_a.py`'s shape (manifest/variant/limit filtering,
  `--output-json`, Markdown companion report), with `--model-id`/`--device`/
  `--dtype` in place of Pipeline A's OCR-backend flags.
- New `vlm` optional dependency group (`pyproject.toml`): `torch>=2.4,<3`,
  `transformers>=4.57,<5`, `accelerate>=1.0,<2`.

51 new focused unit tests (`tests/extraction/pipeline_b/`), covering prompt
construction/schema-shape alignment, JSON parsing (fenced/unfenced/invalid/
non-object/Unicode), canonical mapping (valid, missing-address-default,
empty-payload, Unicode, invalid Box 12 code length, missing Box 14
amount/value, extra unknown keys, non-boolean Box 13 value), image
preparation (PDF page-1 render, direct image passthrough, missing file,
corrupt PDF), GPU diagnostics (mocked `torch`, no real GPU required), model
runtime (mocked `transformers` classes -- no model download required),
extractor orchestration (mocked runtime), and structural/AST-based checks
that no Pipeline B module imports Pipeline A's OCR/parser modules. Full
project suite: 210 tests passing (159 baseline + 51 new), zero regressions.

## Environment Inspected Before Implementation

- GPU: NVIDIA GeForce RTX 3060, 12 GB VRAM, ~11.8 GB free at inspection
  time (`nvidia-smi`, confirmed again via `torch.cuda.mem_get_info`), driver
  610.43.02 -- the same reference machine Pipeline A's PaddleOCR GPU work
  used.
- `torch==2.14.0+cu130` installed from standard PyPI (no separate CUDA-index
  install step was needed, unlike PaddlePaddle's GPU distribution) and
  `transformers==4.57.6` confirmed to import
  `Qwen3VLForConditionalGeneration` natively -- no `trust_remote_code`,
  source-build, or `qwen-vl-utils` package needed.
- A 4B-parameter model in bf16 is roughly 8 GB of weights -- comfortably
  under the ~11.8 GB free VRAM, so no lower-memory/quantized configuration
  was attempted; `device="auto"`/`dtype="auto"` (the simplest viable
  configuration) was used as-is.

## Dependency Gaps Found And Fixed During The Smoke Test

The first smoke attempt failed on all 4 documents with `ModelLoadError`.
Direct single-document reproduction (bypassing the evaluator to get the
full traceback) found two missing/outdated runtime dependencies, neither a
code defect in Pipeline B itself:

1. **`torchvision` missing.** Qwen3-VL's `AutoProcessor.from_pretrained`
   resolves an `AutoVideoProcessor` component (the processor supports video
   input generically, even though Pipeline B only ever sends a still image)
   whose backend import requires `torchvision`. Added
   `torchvision>=0.19,<1` to the `vlm` optional dependency group; installed
   `torchvision==0.29.0` against the already-installed `torch==2.14.0`
   without conflict.
2. **System `jinja2` too old.** `processor.apply_chat_template` requires
   `jinja2>=3.1`; the reference machine's system Python has
   `Jinja2==3.0.3` (apt-managed, `/usr/lib/python3/dist-packages`).
   Installing `jinja2>=3.1,<4` to user site-packages
   (`~/.local/lib/python3.10/site-packages`) shadows the older system
   package for this user without touching or upgrading the apt package
   itself. Added to the `vlm` group.

After both fixes, a direct single-document reproduction succeeded end to
end and surfaced one more, smaller issue: the model returned
`state_local_entries` using simplified key names (e.g. `"state"`) instead
of the canonical `box_15_state`-style keys used everywhere else in its
otherwise-correct output. This is a JSON key rename, not a value
repair, so `mapping.py` gained a small alias-normalization step for exactly
that section (`_STATE_LOCAL_KEY_ALIASES`); 2 new tests
(`test_build_w2_document_normalizes_non_prefixed_state_local_keys`,
`..._accepts_already_canonical_state_local_keys`) cover it. Full suite:
212 tests passing (210 + 2), zero regressions.

## Smoke Test Results

Two runs, 5 documents total (within the Phase 5A 1-5 document scope),
against `data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl`,
default `device="auto"`/`dtype="auto"`:

```bash
python -m w2_pipeline.evaluation.run_pipeline_b <manifest> --variant-id external_clean_render --limit 4 --output-json data/evaluation/results/phase5a_pipeline_b_smoke_clean_4.json
python -m w2_pipeline.evaluation.run_pipeline_b <manifest> --variant-id rotated_png --limit 1 --output-json data/evaluation/results/phase5a_pipeline_b_smoke_rotated_1.json
```

**Clean render, 4 documents**
(`data/evaluation/results/phase5a_pipeline_b_smoke_clean_4.json`):

- 3/4 documents (`symage_900001`, `symage_900002`, `symage_900004`)
  succeeded with **`field_accuracy = 1.0`** each (69/69 correct fields
  combined) -- every evaluated field type (employee identity, SSN, EIN,
  all federal Boxes 1-11, Box 13's three flags, metadata) was exact.
- 1/4 (`symage_900003`) failed: `SchemaValidationError` --
  `Box12Entry.code` validation rejected `"12a"` (max 2 characters). The
  model transcribed the printed *line label* ("12a", the sub-row on Box 12)
  as the `code` value instead of the 1-2 letter code actually written on
  that line (e.g. `"D"`). This is a genuine model extraction ambiguity, not
  a parsing/mapping defect -- see "Known Limitations" below and in
  `docs/contracts/extraction-pipeline-b.md`.
- `average_duration_seconds: 58.42` (image prep + inference + parse +
  validate; model load is excluded after the first document since
  `QwenVlRuntime` caches the loaded model/processor for the life of the
  process).

**Rotated, 1 document**
(`data/evaluation/results/phase5a_pipeline_b_smoke_rotated_1.json`):

- 1/1 succeeded with `field_accuracy = 1.0` (23/23 correct fields),
  `duration_seconds: 70.20`.
- This is a single data point, not a robustness claim -- Pipeline A's
  known weakest variant is rotation (see `docs/project-state.md`), so this
  is only worth noting as "the basic path was not obviously broken by
  rotation," nothing stronger.

**Aggregate**: 4/5 documents fully succeeded with **100% field accuracy on
every one that succeeded** (92/92 correct fields across the 4 successes);
1/5 failed with a specific, understood, reproducible schema-validation
cause. `failed_or_unknown`/`vlm` route buckets in the JSON confirm the
evaluator correctly attributes successful predictions to the `"vlm"` route
(Pipeline B's `PipelineBExtractionResult.route`), not
Pipeline A's `AcquisitionRoute`.

**GPU/device**: NVIDIA GeForce RTX 3060, `device="auto"` resolved to a
single CUDA device, `dtype="auto"` (Transformers/Accelerate's own
resolution, not a manual bf16 override). Peak GPU utilization observed
during generation: ~98%, ~12 GB VRAM in use (of 12 GB total) -- comfortably
within budget but with little headroom; a batch size greater than 1 was
never attempted in Phase 5A.

## Answer To The Phase 5A Question

**"Can Qwen3-VL-4B-Instruct take our existing rendered W-2 image and
produce a valid canonical W2Document?"** Yes, demonstrably, on 4 of 5
smoke-tested documents, with perfect field accuracy on every document that
produced valid output. The one failure has a specific, understood cause
(a Box 12 line-label-vs-code ambiguity) rather than a systemic
architecture failure. This establishes feasibility; it says nothing yet
about accuracy, latency, or cost at scale relative to the Pipeline A
incumbent -- see "Known Limitations" and `docs/project-state.md`'s
Immediate Next Experiment pointer for what remains an open, un-run
question.

## Known Limitations

See `docs/contracts/extraction-pipeline-b.md`'s "Known Limitations"
section for the full list (no `field_observations`, no constrained
decoding, single-page only, no prompt optimization attempted, no
150/600-document benchmark run). Additionally, from this smoke test:

- **Box 12 code/line-label ambiguity**: on at least one document, the
  model returned the printed sub-row label ("12a") instead of the actual
  1-2 letter code for that Box 12 entry. Whether this recurs at scale, and
  whether a prompt clarification (out of scope for this spike) resolves
  it, is unknown from a single occurrence.
- **VRAM headroom is narrow at this dtype/model size**: ~12 GB of 12 GB
  total was in use during generation on the reference RTX 3060. A larger
  model, longer `max_new_tokens`, or concurrent batch processing would
  need explicit headroom analysis before being attempted.
