"use client";

import { useCallback, useRef, useState } from "react";
import { BrowseLaw } from "./BrowseLaw";
import { ChatWindow } from "./ChatWindow";
import { HomeView } from "./HomeView";

type View = "home" | "browse" | "ask";

const NAV: { id: View; label: string }[] = [
  { id: "home", label: "Home" },
  { id: "browse", label: "Browse law" },
  { id: "ask", label: "Ask" },
];

/**
 * Top-level app shell: a masthead + view navigation over three views (Home,
 * Browse law, Ask). The chat stays mounted across navigation so a conversation
 * is never lost, and questions picked on Home/Browse deep-link into it.
 */
export function AppShell() {
  const [view, setView] = useState<View>("home");
  const [seed, setSeed] = useState<{ q: string; id: number } | undefined>();
  const seedId = useRef(0);

  const ask = useCallback((q: string) => {
    seedId.current += 1;
    setSeed({ q, id: seedId.current });
    setView("ask");
  }, []);

  return (
    <main className="mx-auto flex h-[100dvh] max-w-2xl flex-col px-5">
      <header className="pt-6">
        <div className="flex items-center justify-between gap-4">
          <button
            onClick={() => setView("home")}
            className="font-display text-[22px] font-semibold leading-none tracking-tight text-ink transition hover:text-accent"
          >
            Pakistan Law Copilot
          </button>
          <nav className="flex items-center gap-1">
            {NAV.map((item) => (
              <button
                key={item.id}
                onClick={() => setView(item.id)}
                className={`rounded-full px-3 py-1.5 text-[13px] transition ${
                  view === item.id
                    ? "bg-accent/10 font-medium text-accent"
                    : "text-muted hover:text-ink"
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </div>
        <div className="mt-3.5 flex items-center gap-2 border-t border-line pt-2.5">
          <span className="h-1 w-1 rounded-full bg-accent" />
          <p className="text-[11px] text-muted">
            Legal information, not legal advice — grounded in cited statutes, and may be
            incomplete. Verify against the source and consult a lawyer.
          </p>
        </div>
      </header>

      <div className="min-h-0 flex-1">
        {view === "home" && <HomeView onStartAsk={() => setView("ask")} onBrowse={() => setView("browse")} />}
        {view === "browse" && <BrowseLaw onAsk={ask} />}
        {/* Kept mounted so the conversation persists across navigation. */}
        <div className={view === "ask" ? "h-full" : "hidden"}>
          <ChatWindow seed={seed} />
        </div>
      </div>
    </main>
  );
}
