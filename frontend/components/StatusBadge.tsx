import type { DocumentStatus } from "@/lib/types";

const STYLES: Record<DocumentStatus, string> = {
  accepted: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  needs_review: "bg-amber-50 text-amber-800 ring-amber-600/20",
  failed: "bg-red-50 text-red-700 ring-red-600/20",
};

const LABELS: Record<DocumentStatus, string> = {
  accepted: "Accepted",
  needs_review: "Needs Review",
  failed: "Failed",
};

const ICONS: Record<DocumentStatus, string> = {
  accepted: "✓",
  needs_review: "!",
  failed: "✕",
};

// Never relies on color alone: every badge carries an icon glyph and a
// text label alongside its color, so status remains distinguishable
// without color vision.
export default function StatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${STYLES[status]}`}
    >
      <span aria-hidden="true">{ICONS[status]}</span>
      {LABELS[status]}
    </span>
  );
}
