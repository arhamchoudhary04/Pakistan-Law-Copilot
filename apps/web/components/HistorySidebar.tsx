"use client";

import { useAuth } from "./AuthProvider";
import type { ConversationSummary } from "@/lib/api";

/**
 * Left sidebar: start a new chat, revisit or delete past conversations, and sign
 * out. Conversations are the current user's own, newest first.
 */
export function HistorySidebar({
  conversations,
  activeId,
  onNew,
  onSelect,
  onDelete,
}: {
  conversations: ConversationSummary[];
  activeId: string | null;
  onNew: () => void;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const { user, logout } = useAuth();

  return (
    <div className="flex h-full flex-col">
      <button
        onClick={onNew}
        className="m-3 flex items-center justify-center gap-2 rounded-xl border border-line bg-card px-3 py-2.5 text-[13px] font-medium text-ink shadow-paper transition hover:border-accent/40 hover:text-accent"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden>
          <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        New chat
      </button>

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-2">
        {conversations.length === 0 ? (
          <p className="px-2 py-6 text-[12px] leading-relaxed text-faint">
            No conversations yet. Ask a question and it&apos;ll be saved here.
          </p>
        ) : (
          <ul className="space-y-0.5 pb-2">
            {conversations.map((c) => (
              <li key={c.id}>
                <div
                  className={`group flex items-center gap-1 rounded-lg pr-1 transition ${
                    activeId === c.id ? "bg-accent/10" : "hover:bg-surface"
                  }`}
                >
                  <button
                    onClick={() => onSelect(c.id)}
                    className="min-w-0 flex-1 truncate px-2.5 py-2 text-left text-[13px] text-ink/85"
                    title={c.title}
                  >
                    {c.title}
                  </button>
                  <button
                    onClick={() => onDelete(c.id)}
                    aria-label="Delete conversation"
                    className="shrink-0 rounded-md p-1 text-faint opacity-0 transition hover:text-accent group-hover:opacity-100"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
                      <path
                        d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m2 0v12a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V7"
                        stroke="currentColor"
                        strokeWidth="1.6"
                        strokeLinecap="round"
                      />
                    </svg>
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex items-center gap-2 border-t border-line p-3">
        <div className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-accent/12 text-[12px] font-semibold text-accent">
          {(user?.name || user?.email || "?").charAt(0).toUpperCase()}
        </div>
        <span className="min-w-0 flex-1 truncate text-[12px] text-muted" title={user?.email}>
          {user?.name || user?.email}
        </span>
        <button
          onClick={logout}
          className="shrink-0 rounded-md px-2 py-1 text-[12px] text-muted transition hover:text-accent"
        >
          Sign out
        </button>
      </div>
    </div>
  );
}
