# IRS Reference Artifacts

This directory contains authoritative IRS reference/specification artifacts.
These files describe official form structure and terminology for implementation
planning.

## 2026 Form W-2

Reference file:

```text
docs/references/irs/2026_W2.pdf
```

Source:

```text
https://www.irs.gov/pub/irs-pdf/fw2.pdf
```

Observed IRS directory description on 2026-09-02:

```text
fw2.pdf - 2026 Form W-2 (PDF)
```

Local SHA-256:

```text
61eca7c81f16d3965819fe1f31be4fe68c1b2887a81f51172f1d2ed2b2b9f087
```

The 2026 Form W-2 PDF is the authoritative form-format reference for the
initial implementation. It establishes field names, field organization,
groupings, repeatable fields, checkbox fields, code/value structures,
state/local structure, tax-year-specific form differences, layout
characteristics, and IRS terminology.

The 2026 form includes year-specific structure such as Box 14b, Treasury Tipped
Occupation Code(s). Phase 1 must derive the initial canonical W-2 schema from
this 2026 reference, not from older generic examples.

## Reference Vs Evaluation Data

Reference artifacts are not:

- taxpayer fixtures
- ground-truth extraction samples
- completed W-2s
- benchmark data
- model training data

Evaluation documents and ground truth belong under `data/evaluation/`.

Do not mix official reference documents with evaluation data.
