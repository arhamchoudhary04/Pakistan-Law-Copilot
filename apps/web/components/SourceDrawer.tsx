"use client";

import type { SourceItem } from "@/lib/types";

/**
 * Right-side drawer showing the exact source chunk behind a citation:
 * its document, section breadcrumb, and retrieval scores.
 */
export function SourceDrawer({
  source,
  onClose,
}: {
  source: SourceItem | null;
  onClose: () => void;
}) {
  const open = source !== null;
  return (
    <>
      <div
        onClick={onClose}
        className={`fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity duration-300 ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />
      <aside
        className={`scroll-thin fixed right-0 top-0 z-50 h-full w-full max-w-md overflow-y-auto border-l border-white/10 bg-[#0f0f13] p-6 shadow-2xl transition-transform duration-300 ease-out ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {source && (
          <div className="space-y-5">
            <div className="flex items-start justify-between gap-4">
              <h2 className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
                Source
              </h2>
              <button
                onClick={onClose}
                className="grid h-7 w-7 place-items-center rounded-lg text-zinc-400 transition hover:bg-white/10 hover:text-zinc-100"
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            {source.section && (
              <div>
                <div className="text-[11px] uppercase tracking-wider text-zinc-500">Provision</div>
                <div className="mt-1 text-[15px] font-medium leading-snug text-white">
                  {source.section.split(">").pop()?.trim()}
                </div>
              </div>
            )}

            <div>
              <div className="text-[11px] uppercase tracking-wider text-zinc-500">Document</div>
              <div className="mt-1 font-mono text-sm text-indigo-300">{source.source}</div>
            </div>

            <div className="flex flex-wrap gap-2">
              <ScorePill label="cosine" value={source.score} />
              {source.rerank_score !== null && (
                <ScorePill label="rerank" value={source.rerank_score} />
              )}
              {source.used && (
                <div className="rounded-lg bg-indigo-500/15 px-3 py-1.5 text-sm font-medium text-indigo-300 ring-1 ring-inset ring-indigo-400/30">
                  cited in answer
                </div>
              )}
              {source.via_graph && (
                <div className="rounded-lg bg-violet-500/15 px-3 py-1.5 text-sm font-medium text-violet-300 ring-1 ring-inset ring-violet-400/30">
                  via graph
                </div>
              )}
            </div>

            <div className="rounded-lg border border-white/[0.06] bg-white/[0.03] p-3 font-mono text-[11px] text-zinc-500">
              {source.chunk_id}
            </div>
          </div>
        )}
      </aside>
    </>
  );
}

function ScorePill({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-white/[0.06] bg-white/[0.03] px-3 py-1.5">
      <div className="text-[10px] uppercase tracking-wider text-zinc-500">{label}</div>
      <div className="text-sm font-semibold tabular-nums text-zinc-100">{value.toFixed(3)}</div>
    </div>
  );
}
