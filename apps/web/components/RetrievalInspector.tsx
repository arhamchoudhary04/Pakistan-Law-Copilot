"use client";

import { useState } from "react";
import type { AssistantMessage, SourceItem } from "@/lib/types";

/**
 * Collapsible panel exposing what the agent actually did: the per-stage trace
 * (with latency) and every retrieved chunk with its scores and `used` flag.
 * This is the "show your work" surface that makes the pipeline trustworthy.
 */
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
    <div className="overflow-hidden rounded-xl border border-white/[0.08] bg-white/[0.02]">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-2.5 text-left text-xs font-medium text-zinc-400 transition hover:text-zinc-200"
      >
        <span className="flex items-center gap-1.5">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden className="text-indigo-400/70">
            <path d="M12 3v18M3 12h18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          Retrieval inspector · {message.stages.length} stages · {message.sources.length} chunks
        </span>
        <span className={`text-zinc-500 transition-transform ${open ? "rotate-90" : ""}`}>›</span>
      </button>

      {open && (
        <div className="space-y-4 border-t border-white/[0.08] px-4 py-3.5">
          <section>
            <h4 className="mb-2 text-[10px] font-medium uppercase tracking-wider text-zinc-500">
              Pipeline stages
            </h4>
            <ul className="space-y-1.5">
              {message.stages.map((s, i) => (
                <li key={i} className="flex items-center gap-3 text-xs">
                  <span className="w-16 shrink-0 font-mono text-indigo-300">{s.stage}</span>
                  <span className="flex-1 truncate text-zinc-400" title={s.detail}>
                    {s.detail}
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="h-1 w-16 overflow-hidden rounded-full bg-white/10">
                      <span
                        className="block h-full rounded-full bg-indigo-500/70"
                        style={{ width: `${(s.latency_ms / maxLatency) * 100}%` }}
                      />
                    </span>
                    <span className="w-14 text-right font-mono text-zinc-500">
                      {s.latency_ms.toFixed(0)}ms
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          </section>

          {message.sources.length > 0 && (
            <section>
              <h4 className="mb-2 text-[10px] font-medium uppercase tracking-wider text-zinc-500">
                Retrieved chunks (ranked)
              </h4>
              <ul className="space-y-1">
                {message.sources.map((s) => (
                  <li key={s.chunk_id}>
                    <button
                      onClick={() => onOpenSource(s)}
                      className={`flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 text-left text-xs transition hover:bg-white/[0.05] ${
                        s.used ? "bg-indigo-500/[0.07] ring-1 ring-inset ring-indigo-400/25" : ""
                      }`}
                    >
                      <span className="flex-1 truncate text-zinc-300" title={s.section}>
                        {s.section || s.source}
                      </span>
                      {s.via_graph && (
                        <span className="rounded bg-violet-500/20 px-1.5 py-0.5 text-[10px] text-violet-300">
                          graph
                        </span>
                      )}
                      {s.used && (
                        <span className="rounded bg-indigo-500/20 px-1.5 py-0.5 text-[10px] text-indigo-300">
                          used
                        </span>
                      )}
                      <span className="w-14 text-right font-mono text-zinc-500">
                        cos {s.score.toFixed(2)}
                      </span>
                      <span className="w-16 text-right font-mono text-zinc-500">
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
