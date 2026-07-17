// Base URL the browser uses to reach the FastAPI backend.
// Set NEXT_PUBLIC_API_URL in the environment; defaults to local dev.
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

export interface UploadedDoc {
  doc_id: string;
  filename: string;
  chunks: number;
}

/**
 * Upload a PDF to `POST /documents`. The returned `doc_id` is passed to /chat to
 * answer questions grounded in that document instead of the law corpus.
 */
export async function uploadDocument(file: File, signal?: AbortSignal): Promise<UploadedDoc> {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(`${API_URL}/documents`, { method: "POST", body: form, signal });
  if (!resp.ok) {
    const raw = await resp.text().catch(() => "");
    let detail = raw;
    try {
      detail = JSON.parse(raw).detail ?? raw;
    } catch {
      /* not JSON — use raw text */
    }
    throw new Error(detail || `Upload failed (${resp.status})`);
  }
  return (await resp.json()) as UploadedDoc;
}
