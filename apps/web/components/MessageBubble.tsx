"use client";

import { CitationChip } from "./CitationChip";
import { StatusBadge } from "./StatusBadge";
import { dirOf } from "@/lib/text";
import type { AssistantMessage, SourceItem } from "@/lib/types";

const MARKER_RE = /(\[\d+\])/g;

/**
 * Renders the assistant answer as a document card with inline superscript
 * citations. Clicking a citation opens its source. Citations map
 * marker -> chunk_id (citation events) -> full source metadata (sources event).
 */
export function MessageBubble({
  message,
  onOpenSource,
}: {
  message: AssistantMessage;
  onOpenSource: (source: SourceItem) => void;
}) {
  const sourceByChunk = new Map(message.sources.map((s) => [s.chunk_id, s]));
  const chunkByMarker = new Map(message.citations.map((c) => [c.marker, c.chunk_id]));

  const openMarker = (marker: number) => {
    const chunkId = chunkByMarker.get(marker);
    const source = chunkId ? sourceByChunk.get(chunkId) : undefined;
    if (source) onOpenSource(source);
  };

  const parts = message.text.split(MARKER_RE);

  // Multi-second run with no answer text yet: a quiet "working" line with the
  // current pipeline stage so it never looks stuck.
  if (message.streaming && !message.text) {
    const last = message.stages[message.stages.length - 1];
    const label = last ? `${last.stage}…` : "searching the statutes…";
    return (
      <div className="rounded-2xl border border-line bg-card p-5 shadow-paper">
        <div className="flex items-center gap-2.5">
          <span className="flex gap-1">
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent/60 [animation-delay:-0.3s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent/60 [animation-delay:-0.15s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent/60" />
          </span>
          <span className="font-mono text-xs text-muted">{label}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-line bg-card p-5 shadow-paper">
      <div
        dir={dirOf(message.text)}
        className="whitespace-pre-wrap break-words text-[15px] leading-7 text-ink"
      >
        {parts.map((part, i) => {
          const m = /^\[(\d+)\]$/.exec(part);
          if (m) {
            const marker = Number(m[1]);
            return chunkByMarker.has(marker) ? (
              <CitationChip key={i} marker={marker} onClick={() => openMarker(marker)} />
            ) : (
              <span key={i}>{part}</span>
            );
          }
          return <span key={i}>{part}</span>;
        })}
        {message.streaming && <span className="ml-0.5 animate-pulse text-accent">▍</span>}
      </div>

      {(message.status || message.attempts > 1) && (
        <div className="mt-4 flex items-center gap-3 border-t border-line pt-3">
          {message.status && <StatusBadge status={message.status} />}
          {message.attempts > 1 && (
            <span className="text-xs text-faint">{message.attempts} attempts</span>
          )}
        </div>
      )}
    </div>
  );
}
