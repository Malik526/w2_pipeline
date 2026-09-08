// Thin fetch wrapper over the FastAPI backend (`w2_pipeline.api.app`).
// Contains no interpretation of processing results -- only HTTP calls
// and error surfacing -- so all status/latency/review semantics stay
// defined exactly once, in the Python application layer.

import type { DocumentDetail, HealthCheck, ProcessingRun } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? response.statusText;
  } catch {
    return response.statusText || "Request failed.";
  }
}

export async function checkHealth(): Promise<HealthCheck> {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorDetail(response));
  }
  return response.json() as Promise<HealthCheck>;
}

export async function processFiles(files: File[]): Promise<ProcessingRun> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  const response = await fetch(`${API_BASE_URL}/api/process`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorDetail(response));
  }
  return response.json() as Promise<ProcessingRun>;
}

export async function fetchDocumentDetail(runId: string, documentId: string): Promise<DocumentDetail> {
  const response = await fetch(`${API_BASE_URL}/api/runs/${runId}/documents/${documentId}`);
  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorDetail(response));
  }
  return response.json() as Promise<DocumentDetail>;
}

export function absoluteApiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}
