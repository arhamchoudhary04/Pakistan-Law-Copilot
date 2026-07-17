"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { MessageBubble } from "./MessageBubble";
import { RetrievalInspector } from "./RetrievalInspector";
import { SourceDrawer } from "./SourceDrawer";
import { streamChat } from "@/lib/sse";
import { dirOf } from "@/lib/text";
import type { AssistantMessage, ChatTurn, SourceItem } from "@/lib/types";

const EXAMPLES = [
  "What are my rights if I am arrested by the police?",
  "On what grounds can a landlord evict a tenant?",
  "What are my rights if I bought a defective product?",
  "Kya mujhe taleem ka haq hasil hai?", // Roman Urdu: do I have the right to education?
  "What is the capital of France?", // triggers the honest refusal
];

// What the corpus currently covers — shown so users know the scope up front.
const COVERAGE = [
  "Fundamental Rights",
  "Penal Code (PPC)",
  "Criminal Procedure (CrPC)",
  "Family & Divorce",
  "Dowry",
  "Contracts",
  "Cybercrime (PECA)",
  "Workplace Harassment",
  "Right to Information",
  "Rent",
  "Consumer",
  "Employment",
];

function emptyAnswer(): AssistantMessage {
  return {
    text: "",
    stages: [],
    citations: [],
    sources: [],
    status: null,
    attempts: 1,
    streaming: true,
  };
}

export function ChatWindow() {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [drawerSource, setDrawerSource] = useState<SourceItem | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns]);

  // Update the answer of the last turn immutably.
  const patchLast = useCallback((fn: (a: AssistantMessage) => AssistantMessage) => {
    setTurns((prev) => {
      if (prev.length === 0) return prev;
      const next = prev.slice();
      const last = next[next.length - 1];
      next[next.length - 1] = { ...last, answer: fn(last.answer) };
      return next;
    });
  }, []);

  const ask = useCallback(
    async (question: string) => {
      const q = question.trim();
      if (!q || busy) return;
      setBusy(true);
      setInput("");
      setTurns((prev) => [...prev, { question: q, answer: emptyAnswer() }]);

      try {
        for await (const ev of streamChat(q)) {
          switch (ev.event) {
            case "stage":
              patchLast((a) => ({ ...a, stages: [...a.stages, ev.data] }));
              break;
            case "token":
              patchLast((a) => ({ ...a, text: a.text + ev.data.text }));
              break;
            case "citation":
              patchLast((a) => ({ ...a, citations: [...a.citations, ev.data] }));
              break;
            case "sources":
              patchLast((a) => ({ ...a, sources: ev.data.retrieved }));
              break;
            case "done":
              patchLast((a) => ({
                ...a,
                status: ev.data.answer_status,
                attempts: ev.data.attempts,
                streaming: false,
              }));
              break;
          }
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Request failed";
        patchLast((a) => ({
          ...a,
          streaming: false,
          error: msg,
          text: a.text || `Could not reach the API: ${msg}`,
        }));
      } finally {
        patchLast((a) => ({ ...a, streaming: false }));
        setBusy(false);
      }
    },
    [busy, patchLast],
  );

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="scroll-thin min-h-0 flex-1 space-y-7 overflow-y-auto py-5">
        {turns.length === 0 ? (
          <EmptyState onPick={ask} />
        ) : (
          turns.map((turn, i) => (
            <div key={i} className="animate-fade-in-up space-y-2.5">
              <div className="flex justify-end">
                <div
                  dir={dirOf(turn.question)}
                  className="max-w-[85%] rounded-2xl rounded-br-md bg-indigo-500 px-4 py-2.5 text-[15px] leading-relaxed text-white shadow-card"
                >
                  {turn.question}
                </div>
              </div>
              <MessageBubble message={turn.answer} onOpenSource={setDrawerSource} />
              <RetrievalInspector message={turn.answer} onOpenSource={setDrawerSource} />
            </div>
          ))
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void ask(input);
        }}
        className="pb-5 pt-2"
      >
        <div className="flex items-center gap-2 rounded-2xl border border-white/10 bg-white/[0.04] p-2 shadow-card transition focus-within:border-indigo-400/50 focus-within:shadow-glow">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            dir="auto"
            placeholder="Ask about your rights — English, Urdu, or Roman Urdu…"
            disabled={busy}
            className="flex-1 bg-transparent px-3 py-2 text-[15px] text-zinc-100 placeholder:text-zinc-500 focus:outline-none disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
            aria-label="Send"
            className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-indigo-500 text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy ? (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
                <path d="M12 19V5M5 12l7-7 7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </button>
        </div>
        <p className="mt-2 text-center text-[11px] text-zinc-600">
          Answers are grounded in cited law and may be incomplete — not legal advice.
        </p>
      </form>

      <SourceDrawer source={drawerSource} onClose={() => setDrawerSource(null)} />
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="mx-auto max-w-2xl px-1 pt-6 sm:pt-10">
      <div className="text-center">
        <h2 className="text-2xl font-semibold tracking-tight text-white sm:text-[26px]">
          Know your rights, with the source
        </h2>
        <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-zinc-400">
          Ask in plain language and get an answer grounded in Pakistani law, cited to the
          exact Article or Section — and an honest &ldquo;I don&apos;t know&rdquo; when the
          law doesn&apos;t cover it.
        </p>
      </div>

      <div className="mt-6 flex flex-wrap justify-center gap-1.5">
        {COVERAGE.map((c) => (
          <span
            key={c}
            className="rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-1 text-[11px] text-zinc-400"
          >
            {c}
          </span>
        ))}
      </div>

      <div className="mt-7 grid gap-2 sm:grid-cols-2">
        {EXAMPLES.map((q) => (
          <button
            key={q}
            onClick={() => onPick(q)}
            dir={dirOf(q)}
            className="group flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-left text-sm text-zinc-300 transition hover:border-indigo-400/40 hover:bg-white/[0.06] hover:text-white"
          >
            <span>{q}</span>
            <span className="shrink-0 text-zinc-600 transition group-hover:translate-x-0.5 group-hover:text-indigo-300">
              →
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
