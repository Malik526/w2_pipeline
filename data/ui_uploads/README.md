# Local Demo UI Uploads

This directory is the default staging area for `w2_pipeline.api`'s
`POST /api/process` endpoint (Phase 8D.7's demo UI): each request writes
its uploaded W-2 file(s) under a per-run subdirectory,
`data/ui_uploads/<run_id>/`, before handing their paths to the unmodified
`run_document()`/`run_batch()` application services.

Filenames are sanitized to a safe `[A-Za-z0-9_-]` document ID plus the
original (validated) extension -- never the raw uploaded filename -- so
this directory never reflects arbitrary user-controlled paths.

Uploaded files may be synthetic demo documents or, in a future real
deployment, real taxpayer W-2s -- treat this directory as PII-sensitive
the same as `data/review/`. The `.gitignore` file excludes its contents
by default.
