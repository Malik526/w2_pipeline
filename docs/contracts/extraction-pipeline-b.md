# Pipeline B Extraction Contract

Phase 5A implements Pipeline B, the model-based challenger: a
vision-language model (VLM) reads a rendered W-2 page image directly and
returns structured JSON, with no OCR or deterministic parsing stage.

## Scope

Pipeline B starts after the same Phase 2 ingestion/rendering boundary
Pipeline A uses:

```text
IngestedDocument / ExtractionInput
-> render page 1 to an image (shared with Pipeline A's OCR image acquisition)
-> Qwen3-VL-4B-Instruct
-> parse raw text as JSON
-> validate as canonical W2Document
```

Phase 5A is a feasibility spike: implementation, focused/full unit tests,
and a 1-5 document smoke check. It does not include a 150- or 600-document
benchmark, prompt optimization, fine-tuning, or a Pipeline A/B promotion
decision. See `docs/project-state.md` for current status.

## Architecture Boundary

Pipeline B deliberately does not import or depend on any Pipeline A
extraction-logic module:

- `w2_pipeline.extraction.ocr` (Tesseract adapter)
- `w2_pipeline.extraction.ocr_paddle` (PaddleOCR adapter)
- `w2_pipeline.extraction.ocr_backend` (the shared `OcrAdapter` contract)
- `w2_pipeline.extraction.acquisition` (`ObservationAcquirer`)
- `w2_pipeline.extraction.parser_2026` (the deterministic regex/layout parser)
- `w2_pipeline.extraction.checkbox_vision` (Pipeline A's pixel-based Box 13
  detector)

The only module Pipeline B shares with Pipeline A is
`w2_pipeline.extraction.pdf_rendering` (`rendered_pdf_pages`), which is
plain PyMuPDF page rasterization -- turning a PDF page into a PNG -- with no
text extraction, OCR, or parsing involved. Both pipelines see the identical
rendered page image for a given PDF source document; this is the shared
experiment boundary the A/B comparison depends on. `tests/extraction/pipeline_b/`
includes AST-based import checks (`test_extractor.py`,
`test_extract_ingested`) and source-text checks (`test_prompt.py`,
`test_mapping.py`) that fail if any Pipeline B module starts importing
Pipeline A extraction logic.

Both pipelines converge on the same canonical `W2Document` contract
(`src/w2_pipeline/contracts/w2.py`) and are evaluated through the same
pipeline-independent evaluator (`src/w2_pipeline/evaluation/runner.py`,
`comparison.py`). Pipeline B has its own result wrapper,
`PipelineBExtractionResult`, rather than reusing Pipeline A's
`ExtractionResult`: Pipeline A's result types its `route` field as
`AcquisitionRoute` (`native_pdf`/`ocr`/`mixed`), an OCR-routing concept that
does not apply to a single VLM call. `PipelineBExtractionResult.route` is
the plain string `"vlm"`; the evaluator's `_coerce_prediction` accepts any
result object exposing a `.document`/`.route` shape, so this does not
require any evaluator change.

## Module Layout

```text
src/w2_pipeline/extraction/pipeline_b/
  config.py            PipelineBConfig, describe_gpu_availability()
  errors.py            ModelLoadError, ImagePreparationError,
                        VlmInferenceError, MalformedModelOutputError,
                        SchemaValidationError
  image_prep.py         prepare_page_image() -- reuses pdf_rendering only
  prompt.py             build_extraction_prompt(), build_chat_messages()
  model_runtime.py       QwenVlRuntime -- lazy model/processor load + generate()
  response_parsing.py    strip_code_fences(), parse_model_json()
  mapping.py             build_w2_document() -- parsed JSON -> W2Document
  models.py              PipelineBExtractionResult
  extractor.py           PipelineBExtractor -- orchestrates the above
```

`PipelineBExtractor` exposes the same two-method shape as
`PipelineAExtractor`:

```python
extract_ingested(ingested_document: IngestedDocument) -> PipelineBExtractionResult
extract(extraction_input: ExtractionInput) -> PipelineBExtractionResult
```

## Model

Primary model: `Qwen/Qwen3-VL-4B-Instruct`, loaded via Hugging Face
Transformers' native `Qwen3VLForConditionalGeneration` +
`AutoProcessor` (confirmed importable from `transformers==4.57.6`; no
`trust_remote_code` or separate `qwen-vl-utils` package is required with
this Transformers version).

`PipelineBConfig.device`/`dtype` default to `"auto"`, passed straight
through to `from_pretrained(dtype=..., device_map=...)` so
Transformers/Accelerate resolve actual placement -- the simplest viable
configuration, matching the Phase 5A instruction to prefer the simplest
config before any manual device/dtype tuning. Inference runs under
`torch.inference_mode()` (no gradient tracking); `model.eval()` is called
once at load. No fine-tuning code exists anywhere in this module.

`describe_gpu_availability()` (`config.py`) is a fast, model-free
diagnostic -- mirrors
`w2_pipeline.extraction.ocr_paddle.describe_paddle_gpu_availability()`'s
role for PaddleOCR -- reporting `torch.cuda.is_available()`,
`torch.cuda.get_device_name()`, and free/total VRAM via
`torch.cuda.mem_get_info()`. `QwenVlRuntime` records this once at model load
time (`gpu_diagnostics`) and reports it as part of every extraction result,
so VRAM/device state is always visible in benchmark output, not assumed.

**Reference development machine, inspected before implementation** (not
assumed): WSL2 on Windows, NVIDIA GeForce RTX 3060, 12 GB VRAM, ~11.8 GB
free at inspection time (`nvidia-smi` / `torch.cuda.mem_get_info`), driver
610.43.02. `torch==2.14.0+cu130` (CUDA 13 wheels; PyPI's default Linux
`torch` wheel bundles its own CUDA runtime, unlike PaddlePaddle's GPU
distribution, which needed a separate CUDA-specific package index) and
`transformers==4.57.6` were installed via the new `vlm` optional dependency
group. A 4B-parameter model in bf16 is roughly 8 GB of weights, comfortably
under the ~11.8 GB free at inspection time; no lower-memory (quantized)
configuration was needed for this spike.

## Dependency Group

```bash
pip install '.[vlm]'
```

```text
torch>=2.4,<3
torchvision>=0.19,<1
transformers>=4.57,<5
accelerate>=1.0,<2
jinja2>=3.1,<4
```

`torchvision` and `jinja2` were added after the first smoke attempt failed
with `ModelLoadError`/`VlmInferenceError`: Qwen3-VL's `AutoProcessor`
resolves an `AutoVideoProcessor` component that requires `torchvision`
even though Pipeline B only ever sends still images, and
`processor.apply_chat_template` requires `jinja2>=3.1` (the reference
machine's system Python has an older apt-managed `Jinja2==3.0.3`; installing
a newer `jinja2` to user site-packages shadows it without touching the
system package). See
`docs/experiments/phase5a-pipeline-b-feasibility.md` for the full
diagnosis.

If PyTorch/Transformers are not installed, `QwenVlRuntime.ensure_available()`
raises `ModelLoadError` pointing at this group, mirroring
`MissingOcrDependencyError`'s role for Pipeline A's OCR backends.

## Image Preparation

`image_prep.prepare_page_image()` is a context manager: for PDFs it renders
page 1 via `rendered_pdf_pages` (the temporary image is valid only inside
the `with` block, same contract as Pipeline A's OCR callers); for JPEG/PNG
sources it yields the already-ingested file path directly. Only page 1 is
ever rendered -- single-page W-2 is the only supported document shape,
matching the assumption already encoded in `checkbox_vision.py`.

## Prompt

`prompt.build_extraction_prompt()` returns a static prompt (no
document-specific content) describing:

- 2026 Form W-2 field semantics (Box e name-splitting, SSN/EIN punctuation,
  plain-decimal money formatting, Box 12/13/14/15-20 shapes)
- an explicit instruction to read only visible values, never infer/guess,
  use `null` for absent/unreadable fields, and preserve Unicode exactly
- the exact canonical JSON shape to return (`CANONICAL_JSON_SHAPE`), derived
  directly from the substantive (non-metadata) `W2Document` field names so
  the shape cannot drift from the canonical contract silently

The prompt never includes ground truth, expected values, ranges, or any
per-document content -- `tests/extraction/pipeline_b/test_prompt.py` asserts
this and cross-checks the schema shape's keys against the live canonical
Pydantic field names. `metadata` and `field_observations` are intentionally
excluded from the requested shape: metadata is operational
(`document_id`/`source_filename`) or fixed by this pipeline's scope
(tax_year/schema_version 2026), not a visual observation, and
`field_observations` is out of scope for this spike (see "Known
Limitations").

## Response Parsing

`response_parsing.parse_model_json()` strips a leading/trailing Markdown
code fence (```` ```json ... ``` ````) if present, then parses JSON. Anything
that is not valid JSON, or that parses to something other than a JSON
object, raises `MalformedModelOutputError`. This module never OCRs the
image, regex-extracts values from free text, or otherwise repairs a
malformed response -- doing so would blur Pipeline B's extraction boundary
with Pipeline A's deterministic parser and invalidate the architecture
comparison.

## Canonical Mapping

`mapping.build_w2_document()` is the only place Pipeline B constructs
canonical types. It:

- always constructs `W2Metadata` itself (document ID, source filename,
  fixed 2026 tax_year/schema_version) -- never reads these from the parsed
  JSON, even if present
- defaults an entirely-missing `address` key to `{}` (an all-null `Address`)
  for `employee`/`employer`, since those are the only required
  (no-default) nested fields on the canonical model that the VLM is asked
  to populate
- otherwise passes each section straight to the matching canonical Pydantic
  model's `model_validate()`, so a structurally invalid leaf value (wrong
  type, extra unexpected key, invalid Box 12 code length, a `Box14Entry`
  missing both `amount` and `value`) raises `pydantic.ValidationError`,
  wrapped as `SchemaValidationError` -- reported as a distinct diagnostic
  category, never silently coerced or repaired

## Error Categories

Pipeline B distinguishes, at minimum:

| Stage | Exception |
|---|---|
| `vlm` optional dependency missing / model repository load failure | `ModelLoadError` |
| Source document cannot be rendered/opened as a page image | `ImagePreparationError` |
| Model generation itself fails (OOM, runtime error) | `VlmInferenceError` |
| Raw response is not valid JSON / not a JSON object | `MalformedModelOutputError` |
| Parsed JSON fails canonical `W2Document` validation | `SchemaValidationError` |
| (none of the above) | successful extraction, `PipelineBExtractionResult` returned |

All five inherit from `PipelineBError`. None of the extractor's stages
swallow an exception silently; every raised error carries a diagnostic
message with no ground-truth content (there is none in the runtime path to
leak -- see "Evaluation Isolation").

## Timing And Device Metadata

`PipelineBExtractionResult` carries `duration_seconds` (one document's
image-prep + inference + parse + validate wall time),
`model_load_duration_seconds` (`None` after the first call in a process,
since `QwenVlRuntime` caches the loaded model/processor exactly once, the
same pattern `PaddleOcrAdapter._get_client` uses), `device`/`dtype` (the
resolved config values), and `gpu_diagnostics` (the `describe_gpu_availability()`
snapshot taken at load time).

## Evaluation Isolation

Pipeline B integrates with the same evaluator boundary as Pipeline A: its
`extract()` method receives only `ExtractionInput` (document path, document
ID, source metadata, optional tax-year hint) -- never dataset tokens,
bounding boxes, NER tags, FUNSD/COCO/YOLO annotations, or ground truth.
`tests/extraction/pipeline_b/test_extractor.py` asserts the extraction
prompt sent to the model never contains any ground-truth value from a
smoke-tested document (checked structurally, not just by convention).

## Benchmark Command

```bash
python -m w2_pipeline.evaluation.run_pipeline_b data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl --variant-id external_clean_render --limit 5
```

`--device`/`--dtype` (both default `auto`) and `--model-id` (default
`Qwen/Qwen3-VL-4B-Instruct`) are exposed for explicit overrides; Phase 5A
did not need to use them. Model download/load plus multi-document inference
routinely exceeds the project's 2-minute interactive threshold -- launch
in background per `AGENTS.md`'s long-running command policy, the same as a
PaddleOCR GPU benchmark run.

## Known Limitations (Phase 5A)

- `field_observations` is never populated by Pipeline B (always empty list);
  the prompt does not ask the model to distinguish `observed_blank` /
  `not_applicable` / `extraction_failed` field-level states, only a value or
  `null`.
- No structured/JSON-constrained decoding (e.g. grammar-constrained
  generation) is used -- the model is instructed via prompt to return JSON
  only, and output is parsed defensively. This is more failure-prone than
  constrained decoding would be; Phase 5A did not evaluate constrained
  decoding options.
- Only page 1 of a source document is ever rendered/sent to the model
  (single-page W-2 assumption, shared with the rest of this codebase).
- No prompt optimization, few-shot examples, or fine-tuning was attempted;
  the prompt is a first-pass schema-guided instruction only.
- No 150- or 600-document benchmark has been run; only a small (5
  document) smoke check (see `docs/experiments/phase5a-pipeline-b-feasibility.md`).
  Field-level accuracy trends should not be inferred from this sample size.
- **Box 12 code/line-label ambiguity, observed once in the smoke test**: the
  model returned the printed sub-row label (`"12a"`) as `Box12Entry.code`
  instead of the actual 1-2 letter code written on that line, failing
  canonical validation (`code` has `max_length=2`). Not patched around
  (that would require either a prompt change, out of scope for this spike,
  or value-level repair, explicitly disallowed) -- reported as a schema
  validation failure, exactly the outcome the error taxonomy above is for.
- **VRAM headroom is narrow at this dtype/model size**: the smoke test
  observed ~12 GB of the RTX 3060's 12 GB total in use during generation
  (`nvidia-smi` while a generation was in flight). A larger model, longer
  `max_new_tokens`, or concurrent/batched inference would need explicit
  headroom analysis first.

## Smoke Test Result (Phase 5A)

4 of 5 smoke-tested documents (3/4 clean + 1/1 rotated) produced a valid
canonical `W2Document` with **`field_accuracy = 1.0`** on every one that
succeeded (92/92 correct fields combined); the one failure is the Box 12
ambiguity above, a specific and understood cause, not a systemic failure.
Per-document duration: `58.42s` average across the 4 clean documents,
`70.20s` for the one rotated document (model load excluded after the first
call in a process). Full detail, including the two runtime-dependency
gaps found and fixed (`torchvision`, `jinja2`) before this result was
reached, is in `docs/experiments/phase5a-pipeline-b-feasibility.md`.
