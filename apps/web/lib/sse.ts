import { API_URL } from "./api";
import type { ChatEvent } from "./types";

/**
 * Stream `POST /chat` as an async iterable of parsed SSE events.
 *
 * The backend uses standard SSE framing (`event:` + `data:` lines, blank line
 * between events). Because /chat is a POST with a JSON body, we can't use the
 * browser's EventSource (GET-only), so we read the fetch response body stream and
 * parse the frames ourselves.
 */
export async function* streamChat(
  message: string,
  history: { question: string; answer: string }[] = [],
  docId: string | null = null,
  signal?: AbortSignal,
): AsyncGenerator<ChatEvent> {
  const resp = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history, doc_id: docId }),
    signal,
  });

  if (!resp.ok || !resp.body) {
    const detail = await resp.text().catch(() => "");
    throw new Error(`Request failed (${resp.status}) ${detail}`.trim());
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // Normalize CRLF -> LF. sse-starlette separates events with "\r\n\r\n", which
    // does NOT contain "\n\n", so we must normalize before splitting on blank lines.
    buffer = buffer.replace(/\r\n/g, "\n");

    // SSE events are separated by a blank line.
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const parsed = parseFrame(frame);
      if (parsed) yield parsed;
    }
  }
}

function parseFrame(frame: string): ChatEvent | null {
  let event: string | null = null;
  const dataLines: string[] = [];
  for (const raw of frame.split("\n")) {
    const line = raw.replace(/\r$/, "");
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (!event || dataLines.length === 0) return null;
  try {
    const data = JSON.parse(dataLines.join("\n"));
    return { event, data } as ChatEvent;
  } catch {
    return null;
  }
}
