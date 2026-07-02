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
        className={`fixed inset-0 z-40 bg-black/50 transition-opacity ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />
      <aside
        className={`fixed right-0 top-0 z-50 h-full w-full max-w-md overflow-y-auto border-l border-slate-800 bg-slate-900 p-5 shadow-2xl transition-transform scroll-thin ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {source && (
          <div className="space-y-4">
            <div className="flex items-start justify-between gap-4">
              <h2 className="text-sm font-semibold text-slate-200">Source</h2>
              <button
                onClick={onClose}
                className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            <div>
              <div className="text-xs uppercase tracking-wide text-slate-500">Document</div>
              <div className="mt-1 font-mono text-sm text-sky-300">{source.source}</div>
            </div>

            {source.section && (
              <div>
                <div className="text-xs uppercase tracking-wide text-slate-500">Section</div>
                <div className="mt-1 text-sm text-slate-300">{source.section}</div>
              </div>
            )}

            <div className="flex gap-3">
              <ScorePill label="cosine" value={source.score} />
              {source.rerank_score !== null && (
                <ScorePill label="rerank" value={source.rerank_score} />
              )}
            </div>

            <div className="rounded-md bg-slate-800/60 p-3 font-mono text-xs text-slate-400">
              chunk id: {source.chunk_id}
            </div>
          </div>
        )}
      </aside>
    </>
  );
}

function ScorePill({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md bg-slate-800 px-3 py-1.5">
      <div className="text-[10px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className="text-sm font-semibold text-slate-200">{value.toFixed(3)}</div>
    </div>
  );
}
