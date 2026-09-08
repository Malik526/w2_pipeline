"use client";

import { useEffect, useState } from "react";
import { ApiError, checkHealth, processFiles } from "@/lib/api";
import type { DocumentResult, ProcessingRun } from "@/lib/types";
import UploadZone from "@/components/UploadZone";
import ResultsTable from "@/components/ResultsTable";
import RunSummary from "@/components/RunSummary";
import DocumentDetailPanel from "@/components/DocumentDetailPanel";
import HowItWorks from "@/components/HowItWorks";

export default function Home() {
  const [supportedExtensions, setSupportedExtensions] = useState<string[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [run, setRun] = useState<ProcessingRun | null>(null);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<DocumentResult | null>(null);

  useEffect(() => {
    checkHealth()
      .then((health) => setSupportedExtensions(health.supported_extensions))
      .catch(() => setError("Could not reach the processing backend. Is the API server running?"));
  }, []);

  async function handleRun() {
    if (files.length === 0 || processing) return;
    setProcessing(true);
    setError(null);
    setRun(null);
    try {
      const result = await processFiles(files);
      setRun(result);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("The processor is currently busy with another run. Try again shortly.");
      } else if (err instanceof ApiError && err.status === 502) {
        setError("Processing backend could not initialize.");
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Something went wrong while processing these documents.");
      }
    } finally {
      setProcessing(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-4 py-10">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">W-2 Processing Demo</h1>
        <p className="mt-1 text-sm text-slate-600">
          Upload completed W-2 documents to extract, validate, route uncertain documents for human
          review, and export finalized structured data.
        </p>
      </header>

      <section className="rounded-lg border border-slate-200 p-4">
        <UploadZone
          acceptedExtensions={supportedExtensions}
          files={files}
          onFilesChange={setFiles}
          disabled={processing}
        />
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-slate-500">
            {processing
              ? `Initializing PaddleOCR and processing ${files.length} document${files.length === 1 ? "" : "s"}…`
              : files.length > 0
                ? `Ready to process ${files.length} document${files.length === 1 ? "" : "s"}.`
                : "No files selected yet."}
          </p>
          <button
            type="button"
            onClick={handleRun}
            disabled={files.length === 0 || processing}
            className="shrink-0 rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {processing ? "Processing…" : "Run Processing"}
          </button>
        </div>
      </section>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {run && (
        <section className="flex flex-col gap-4">
          <ResultsTable documents={run.documents} onView={setSelectedDocument} />
          <RunSummary run={run} />
        </section>
      )}

      <HowItWorks />

      {run && selectedDocument && (
        <DocumentDetailPanel
          key={selectedDocument.document_id}
          runId={run.run_id}
          document={selectedDocument}
          onClose={() => setSelectedDocument(null)}
        />
      )}
    </main>
  );
}
