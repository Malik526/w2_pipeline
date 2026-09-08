"""Phase 8D.7: thin FastAPI transport layer for the Next.js demo UI.

Nothing in this package implements extraction, validation, review, or
export logic -- it only stages uploads and calls
`w2_pipeline.application.run_document.run_document()` /
`w2_pipeline.application.run_batch.run_batch()`, the same application
services the CLIs (`w2_pipeline.cli.run_document`/`run_batch`) and the
agent skill (`skills/run-w2-pipeline/`) already call.
"""
