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
    <div className="mt-2 rounded-xl border border-slate-800 bg-slate-900/50">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-2.5 text-left text-xs font-medium text-slate-400 hover:text-slate-200"
      >
        <span>
          Retrieval inspector · {message.stages.length} stages ·{" "}
          {message.sources.length} chunks
        </span>
        <span className={`transition-transform ${open ? "rotate-90" : ""}`}>›</span>
      </button>

      {open && (
        <div className="space-y-4 border-t border-slate-800 px-4 py-3">
          <section>
            <h4 className="mb-2 text-[10px] uppercase tracking-wide text-slate-500">
              Pipeline stages
            </h4>
            <ul className="space-y-1.5">
              {message.stages.map((s, i) => (
                <li key={i} className="flex items-center gap-3 text-xs">
                  <span className="w-16 shrink-0 font-mono text-sky-300">{s.stage}</span>
                  <span className="flex-1 truncate text-slate-400" title={s.detail}>
                    {s.detail}
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="h-1 w-16 overflow-hidden rounded bg-slate-800">
                      <span
                        className="block h-full bg-sky-500/60"
                        style={{ width: `${(s.latency_ms / maxLatency) * 100}%` }}
                      />
                    </span>
                    <span className="w-14 text-right font-mono text-slate-500">
                      {s.latency_ms.toFixed(0)}ms
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          </section>

          {message.sources.length > 0 && (
            <section>
              <h4 className="mb-2 text-[10px] uppercase tracking-wide text-slate-500">
                Retrieved chunks (ranked)
              </h4>
              <ul className="space-y-1">
                {message.sources.map((s) => (
                  <li key={s.chunk_id}>
                    <button
                      onClick={() => onOpenSource(s)}
                      className={`flex w-full items-center gap-3 rounded-md px-2 py-1.5 text-left text-xs hover:bg-slate-800 ${
                        s.used ? "ring-1 ring-sky-500/30" : ""
                      }`}
                    >
                      <span className="flex-1 truncate text-slate-300" title={s.section}>
                        {s.section || s.source}
                      </span>
                      {s.used && (
                        <span className="rounded bg-sky-500/20 px-1.5 text-[10px] text-sky-300">
                          used
                        </span>
                      )}
                      <span className="w-14 text-right font-mono text-slate-500">
                        cos {s.score.toFixed(2)}
                      </span>
                      <span className="w-16 text-right font-mono text-slate-500">
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
