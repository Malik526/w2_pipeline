// Mirrors `w2_pipeline.api.schemas` field-for-field (snake_case wire
// format, matching this project's existing run_summary.json/
// batch_summary.json convention) -- never a second interpretation of
// what the backend already computed.

export type DocumentStatus = "accepted" | "needs_review" | "failed";

export interface DocumentResult {
  document_id: string;
  filename: string;
  status: DocumentStatus;
  route: string | null;
  issue_codes: string[];
  review_id: string | null;
  finalized: boolean;
  error_message: string | null;
  model_startup_seconds: number;
  processing_latency_seconds: number;
  total_duration_seconds: number;
  downloads: Record<string, string>;
}

export interface DocumentDetail extends DocumentResult {
  canonical: Record<string, unknown> | null;
}

export interface ProcessingRun {
  run_id: string;
  mode: "single" | "batch";
  documents_total: number;
  accepted: number;
  needs_review: number;
  failed: number;
  model_startup_seconds: number;
  batch_processing_seconds: number | null;
  mean_document_latency_seconds: number;
  median_document_latency_seconds: number;
  total_duration_seconds: number;
  aggregate_csv_available: boolean;
  aggregate_csv_url: string | null;
  documents: DocumentResult[];
}

export interface HealthCheck {
  status: string;
  supported_extensions: string[];
}
