# W-2 Pipeline Demo UI

Next.js + TypeScript frontend for this project's demo UI (Phase 8D.7). It
is presentation/orchestration only -- it calls the FastAPI backend
(`w2_pipeline.api`), which in turn calls the same
`run_document()`/`run_batch()` application services the CLIs and agent
skill use. No extraction/validation/review logic lives here.

Full setup, architecture, and behavior: see
[`../docs/demo-ui.md`](../docs/demo-ui.md) and the main
[`../README.md`](../README.md) ("Run the demo UI" section).

## Quick start

```bash
npm install
cp .env.example .env.local   # defaults to http://localhost:8000
npm run dev
```

Requires the FastAPI backend running separately -- see
`docs/demo-ui.md`.
