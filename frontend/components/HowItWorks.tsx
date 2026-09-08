"use client";

import { useState } from "react";

const STEPS = [
  "Ingest completed W-2",
  "PaddleOCR",
  "Deterministic extraction",
  "Evidence-based validation",
  "Human review when uncertain",
  "Finalized JSON/CSV output",
];

export default function HowItWorks() {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-lg border border-slate-200">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between px-4 py-2 text-sm font-medium text-slate-700"
      >
        How it works
        <span aria-hidden="true">{open ? "−" : "+"}</span>
      </button>
      {open && (
        <ol className="space-y-1 border-t border-slate-100 px-4 py-3 text-sm text-slate-600">
          {STEPS.map((step, index) => (
            <li key={step}>
              {index + 1}. {step}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
