"use client";

import { CitationChip } from "./CitationChip";
import { StatusBadge } from "./StatusBadge";
import { dirOf } from "@/lib/text";
import type { AssistantMessage, SourceItem } from "@/lib/types";

const MARKER_RE = /(\[\d+\])/g;

/**
 * Renders the assistant answer with inline [n] citation chips. Clicking a chip
 * opens the corresponding source. Citations map marker -> chunk_id (from the
 * citation events) -> full source metadata (from the sources event).
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

  // While the agent runs (multi-second) and no answer text has arrived yet, show a
  // live "thinking" line with the current pipeline stage so it never looks stuck.
  if (message.streaming && !message.text) {
    const last = message.stages[message.stages.length - 1];
    const label = last ? `${last.stage}…` : "searching the law…";
    return (
      <div className="rounded-2xl rounded-bl-md border border-white/[0.08] bg-white/[0.03] p-4 shadow-card">
        <div className="flex items-center gap-2.5">
          <span className="flex gap-1">
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-400/70 [animation-delay:-0.3s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-400/70 [animation-delay:-0.15s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-400/70" />
          </span>
          <span className="font-mono text-xs text-zinc-500">{label}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl rounded-bl-md border border-white/[0.08] bg-white/[0.03] p-4 shadow-card">
      <div
        dir={dirOf(message.text)}
        className="whitespace-pre-wrap break-words text-[15px] leading-relaxed text-zinc-100"
      >
        {parts.map((part, i) => {
          const m = /^\[(\d+)\]$/.exec(part);
          if (m) {
            const marker = Number(m[1]);
            const clickable = chunkByMarker.has(marker);
            return clickable ? (
              <CitationChip key={i} marker={marker} onClick={() => openMarker(marker)} />
            ) : (
              <span key={i}>{part}</span>
            );
          }
          return <span key={i}>{part}</span>;
        })}
        {message.streaming && <span className="ml-0.5 animate-pulse text-indigo-400">▍</span>}
      </div>

      {(message.status || message.attempts > 1) && (
        <div className="mt-3 flex items-center gap-3 border-t border-white/10 pt-3">
          {message.status && <StatusBadge status={message.status} />}
          {message.attempts > 1 && (
            <span className="text-xs text-zinc-500">{message.attempts} attempts</span>
          )}
        </div>
      )}
    </div>
  );
}
