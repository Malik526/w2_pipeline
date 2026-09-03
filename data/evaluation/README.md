# Evaluation Data

Phase 3 defines a reproducible synthetic evaluation dataset for offline
benchmarking. Generated assets are written under:

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
