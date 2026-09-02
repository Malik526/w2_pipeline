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
- `docs/references/irs/README.md` for official IRS reference artifact handling.

## Scope Guard

The project currently includes Phase 0 contracts and the Phase 1 canonical W-2
schema contract. Do not implement extraction, OCR, validation engines,
evaluation runners, adapters, review UI, CSV export, RAG, persistence,
frontend, or production integrations unless a later brief explicitly asks for
them.

## Data Handling

Real taxpayer W-2 data is sensitive PII and must not be committed. Keep
authoritative blank IRS forms under `docs/references/`. Keep future benchmark
documents and ground truth under `data/evaluation/`, using synthetic or otherwise
safe data only.

## Changelog

Meaningful repository changes must update `CHANGELOG.md`.
