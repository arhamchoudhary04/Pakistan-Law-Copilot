"use client";

import { useState } from "react";
import type { AssistantMessage, SourceItem } from "@/lib/types";

/** Collapsible "show your work" panel: per-stage trace + retrieved chunks with scores. */
export function RetrievalInspector({
  message,
  onOpenSource,
}: {
  message: AssistantMessage;
  onOpenSource: (source: SourceItem) => void;
}) {
  const [open, setOpen] = useState(false);
  const hasData = message.stages.length > 0 || message.sources.length > 0;
  if (!hasData) return null;

  const maxLatency = Math.max(1, ...message.stages.map((s) => s.latency_ms));

  return (
    <div className="overflow-hidden rounded-xl border border-line bg-card/60">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-2.5 text-left text-xs font-medium text-muted transition hover:text-ink"
      >
        <span className="flex items-center gap-1.5">
          <span className={`text-faint transition-transform ${open ? "rotate-90" : ""}`}>›</span>
          Retrieval inspector · {message.stages.length} stages · {message.sources.length} chunks
        </span>
      </button>

      {open && (
        <div className="space-y-4 border-t border-line px-4 py-3.5">
          <section>
            <h4 className="mb-2 text-[10px] font-medium uppercase tracking-[0.16em] text-faint">
              Pipeline
            </h4>
            <ul className="space-y-1.5">
              {message.stages.map((s, i) => (
                <li key={i} className="flex items-center gap-3 text-xs">
                  <span className="w-16 shrink-0 font-mono text-accent">{s.stage}</span>
                  <span className="flex-1 truncate text-muted" title={s.detail}>
                    {s.detail}
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="h-1 w-16 overflow-hidden rounded-full bg-surface">
                      <span
                        className="block h-full rounded-full bg-accent/70"
                        style={{ width: `${(s.latency_ms / maxLatency) * 100}%` }}
                      />
                    </span>
                    <span className="w-14 text-right font-mono text-faint">
                      {s.latency_ms.toFixed(0)}ms
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          </section>

          {message.sources.length > 0 && (
            <section>
              <h4 className="mb-2 text-[10px] font-medium uppercase tracking-[0.16em] text-faint">
                Retrieved chunks (ranked)
              </h4>
              <ul className="space-y-0.5">
                {message.sources.map((s) => (
                  <li key={s.chunk_id}>
                    <button
                      onClick={() => onOpenSource(s)}
                      className={`flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 text-left text-xs transition hover:bg-surface ${
                        s.used ? "bg-accent-tint" : ""
                      }`}
                    >
                      <span className="flex-1 truncate text-ink/80" title={s.section}>
                        {s.section || s.source}
                      </span>
                      {s.via_graph && (
                        <span className="rounded border border-line bg-surface px-1.5 py-0.5 text-[10px] text-muted">
                          graph
                        </span>
                      )}
                      {s.used && (
                        <span className="rounded bg-accent/15 px-1.5 py-0.5 text-[10px] font-medium text-accent">
                          cited
                        </span>
                      )}
                      <span className="w-14 text-right font-mono text-faint">
                        cos {s.score.toFixed(2)}
                      </span>
                      <span className="w-16 text-right font-mono text-faint">
                        {s.rerank_score !== null ? `rr ${s.rerank_score.toFixed(1)}` : "—"}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
