# W-2 Pipeline Agent Instructions

This project follows the Thin Harness / Fat Skills pattern. Keep this file thin:
load only the project contract needed for the current task, then work inside
that narrower context.

## Required Global Policies

Before changing this project, follow the shared policies in:

- `/home/malik/.agents/CODING.md`
- `/home/malik/.agents/SECURITY.md`
- `/home/malik/.agents/GIT.md`
- `/home/malik/.agents/DOCUMENTATION.md`
- `/home/malik/.agents/VERIFICATION.md`

## Project Contracts

Use these deterministic project contracts as the authoritative project context:

- `README.md` for the project overview and current phase.
- `docs/contracts/system-contract.md` for product scope, system boundaries,
  supported inputs and outputs, tax-year posture, and non-goals.
- `docs/contracts/workflow-and-architecture.md` for lifecycle terminology,
  architecture, pipeline boundaries, and technology direction.
- `docs/contracts/evaluation-plan.md` for benchmark and metric contracts.
- `docs/contracts/canonical-w2-schema.md` for the Phase 1 canonical Pydantic
  schema contract.
- `docs/contracts/ingestion-contract.md` for the Phase 2 document ingestion
  boundary.
- `docs/contracts/extraction-pipeline-a.md` for the Pipeline A deterministic
  OCR/parser architecture.
- `docs/contracts/extraction-pipeline-b.md` for the Phase 5A Pipeline B
  vision-language-model architecture.
- `docs/contracts/validation-and-routing.md` for the Phase 6 validation and
  human-review-routing boundary.
- `docs/contracts/review-and-downstream-output.md` for the Phase 7 review
  workflow and downstream JSON/CSV output boundary.
- `docs/references/irs/README.md` for official IRS reference artifact handling.

## Skills

Use these project-local skills when the current task matches their scope:

- `skills/run-pipeline-a-extraction-experiment/SKILL.md` for running or
  benchmarking a Pipeline A OCR extraction configuration (named phase
  experiments, PSM configuration runs, smoke tests, or full clean/robustness
  benchmark runs). Pipeline A only.

## Scope Guard

The project has implemented Phase 0-4E: contracts, the canonical W-2 schema,
the ingestion boundary, the evaluation harness (internal and external Symage
benchmarks), Pipeline A (deterministic native-text/OCR extraction, including
configurable Tesseract PSM experiments and a PaddleOCR backend); Phase 5A
(Pipeline B: a Qwen3-VL-4B-Instruct vision-language extraction challenger,
feasibility-spike scope only -- see `docs/contracts/extraction-pipeline-b.md`);
Phase 6 (deterministic, backend-neutral validation and human-review
routing over an already-extracted canonical `W2Document` -- see
`docs/contracts/validation-and-routing.md`); and Phase 7 (a backend-only
human review workflow -- `ReviewRecord` state machine, explicit
field-path corrections, revalidation through the unmodified Phase 6
validator -- plus downstream JSON/CSV output gated on an `accepted`
result; see `docs/contracts/review-and-downstream-output.md`). Current
phase status lives in `docs/project-state.md`. Do not run a large-scale
Pipeline B benchmark, optimize its prompt, add constrained decoding,
fine-tune it, or make a Pipeline A/B promotion decision; do not change
Pipeline A or Pipeline B extraction behavior, or Phase 6 validation rules,
as part of a review/downstream-output task; do not add an ML/statistical
confidence model, a routing-policy configuration UI, an AI/LLM-based
auto-correction mechanism, a review reopen workflow, a review frontend,
RAG, a production database, vendor-specific (e.g. QuickBooks)
integrations, or authentication, unless a later brief explicitly asks for
them.

## Data Handling

Real taxpayer W-2 data is sensitive PII and must not be committed. Keep
authoritative blank IRS forms under `docs/references/`. Keep future benchmark
documents and ground truth under `data/evaluation/`, using synthetic or otherwise
safe data only.

## Long-Running Test And Benchmark Policy

Any deterministic test, benchmark, model evaluation, OCR run, build, or similar
command expected to take more than approximately 2 minutes must not be kept
running interactively while the agent repeatedly polls for completion.

Instead, launch it in the background or detached mode, redirect stdout and
stderr to a persistent log file, persist the process ID, persist or document the
intended result/output path, report the command, PID, log path, and expected
result path, then stop active polling and end the current turn once the process
is confirmed running.

Resume inspection only when the user explicitly asks to continue/check it, or
in a later agent turn. Do not repeatedly emit "still running", "still
processing", or "no output yet" style updates when no new engineering work is
occurring.

For benchmark-specific examples, follow `data/evaluation/README.md`.

## Changelog

Meaningful repository changes must update `CHANGELOG.md`.
