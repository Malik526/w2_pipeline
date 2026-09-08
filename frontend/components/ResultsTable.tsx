import type { DocumentResult } from "@/lib/types";
import StatusBadge from "./StatusBadge";

interface ResultsTableProps {
  documents: DocumentResult[];
  onView: (document: DocumentResult) => void;
}

export default function ResultsTable({ documents, onView }: ResultsTableProps) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-2 text-left font-medium text-slate-500">File</th>
            <th className="px-4 py-2 text-left font-medium text-slate-500">Status</th>
            <th className="px-4 py-2 text-left font-medium text-slate-500">Latency</th>
            <th className="px-4 py-2 text-left font-medium text-slate-500">Issues / Review</th>
            <th className="px-4 py-2 text-right font-medium text-slate-500">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {documents.map((doc) => (
            <tr key={doc.document_id}>
              <td className="max-w-xs truncate px-4 py-2 text-slate-800">{doc.filename}</td>
              <td className="px-4 py-2">
                <StatusBadge status={doc.status} />
              </td>
              <td className="px-4 py-2 text-slate-600">
                {doc.processing_latency_seconds.toFixed(2)}s
              </td>
              <td className="px-4 py-2 text-slate-500">
                {doc.status === "needs_review" && doc.issue_codes.length > 0
                  ? doc.issue_codes.join(", ")
                  : doc.status === "failed"
                    ? (doc.error_message ?? "Processing failed.")
                    : "—"}
              </td>
              <td className="px-4 py-2 text-right">
                <button
                  type="button"
                  onClick={() => onView(doc)}
                  className="text-xs font-medium text-slate-700 underline-offset-2 hover:underline"
                >
                  {doc.status === "needs_review" ? "Review" : "View"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
