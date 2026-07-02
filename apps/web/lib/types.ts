// Mirrors the backend SSE payloads (app/models/schemas.py).

export type AnswerStatus = "grounded" | "idk" | "partial";

export interface StageEvent {
  stage: string;
  detail: string;
  latency_ms: number;
}

export interface CitationEvent {
  marker: number;
  chunk_id: string;
  source: string;
  section: string;
}

export interface SourceItem {
  chunk_id: string;
  score: number;
  rerank_score: number | null;
  used: boolean;
  section: string;
  source: string;
}

export interface DoneEvent {
  message_id: string;
  answer_status: AnswerStatus;
  attempts: number;
}

// Discriminated union of parsed SSE events.
export type ChatEvent =
  | { event: "stage"; data: StageEvent }
  | { event: "token"; data: { text: string } }
  | { event: "citation"; data: CitationEvent }
  | { event: "sources"; data: { retrieved: SourceItem[] } }
  | { event: "done"; data: DoneEvent };

// Assembled state for one assistant answer, built up from the event stream.
export interface AssistantMessage {
  text: string;
  stages: StageEvent[];
  citations: CitationEvent[];
  sources: SourceItem[];
  status: AnswerStatus | null;
  attempts: number;
  streaming: boolean;
  error?: string;
}

export interface ChatTurn {
  question: string;
  answer: AssistantMessage;
}
