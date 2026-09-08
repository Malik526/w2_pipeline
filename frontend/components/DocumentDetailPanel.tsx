"use client";

import { useEffect, useState } from "react";
import { absoluteApiUrl, fetchDocumentDetail } from "@/lib/api";
import type { DocumentResult } from "@/lib/types";
import StatusBadge from "./StatusBadge";

interface DocumentDetailPanelProps {
  runId: string;
  document: DocumentResult;
  onClose: () => void;
}

type Canonical = Record<string, unknown>;

function get(obj: Canonical | null | undefined, ...path: string[]): unknown {
  let current: unknown = obj;
  for (const key of path) {
    if (current == null || typeof current !== "object") return null;
    current = (current as Canonical)[key];
  }
  return current ?? null;
}

function display(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

function money(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  return `$${value}`;
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 py-1 text-sm">
      <span className="text-slate-500">{label}</span>
      <span className="text-right text-slate-800">{value}</span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-md border border-slate-200 p-3">
      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">{title}</h3>
      {children}
    </div>
  );
}

export default function DocumentDetailPanel({ runId, document, onClose }: DocumentDetailPanelProps) {
  const [canonical, setCanonical] = useState<Canonical | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // `loading` starts `true` (see `useState` above) and the parent
    // remounts this component per document (`key={document.document_id}`
    // in app/page.tsx), so no synchronous `setLoading(true)` is needed
    // here -- only the eventual `false` once the fetch settles.
    let cancelled = false;
    fetchDocumentDetail(runId, document.document_id)
      .then((detail) => {
        if (!cancelled) setCanonical(detail.canonical);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load extracted data for this document.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [runId, document.document_id]);

  const box12 = (get(canonical, "box_12_entries") as { code: string; amount: unknown }[] | null) ?? [];
  const box14 = (get(canonical, "box_14_entries") as { label: string; amount: unknown; value: unknown }[] | null) ?? [];
  const stateLocal = (get(canonical, "state_local_entries") as Canonical[] | null) ?? [];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-6 shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <p className="text-xs text-slate-400">{document.document_id}</p>
            <h2 className="text-lg font-semibold text-slate-900">{document.filename}</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-2 py-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="mb-4 flex flex-wrap items-center gap-4">
          <StatusBadge status={document.status} />
          <span className="text-sm text-slate-500">
            Processing latency: {document.processing_latency_seconds.toFixed(2)}s
          </span>
        </div>

        {document.status === "needs_review" && (
          <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            <p className="font-medium">Needs human review</p>
            <ul className="mt-1 list-inside list-disc">
              {document.issue_codes.map((code) => (
                <li key={code}>{code}</li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-amber-700">Review ID: {document.review_id}</p>
            <p className="mt-1 text-xs font-medium text-amber-800">
              Finalization blocked until review is resolved.
            </p>
          </div>
        )}

        {document.status === "failed" && (
          <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            {document.error_message ?? "Processing failed."}
          </div>
        )}

        {document.finalized && (
          <div className="mb-4 flex gap-2">
            {document.downloads.json && (
              <a
                href={absoluteApiUrl(document.downloads.json)}
                className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700"
              >
                Download JSON
              </a>
            )}
            {document.downloads.csv && (
              <a
                href={absoluteApiUrl(document.downloads.csv)}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                Download CSV
              </a>
            )}
          </div>
        )}

        {loading && <p className="text-sm text-slate-400">Loading extracted data…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}

        {!loading && !error && canonical && (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Section title="Employee">
              <Field label="Name" value={display(`${get(canonical, "employee", "first_name") ?? ""} ${get(canonical, "employee", "last_name") ?? ""}`.trim() || null)} />
              <Field label="SSN" value={display(get(canonical, "employee", "ssn"))} />
              <Field
                label="Address"
                value={display(get(canonical, "employee", "address", "address_line_1"))}
              />
              <Field
                label="City / State / ZIP"
                value={[
                  get(canonical, "employee", "address", "city"),
                  get(canonical, "employee", "address", "state"),
                  get(canonical, "employee", "address", "postal_code"),
                ]
                  .filter(Boolean)
                  .join(", ") || "—"}
              />
            </Section>

            <Section title="Employer">
              <Field label="Name" value={display(get(canonical, "employer", "name"))} />
              <Field label="EIN" value={display(get(canonical, "employer", "ein"))} />
              <Field
                label="Address"
                value={display(get(canonical, "employer", "address", "address_line_1"))}
              />
              <Field
                label="City / State / ZIP"
                value={[
                  get(canonical, "employer", "address", "city"),
                  get(canonical, "employer", "address", "state"),
                  get(canonical, "employer", "address", "postal_code"),
                ]
                  .filter(Boolean)
                  .join(", ") || "—"}
              />
            </Section>

            <Section title="Federal (Boxes 1-11)">
              <Field label="Box 1 - Wages" value={money(get(canonical, "federal_wages_and_taxes", "box_1_wages_tips_other_compensation"))} />
              <Field label="Box 2 - Federal tax withheld" value={money(get(canonical, "federal_wages_and_taxes", "box_2_federal_income_tax_withheld"))} />
              <Field label="Box 3 - SS wages" value={money(get(canonical, "federal_wages_and_taxes", "box_3_social_security_wages"))} />
              <Field label="Box 5 - Medicare wages" value={money(get(canonical, "federal_wages_and_taxes", "box_5_medicare_wages_and_tips"))} />
              <Field label="Box 6 - Medicare tax" value={money(get(canonical, "federal_wages_and_taxes", "box_6_medicare_tax_withheld"))} />
            </Section>

            <Section title="Box 13">
              <Field label="Statutory employee" value={display(get(canonical, "box_13", "statutory_employee"))} />
              <Field label="Retirement plan" value={display(get(canonical, "box_13", "retirement_plan"))} />
              <Field label="Third-party sick pay" value={display(get(canonical, "box_13", "third_party_sick_pay"))} />
            </Section>

            {box12.length > 0 && (
              <Section title="Box 12">
                {box12.map((entry, index) => (
                  <Field key={index} label={`Code ${entry.code}`} value={money(entry.amount)} />
                ))}
              </Section>
            )}

            {box14.length > 0 && (
              <Section title="Box 14">
                {box14.map((entry, index) => (
                  <Field key={index} label={entry.label} value={entry.amount !== null ? money(entry.amount) : display(entry.value)} />
                ))}
              </Section>
            )}

            {stateLocal.length > 0 && (
              <Section title="State / Local">
                {stateLocal.map((entry, index) => (
                  <div key={index} className={index > 0 ? "mt-2 border-t border-slate-100 pt-2" : undefined}>
                    <Field label="State" value={display(entry.box_15_state)} />
                    <Field label="State wages" value={money(entry.box_16_state_wages_tips_etc)} />
                    <Field label="State tax" value={money(entry.box_17_state_income_tax)} />
                  </div>
                ))}
              </Section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
