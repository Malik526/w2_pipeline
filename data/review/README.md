# Local Review Records

This directory is the default location for `FileReviewRepository` review
record artifacts (`src/w2_pipeline/review/repository.py`).

A `ReviewRecord` carries the full original (and, once corrected, the
corrected) canonical `W2Document` -- in production use with real W-2s, that
means real taxpayer PII and financial information. Review records must not
be committed to the repository or copied into docs, test fixtures, logs,
screenshots, or generated artifacts.

The `.gitignore` file excludes local review record files by default.
Filenames use the review ID only (never a name/SSN/EIN), matching the
project's PII-in-filenames policy.
