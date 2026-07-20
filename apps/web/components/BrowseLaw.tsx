"use client";

import { useState } from "react";
import { TOPICS } from "@/lib/topics";

/** "Browse the law": statutes grouped into everyday topics, each with example questions. */
export function BrowseLaw({ onAsk }: { onAsk: (q: string) => void }) {
  const [openId, setOpenId] = useState<string | null>(TOPICS[0]?.id ?? null);

  return (
    <div className="scroll-thin h-full overflow-y-auto py-8">
      <div className="animate-fade-in-up">
        <h2 className="font-display text-[30px] font-medium leading-tight tracking-tight text-ink sm:text-[36px]">
          Browse the law
        </h2>
        <p className="mt-3 max-w-lg text-[15px] leading-relaxed text-muted">
          {TOPICS.length} everyday topics, drawn from the statutes in the corpus. Pick a
          question to ask it, or explore what each area covers.
        </p>

        <ul className="mt-7 divide-y divide-line border-y border-line">
          {TOPICS.map((t) => {
            const open = openId === t.id;
            return (
              <li key={t.id}>
                <button
                  onClick={() => setOpenId(open ? null : t.id)}
                  className="flex w-full items-center gap-4 py-4 text-left"
                  aria-expanded={open}
                >
                  <div className="min-w-0 flex-1">
                    <span className="font-display text-[18px] font-medium text-ink">
                      {t.title}
                    </span>
                    <p className="mt-0.5 truncate text-[13px] text-muted">{t.blurb}</p>
                  </div>
                  <span
                    className={`shrink-0 text-faint transition-transform duration-200 ${
                      open ? "rotate-90 text-accent" : ""
                    }`}
                  >
                    ›
                  </span>
                </button>

                {open && (
                  <div className="animate-fade-in-up pb-5">
                    <ul className="space-y-1.5">
                      {t.examples.map((q) => (
                        <li key={q}>
                          <button
                            onClick={() => onAsk(q)}
                            className="group flex w-full items-center justify-between gap-3 rounded-lg border border-line bg-card px-3.5 py-2.5 text-left transition hover:border-accent/40 hover:bg-accent/[0.03]"
                          >
                            <span className="text-[14px] leading-snug text-ink/90 transition group-hover:text-accent">
                              {q}
                            </span>
                            <span className="shrink-0 text-faint transition group-hover:translate-x-0.5 group-hover:text-accent">
                              →
                            </span>
                          </button>
                        </li>
                      ))}
                    </ul>
                    <div className="mt-3 flex flex-wrap items-center gap-1.5">
                      <span className="text-[10px] uppercase tracking-[0.16em] text-faint">
                        Source
                      </span>
                      {t.acts.map((a) => (
                        <span
                          key={a}
                          className="rounded-md border border-line bg-surface px-2 py-0.5 text-[11px] text-muted"
                        >
                          {a}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
