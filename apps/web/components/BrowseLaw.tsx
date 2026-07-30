"use client";

import { useState } from "react";
import { TOPICS } from "@/lib/topics";

/** "Browse the law": statutes grouped into everyday topics, each with example questions.
 *  Master/detail rather than an accordion, so the wide layout stays filled. */
export function BrowseLaw({ onAsk }: { onAsk: (q: string) => void }) {
  const [selectedId, setSelectedId] = useState<string>(TOPICS[0]?.id ?? "");
  const topic = TOPICS.find((t) => t.id === selectedId) ?? TOPICS[0];

  return (
    <div className="scroll-thin h-full overflow-y-auto pb-10 pt-8">
      <div className="animate-fade-in-up">
        <h2 className="font-display text-[30px] font-medium leading-tight tracking-tight text-ink sm:text-[36px]">
          Browse the law
        </h2>
        <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-muted">
          {TOPICS.length} everyday topics, drawn from the statutes in the corpus. Pick a
          question to ask it, or explore what each area covers.
        </p>

        <div className="mt-8 grid gap-6 lg:grid-cols-[300px_minmax(0,1fr)]">
          {/* Topic list */}
          <nav className="scroll-thin lg:max-h-[calc(100dvh-320px)] lg:overflow-y-auto lg:pr-1">
            <ul className="space-y-1">
              {TOPICS.map((t) => {
                const active = t.id === topic?.id;
                return (
                  <li key={t.id}>
                    <button
                      onClick={() => setSelectedId(t.id)}
                      aria-current={active}
                      className={`w-full rounded-xl border px-3.5 py-3 text-left transition ${
                        active
                          ? "border-accent/35 bg-card bg-sheen shadow-paper"
                          : "border-transparent hover:border-line hover:bg-surface"
                      }`}
                    >
                      <span
                        className={`block text-[14px] font-medium ${
                          active ? "text-accent" : "text-ink"
                        }`}
                      >
                        {t.title}
                      </span>
                      <span className="mt-0.5 block truncate text-[12px] text-faint">
                        {t.acts.length === 1 ? t.acts[0] : `${t.acts.length} statutes`}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>

          {/* Detail */}
          {topic && (
            <section
              key={topic.id}
              className="animate-fade-in-up rounded-2xl border border-line bg-card p-6 shadow-paper"
            >
              <h3 className="font-display text-[24px] font-medium leading-tight text-ink">
                {topic.title}
              </h3>
              <p className="mt-2 text-[14px] leading-relaxed text-muted">{topic.blurb}</p>

              <div className="mt-5 flex flex-wrap items-center gap-1.5">
                <span className="mr-1 text-[10px] uppercase tracking-[0.16em] text-faint">
                  Source
                </span>
                {topic.acts.map((a) => (
                  <span
                    key={a}
                    className="rounded-md border border-line bg-surface px-2 py-0.5 text-[11px] text-muted"
                  >
                    {a}
                  </span>
                ))}
              </div>

              <div className="mt-6 h-px bg-line" />

              <p className="mt-5 text-[10px] font-medium uppercase tracking-[0.2em] text-faint">
                Ask one of these
              </p>
              <ul className="mt-3 space-y-2">
                {topic.examples.map((q) => (
                  <li key={q}>
                    <button
                      onClick={() => onAsk(q)}
                      className="group flex w-full items-center justify-between gap-3 rounded-xl border border-line bg-surface px-4 py-3 text-left transition hover:border-accent/40 hover:bg-elevated"
                    >
                      <span className="text-[14px] leading-snug text-ink/90 transition group-hover:text-accent">
                        {q}
                      </span>
                      <span className="shrink-0 text-faint transition group-hover:translate-x-0.5 group-hover:text-accent">
                        &rarr;
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
