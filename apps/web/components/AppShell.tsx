"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AuthScreen } from "./AuthScreen";
import { useAuth } from "./AuthProvider";
import { BrowseLaw } from "./BrowseLaw";
import { ChatWindow } from "./ChatWindow";
import { HistorySidebar } from "./HistorySidebar";
import { HomeView } from "./HomeView";
import {
  deleteConversation,
  getConversation,
  listConversations,
  type ConversationSummary,
} from "@/lib/api";
import { turnsFromMessages } from "@/lib/history";
import type { ChatTurn } from "@/lib/types";

type View = "home" | "browse" | "ask";

const NAV: { id: View; label: string }[] = [
  { id: "home", label: "Home" },
  { id: "browse", label: "Browse law" },
  { id: "ask", label: "Ask" },
];

/** Root: gate on auth, then render the app with per-user chat history. */
export function AppShell() {
  const { ready, user } = useAuth();
  if (!ready) {
    return (
      <div className="grid h-[100dvh] place-items-center">
        <span className="h-6 w-6 animate-spin rounded-full border-2 border-line-strong border-t-accent" />
      </div>
    );
  }
  if (!user) return <AuthScreen />;
  return <Workspace />;
}

function Workspace() {
  const { token } = useAuth();
  const authToken = token as string;

  const [view, setView] = useState<View>("home");
  const [seed, setSeed] = useState<{ q: string; id: number } | undefined>();
  const seedId = useRef(0);

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [loadedTurns, setLoadedTurns] = useState<ChatTurn[]>([]);
  const [chatKey, setChatKey] = useState(0);
  const [mobileNav, setMobileNav] = useState(false);

  const refreshList = useCallback(() => {
    listConversations(authToken)
      .then(setConversations)
      .catch(() => setConversations([]));
  }, [authToken]);

  useEffect(() => {
    refreshList();
  }, [refreshList]);

  // Start a brand-new chat (optionally seeded with a question from Home/Browse).
  const newChat = useCallback((question?: string) => {
    setActiveId(null);
    setLoadedTurns([]);
    setChatKey((k) => k + 1);
    if (question) {
      seedId.current += 1;
      setSeed({ q: question, id: seedId.current });
    } else {
      setSeed(undefined);
    }
    setView("ask");
    setMobileNav(false);
  }, []);

  const openConversation = useCallback(
    async (id: string) => {
      setMobileNav(false);
      try {
        const detail = await getConversation(id, authToken);
        setLoadedTurns(turnsFromMessages(detail.messages));
        setActiveId(id);
        setSeed(undefined);
        setChatKey((k) => k + 1);
        setView("ask");
      } catch {
        refreshList(); // likely deleted elsewhere
      }
    },
    [authToken, refreshList],
  );

  const removeConversation = useCallback(
    async (id: string) => {
      try {
        await deleteConversation(id, authToken);
      } catch {
        /* ignore */
      }
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (id === activeId) newChat();
    },
    [authToken, activeId, newChat],
  );

  const onConversationCreated = useCallback((summary: ConversationSummary) => {
    setConversations((prev) => [summary, ...prev.filter((c) => c.id !== summary.id)]);
    setActiveId(summary.id);
  }, []);

  // Home and Browse are content pages and use the full width; the chat keeps a
  // narrow measure, because a 1,200px line of legal prose is unreadable.
  const columnWidth = view === "ask" ? "max-w-3xl" : "max-w-6xl";

  return (
    <div className="flex h-[100dvh]">
      {/* Desktop sidebar */}
      <aside className="hidden w-[268px] shrink-0 border-r border-line bg-surface md:block">
        <HistorySidebar
          conversations={conversations}
          activeId={activeId}
          onNew={() => newChat()}
          onSelect={openConversation}
          onDelete={removeConversation}
        />
      </aside>

      {/* Mobile sidebar drawer */}
      {mobileNav && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-[2px]"
            onClick={() => setMobileNav(false)}
          />
          <div className="absolute left-0 top-0 h-full w-[280px] border-r border-line bg-surface shadow-lift">
            <HistorySidebar
              conversations={conversations}
              activeId={activeId}
              onNew={() => newChat()}
              onSelect={openConversation}
              onDelete={removeConversation}
            />
          </div>
        </div>
      )}

      {/* Main column */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 border-b border-line bg-canvas/85 backdrop-blur-xl">
          <div
            className={`mx-auto flex ${columnWidth} items-center justify-between gap-3 px-5 py-3.5`}
          >
            <div className="flex min-w-0 items-center gap-2.5">
              <button
                onClick={() => setMobileNav(true)}
                aria-label="Open history"
                className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-muted transition hover:bg-elevated hover:text-ink md:hidden"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </button>
              <button
                onClick={() => setView("home")}
                className="group flex min-w-0 items-center gap-2.5"
              >
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-accent/30 bg-sheen font-display text-[15px] font-semibold text-accent">
                  §
                </span>
                <span className="truncate text-left">
                  <span className="block truncate font-display text-[17px] font-semibold leading-none tracking-tight text-ink transition group-hover:text-accent">
                    Pakistan Law Copilot
                  </span>
                  <span className="mt-1 block text-[10px] uppercase tracking-[0.18em] text-faint">
                    Cited. Or it says no.
                  </span>
                </span>
              </button>
            </div>
            <nav className="flex shrink-0 items-center gap-1 rounded-full border border-line bg-surface p-1">
              {NAV.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setView(item.id)}
                  className={`rounded-full px-3 py-1.5 text-[13px] transition ${
                    view === item.id
                      ? "bg-elevated font-medium text-accent shadow-paper"
                      : "text-muted hover:text-ink"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </nav>
          </div>
        </header>

        <div className={`mx-auto min-h-0 w-full ${columnWidth} flex-1 px-5`}>
          {view === "home" && (
            <HomeView
              onStartAsk={() => newChat()}
              onBrowse={() => setView("browse")}
              onAsk={(q) => newChat(q)}
            />
          )}
          {view === "browse" && <BrowseLaw onAsk={(q) => newChat(q)} />}
          {/* Kept mounted so navigating Home/Browse never drops the conversation;
              remounts (via key) only when a different conversation is opened. */}
          <div className={view === "ask" ? "h-full" : "hidden"}>
            <ChatWindow
              key={chatKey}
              seed={seed}
              conversationId={activeId}
              initialTurns={loadedTurns}
              token={authToken}
              onConversationCreated={onConversationCreated}
              onSaved={refreshList}
            />
          </div>
        </div>

        {/* Kept on every view: the disclaimer has to be present, not just on Home. */}
        <footer className="shrink-0 border-t border-line bg-surface/60">
          <p
            className={`mx-auto ${columnWidth} px-5 py-2.5 text-[11px] leading-relaxed text-faint`}
          >
            <span className="mr-1.5 inline-block h-1 w-1 -translate-y-[2px] rounded-full bg-accent/70" />
            Legal information, not legal advice. Answers are drawn from a limited corpus and
            may be incomplete. Verify against the cited source and consult a lawyer.
          </p>
        </footer>
      </div>
    </div>
  );
}
