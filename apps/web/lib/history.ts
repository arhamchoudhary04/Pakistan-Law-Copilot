import type { StoredMessage } from "./api";
import type { AnswerStatus, ChatTurn, CitationEvent, SourceItem } from "./types";

/**
 * Rebuild chat turns from a conversation's stored messages (alternating user/assistant).
 * The assistant `meta` blob (status, citations, sources) keeps reloaded answers clickable;
 * stages aren't persisted since the inspector is a live-run detail.
 */
export function turnsFromMessages(messages: StoredMessage[]): ChatTurn[] {
  const turns: ChatTurn[] = [];
  for (let i = 0; i < messages.length; i++) {
    const m = messages[i];
    if (m.role !== "user") continue;
    const next = messages[i + 1];
    const assistant = next && next.role === "assistant" ? next : null;
    const meta = (assistant?.meta ?? {}) as {
      status?: AnswerStatus;
      attempts?: number;
      citations?: CitationEvent[];
      sources?: SourceItem[];
    };
    turns.push({
      question: m.content,
      answer: {
        text: assistant?.content ?? "",
        stages: [],
        citations: meta.citations ?? [],
        sources: meta.sources ?? [],
        status: meta.status ?? null,
        attempts: meta.attempts ?? 1,
        streaming: false,
      },
    });
    if (assistant) i++;
  }
  return turns;
}
