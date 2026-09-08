import type { ProcessingRun } from "@/lib/types";
import { absoluteApiUrl } from "@/lib/api";

// Timing labels intentionally match the backend's own field names/
// semantics (`docs/batch-runner.md`) -- `total_duration_seconds` is
// wall time, never presented as "latency".
export default function RunSummary({ run }: { run: ProcessingRun }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-wrap gap-x-8 gap-y-2 text-sm">
        <Stat label="Documents" value={String(run.documents_total)} />
        <Stat label="Accepted" value={String(run.accepted)} tone="emerald" />
        <Stat label="Needs review" value={String(run.needs_review)} tone="amber" />
        <Stat label="Failed" value={String(run.failed)} tone={run.failed > 0 ? "red" : undefined} />
      </div>

      <div className="mt-4 flex flex-wrap gap-x-8 gap-y-2 text-sm text-slate-600">
        <Stat label="Model startup" value={`${run.model_startup_seconds.toFixed(2)}s`} />
        <Stat label="Mean doc latency" value={`${run.mean_document_latency_seconds.toFixed(2)}s`} />
        <Stat label="Median doc latency" value={`${run.median_document_latency_seconds.toFixed(2)}s`} />
        {run.batch_processing_seconds !== null && (
          <Stat label="Batch processing" value={`${run.batch_processing_seconds.toFixed(2)}s`} />
        )}
        <Stat label="Total wall time" value={`${run.total_duration_seconds.toFixed(2)}s`} />
      </div>

      <div className="mt-4">
        {run.aggregate_csv_available && run.aggregate_csv_url ? (
          <a
            href={absoluteApiUrl(run.aggregate_csv_url)}
            className="inline-block rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700"
          >
            Download Finalized CSV
          </a>
        ) : (
          <p className="text-xs text-slate-400">
            No finalized CSV available -- no documents in this run were accepted.
          </p>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "emerald" | "amber" | "red" }) {
  const toneClass =
    tone === "emerald"
      ? "text-emerald-700"
      : tone === "amber"
        ? "text-amber-700"
        : tone === "red"
          ? "text-red-700"
          : "text-slate-900";
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className={`text-base font-semibold ${toneClass}`}>{value}</p>
    </div>
  );
}
