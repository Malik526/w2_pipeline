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
- `docs/references/irs/README.md` for official IRS reference artifact handling.

## Skills

Use these project-local skills when the current task matches their scope:

- `skills/run-pipeline-a-extraction-experiment/SKILL.md` for running or
  benchmarking a Pipeline A OCR extraction configuration (named phase
  experiments, PSM configuration runs, smoke tests, or full clean/robustness
  benchmark runs). Pipeline A only; Pipeline B has no defined execution
  workflow yet.

## Scope Guard

The project has implemented Phase 0-4D: contracts, the canonical W-2 schema,
the ingestion boundary, the evaluation harness (internal and external Symage
benchmarks), and Pipeline A (deterministic native-text/OCR extraction,
including configurable Tesseract PSM experiments). Current phase status lives
in `docs/project-state.md`. Do not implement Pipeline B, model/vision
inference, validation engines, review UI, CSV export, RAG, persistence,
frontend, or production integrations unless a later brief explicitly asks for
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
