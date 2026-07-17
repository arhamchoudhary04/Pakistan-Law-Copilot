"use client";

import type { SourceItem } from "@/lib/types";

/**
 * Right-side drawer showing the exact source provision behind a citation:
 * its title, document, and retrieval scores.
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
        className={`fixed inset-0 z-40 bg-ink/25 backdrop-blur-[2px] transition-opacity duration-300 ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />
      <aside
        className={`scroll-thin fixed right-0 top-0 z-50 h-full w-full max-w-md overflow-y-auto border-l border-line bg-paper p-6 shadow-lift transition-transform duration-300 ease-out ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {source && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-medium uppercase tracking-[0.2em] text-faint">
                Source
              </span>
              <button
                onClick={onClose}
                className="grid h-7 w-7 place-items-center rounded-lg text-muted transition hover:bg-surface hover:text-ink"
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            {source.section && (
              <h2 className="font-display text-2xl font-medium leading-tight tracking-tight text-ink">
                {source.section.split(">").pop()?.trim()}
              </h2>
            )}

            <div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-faint">Document</div>
              <div className="mt-1 font-mono text-[13px] text-accent">{source.source}</div>
            </div>

            <div className="flex flex-wrap gap-2">
              <ScorePill label="cosine" value={source.score} />
              {source.rerank_score !== null && (
                <ScorePill label="rerank" value={source.rerank_score} />
              )}
              {source.used && (
                <div className="rounded-lg bg-accent/12 px-3 py-1.5 text-sm font-medium text-accent">
                  cited in answer
                </div>
              )}
              {source.via_graph && (
                <div className="rounded-lg border border-line bg-surface px-3 py-1.5 text-sm text-muted">
                  found via graph
                </div>
              )}
            </div>

            <div className="rounded-lg border border-line bg-surface p-3 font-mono text-[11px] text-muted">
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
    <div className="rounded-lg border border-line bg-card px-3 py-1.5">
      <div className="text-[10px] uppercase tracking-[0.18em] text-faint">{label}</div>
      <div className="text-sm font-semibold tabular-nums text-ink">{value.toFixed(3)}</div>
    </div>
  );
}
