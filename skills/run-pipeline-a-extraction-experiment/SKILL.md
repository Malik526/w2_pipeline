---
name: run-pipeline-a-extraction-experiment
description: Use when the user asks to run, launch, or benchmark a Pipeline A OCR extraction experiment or configuration on the internal or external W-2 evaluation dataset — for example a named phase experiment ("Phase 4D.2"), a specific Tesseract PSM configuration, a smoke test with a document limit, or a full clean/robustness benchmark run. Not for Pipeline B, ingestion, schema, or evaluator implementation work.
---

# Run Pipeline A Extraction Experiment

Encodes the one safe, reproducible workflow for launching a Pipeline A
Tesseract OCR extraction benchmark run and recording its result. This skill
is Pipeline A-specific. Pipeline B does not exist yet and has no defined
execution workflow — do not generalize this skill to cover it.

Full contracts, if you need more than this skill provides:

- `docs/contracts/evaluation-plan.md` — benchmark/metric contract, isolation
  rules
- `docs/contracts/extraction-pipeline-a.md` — Pipeline A architecture, OCR
  configuration, benchmark commands
- `data/evaluation/README.md` — dataset preparation and long-running command
  patterns
- `docs/experiments/pipeline-a-extraction-history.md` — prior experiment
  results and conclusions (check before rerunning something already tested)
- `docs/project-state.md` — current incumbent configuration and the current
  phase/next-experiment pointer

## What never changes across an experiment

Only the OCR configuration (`--tesseract-psm`) and the dataset/variant/limit
selection may vary. Every run in this skill must otherwise hold constant:

- the canonical schema
- the deterministic parser (`parser_2026.py`)
- the evaluator/comparison logic
- ground truth
- the targeted supplemental PSM 6 SSN-recovery pass (it stays enabled for
  every main PSM — never disable it)
- annotation isolation: Pipeline A never receives tokens, bboxes, ner_tags,
  FUNSD/COCO/YOLO, or ground truth

Do not edit parser, evaluator, schema, or ground-truth code to "run an
experiment." If the user's request requires changing any of those, stop and
say this is no longer a Pipeline A configuration experiment — it needs its
own task.

## Step 1 — Translate the request into flags

Every experiment request maps to a `python -m w2_pipeline.evaluation.run_pipeline_a`
invocation. Work out each part before building the command:

**Main PSM** (`--tesseract-psm`): supported values are `3` (incumbent
default), `11`, and `12`. If the user names a phase (e.g. "Phase 4D.2"),
look up its defined PSM in `docs/experiments/pipeline-a-extraction-history.md`
or `docs/project-state.md` rather than guessing. If the user gives no PSM,
use the current incumbent from `docs/project-state.md` (default `3`).

**Dataset / manifest**:

| User says | Manifest | `--variant-id` |
|---|---|---|
| "clean benchmark", "clean render", "external clean", "150 clean" | `data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl` | `external_clean_render` |
| "all variants", "600 variants", "robustness", "full robustness set" | `data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl` | (omit — runs all variants) |
| "compressed" / "rotated" / "blurred" only | `data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl` | `compressed_jpeg` / `rotated_png` / `blurred_png` |
| "internal", "generated", "clean PDF" | `data/evaluation/generated/manifest.jsonl` | `clean_pdf` |
| unspecified | ask which dataset, unless a named phase in the experiment history already pins it |

Before running against the external manifest, confirm it exists:
`data/evaluation/external/symage-synthetic-us-forms-preview/manifest.jsonl`.
If missing, tell the user to prepare it first with
`python -m w2_pipeline.evaluation.prepare_external_dataset` rather than
silently running it yourself as part of an "experiment" ask.

**Smoke test / document count** (`--limit`): "N-document smoke test" ->
`--limit N`. No mention of a limit -> omit `--limit` (full variant scope).

**Output path**: always pass `--output-json`, never rely on stdout alone —
see naming rules below. Do not pass `--no-markdown-report`; the Markdown
companion is part of the standard artifact pair.

## Step 2 — Name the result artifact

Never overwrite an existing result file. Use `data/evaluation/results/` and
pick a `run_name`:

- If the request matches a defined phase/subphase (e.g. Phase 4D.2), use that
  phase's already-planned name if one is documented (check
  `docs/experiments/pipeline-a-extraction-history.md` first), e.g.
  `phase4d_psm12_external_clean_150`.
- Otherwise construct a descriptive ad hoc name:
  `adhoc_psm<N>_<variant-or-dataset>_<doc-count-or-full>_<YYYYMMDD_HHMM>`,
  e.g. `adhoc_psm11_external_clean_5docs_20260905_1410`.

Derive `.json`, `.md`, `.log`, `.pid` paths from that one `run_name` so the
whole artifact set stays matched.

## Step 3 — Decide foreground vs. background

Pipeline A OCR averages roughly 2 seconds/document. Use this to decide, and
err toward background if unsure:

- **Foreground (run directly, wait for it)**: `--limit` is small enough that
  the run should finish in well under ~2 minutes — roughly `--limit 30` or
  fewer against one variant. Good for smoke tests.
- **Background/detached (mandatory)**: a full clean-150 run, any full
  600-variant run, or anything else likely to exceed ~2 minutes. This follows
  the project's long-running command policy in `AGENTS.md` and
  `data/evaluation/README.md` — do not keep it running interactively while
  repeatedly polling.

Foreground command:

```bash
PYTHONPATH=src python3 -m w2_pipeline.evaluation.run_pipeline_a \
  <manifest-path> \
  [--variant-id <variant-id>] \
  [--limit <n>] \
  --tesseract-psm <psm> \
  --output-json data/evaluation/results/<run_name>.json
```

Background command (matches the pattern in `data/evaluation/README.md`):

```bash
run_name=<run_name>
setsid -f sh -c "trap '' HUP; echo \$\$ > data/evaluation/results/${run_name}.pid; \
  exec env PYTHONPATH=src python3 -m w2_pipeline.evaluation.run_pipeline_a \
  <manifest-path> \
  [--variant-id <variant-id>] \
  --tesseract-psm <psm> \
  --output-json data/evaluation/results/${run_name}.json \
  > data/evaluation/results/${run_name}.log 2>&1"
```

After launching a background run: report the command, the PID file path, the
log path, and the expected JSON/Markdown result paths, then stop. Do not poll
in a loop or repeat "still running" updates. Resume inspection only when the
user asks or in a later turn, using:

```bash
ps -p "$(cat data/evaluation/results/<run_name>.pid)" -o pid,etime,cmd
tail -n 80 data/evaluation/results/<run_name>.log
```

## Step 4 — After a run completes

1. Read the resulting `.json` (and generated `.md`) and confirm
   `failed_documents` / `field_accuracy` look sane before treating the run as
   valid.
2. Do not silently promote a new PSM to the incumbent default. Report the
   result and let the user decide; only change `docs/project-state.md`'s
   stated incumbent if the user explicitly says to adopt the new
   configuration.
3. Append an entry to `docs/experiments/pipeline-a-extraction-history.md`
   describing what was run, held constant, and concluded — this file is the
   "what did we test and learn" record, distinct from the changelog.
4. Update `docs/project-state.md` if the run changes current phase, the
   incumbent configuration, the authoritative benchmark numbers, known
   weaknesses, or the next-experiment pointer (see its maintenance policy).
5. Update `CHANGELOG.md` with a dated entry for the new benchmark artifacts.
6. Clean up run-control files once results are confirmed valid: remove the
   `.pid` file, and remove the `.log` file unless it holds a unique
   warning/error not already reflected in the JSON/Markdown — keep logs from
   failed runs for debugging. Never delete or overwrite a prior experiment's
   `.json`/`.md` artifacts.

## Hard boundaries

- Pipeline A only. Do not build or assume any Pipeline B runtime workflow.
- Never pass ground truth, tokens, bboxes, ner_tags, or FUNSD/COCO/YOLO
  annotations into the extractor — the CLI already enforces this; do not
  work around it.
- Never run this against real taxpayer W-2 data — internal generated or
  prepared external Symage synthetic manifests only.
- Do not change the parser, evaluator, or canonical schema as part of running
  an experiment.
