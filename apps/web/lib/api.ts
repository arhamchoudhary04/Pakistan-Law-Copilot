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
      /* not JSON, use raw text */
    }
    throw new Error(detail || `Upload failed (${resp.status})`);
  }
  return (await resp.json()) as UploadedDoc;
}

// ---- Auth & chat history ----

export interface AuthUser {
  id: string;
  email: string;
  name: string;
}

export interface AuthResult {
  token: string;
  user: AuthUser;
}

export interface ConversationSummary {
  id: string;
  title: string;
  updated_at: string;
}

export interface StoredMessage {
  role: "user" | "assistant";
  content: string;
  meta: Record<string, unknown> | null;
}

export interface ConversationDetail extends ConversationSummary {
  messages: StoredMessage[];
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function apiFetch<T>(path: string, opts: RequestInit = {}, token?: string): Promise<T> {
  const headers: Record<string, string> = {};
  if (opts.body) headers["Content-Type"] = "application/json";
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const resp = await fetch(`${API_URL}${path}`, { ...opts, headers });
  if (!resp.ok) {
    const raw = await resp.text().catch(() => "");
    let detail = raw;
    try {
      detail = JSON.parse(raw).detail ?? raw;
    } catch {
      /* not JSON */
    }
    throw new ApiError(detail || `Request failed (${resp.status})`, resp.status);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export const signup = (email: string, name: string, password: string) =>
  apiFetch<AuthResult>("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, name, password }),
  });

export const login = (email: string, password: string) =>
  apiFetch<AuthResult>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });

export const forgotPassword = (email: string) =>
  apiFetch<{ message: string; reset_token: string | null }>("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  });

export const resetPassword = (token: string, newPassword: string) =>
  apiFetch<AuthResult>("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ token, new_password: newPassword }),
  });

export const fetchMe = (token: string) => apiFetch<AuthUser>("/auth/me", {}, token);

export const listConversations = (token: string) =>
  apiFetch<ConversationSummary[]>("/conversations", {}, token);

export const createConversation = (title: string, token: string) =>
  apiFetch<ConversationSummary>("/conversations", { method: "POST", body: JSON.stringify({ title }) }, token);

export const getConversation = (id: string, token: string) =>
  apiFetch<ConversationDetail>(`/conversations/${id}`, {}, token);

export const deleteConversation = (id: string, token: string) =>
  apiFetch<void>(`/conversations/${id}`, { method: "DELETE" }, token);

export const saveTurn = (
  id: string,
  body: { question: string; answer: string; meta?: Record<string, unknown> },
  token: string,
) => apiFetch<void>(`/conversations/${id}/turn`, { method: "POST", body: JSON.stringify(body) }, token);
