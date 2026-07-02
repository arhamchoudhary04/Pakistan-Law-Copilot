// Base URL the browser uses to reach the FastAPI backend.
// Set NEXT_PUBLIC_API_URL in the environment; defaults to local dev.
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";
