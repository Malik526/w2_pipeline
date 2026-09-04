# Evaluation Data

Phase 3 defines a reproducible synthetic evaluation dataset for offline
benchmarking. Internally generated assets are written under:

```text
data/evaluation/generated/
```

That directory is ignored by Git because the dataset can be recreated
deterministically.

Regenerate the initial benchmark with:

```bash
python -m w2_pipeline.evaluation.generate_dataset
```

The default command generates 12 semantic 2026 W-2 samples with five document
variants each:

- clean PDF
- clean PNG
- modest rotated PNG
- compressed JPEG
- modest blurred/lower-quality PNG

Each semantic sample has one canonical ground-truth JSON file serialized from
`W2Document`. Each document variant is linked to that ground truth in
`manifest.jsonl`.

Synthetic identifiers are generated solely for structural extraction testing
and must never be interpreted as real identities. The generator uses obvious
synthetic names, invalid placeholder-style SSNs and EINs, fake employer names,
and fake addresses. Real taxpayer W-2 data must not be committed.

The rendered documents are W-2-like development artifacts based on the 2026
field relationships. They are not official IRS forms and must not be described
as IRS-compliant printable W-2s. Keep authoritative blank IRS reference forms
under `docs/references/`, not in this directory.

## External Synthetic Benchmark

Phase 3B adds support for the Hugging Face dataset:

```text
Symage/synthetic-us-forms-preview
```

The adapter targets only:

```text
form_id = irs_w2_single_page_2026
```

Prepare the external benchmark locally with:

```bash
python3 -m pip install '.[external]'
python -m w2_pipeline.evaluation.prepare_external_dataset
```

The default loader uses Hugging Face `datasets` when available and can fall
back to pandas over the Hugging Face parquet URLs. To force the pandas path:

```bash
python -m w2_pipeline.evaluation.prepare_external_dataset --loader pandas
```

The prepared external benchmark is written under:

```text
data/evaluation/external/symage-synthetic-us-forms-preview/
```

That path is ignored by Git. Do not commit the downloaded/prepared external
dataset.

Inspected source metadata from the Hugging Face dataset card:

- dataset license: `cc-by-4.0`
- total rows: 525
- splits: `train` with 420 rows and `test` with 105 rows
- target W-2 subset: 150 `irs_w2_single_page_2026` documents
- image format: clean typed page renders, 300 DPI PNG
- columns: `id`, `identity_id`, `form_id`, `page`, `image`, `tokens`,
  `bboxes`, `ner_tags`, `funsd_json`, `coco_json`, `yolo_txt`,
  `num_entities`
- annotation formats: FUNSD, BIO token tags, COCO field-region annotations,
  and YOLO per-word annotations

Runtime loader notes:

- Hugging Face `datasets` yields `image` as a PIL PNG image, `tokens` /
  `bboxes` / `ner_tags` as lists, `funsd_json` as a JSON string decoding to a
  FUNSD entity list, `coco_json` as a JSON string decoding to a COCO object,
  and `yolo_txt` as text.
- pandas parquet loading yields `image` as a `{bytes, path}` dict, `tokens` /
  `bboxes` / `ner_tags` as ndarray-backed values, `funsd_json` as a JSON string
  decoding to a FUNSD entity list, `coco_json` as a JSON string decoding to a
  COCO object, and `yolo_txt` as text.

The external adapter treats the dataset image as the primary benchmark
document and classifies it as `external_clean_render`, not as a scan. Controlled
rotated, compressed, and degraded variants can be derived from that clean image
while retaining the same semantic ground truth.

## Benchmark Isolation

Primary end-to-end benchmark extractors must receive only image/document input
and production-realistic non-answer metadata. They must not receive
dataset-provided:

- `tokens`
- `bboxes`
- `ner_tags`
- `funsd_json`
- `coco_json`
- `yolo_txt`

Those fields are stored separately as evaluator-side annotations and are used
to construct or verify canonical ground truth. They may support a future
explicitly labeled `parser_isolation` or `oracle_layout` diagnostic, but those
results must not be reported as end-to-end extraction accuracy.

## Pipeline A Benchmarks

Run Pipeline A against internal generated clean PDFs:

```bash
python -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/generated/manifest.jsonl --variant-id clean_pdf --limit 5
```

Run Pipeline A against external Symage clean renders:

```bash
python -m w2_pipeline.evaluation.run_pipeline_a data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl --variant-id external_clean_render --limit 5
```

Pipeline A never receives external annotations. It receives only the document
path and production-realistic metadata through `ExtractionInput`.

Recorded Phase 4B Pipeline A result artifacts live in:

```text
data/evaluation/results/
```

The concise human-readable summary is:

```text
docs/results/phase4b-pipeline-a-benchmark.md
```

The committed external result artifacts record a completed 150-document clean
OCR benchmark and a completed 600-document clean/compressed/rotated/blurred OCR
robustness benchmark. The JSON files are the canonical machine-readable
benchmark records.
