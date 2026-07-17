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
  "What is the punishment for theft under the Penal Code?",
  "Kya mujhe taleem ka haq hasil hai?", // Roman Urdu: do I have the right to education?
  "What is the capital of France?", // triggers the honest refusal
];

const COVERAGE = [
  "Fundamental Rights",
  "Penal Code",
  "Criminal Procedure",
  "Family & Divorce",
  "Dowry",
  "Contracts",
  "Cybercrime",
  "Harassment",
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
  const turnsRef = useRef<ChatTurn[]>([]);

  useEffect(() => {
    turnsRef.current = turns;
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns]);

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
      // Recent completed turns → follow-up context (kept short).
      const history = turnsRef.current
        .filter((t) => t.answer.text && !t.answer.streaming && !t.answer.error)
        .slice(-4)
        .map((t) => ({ question: t.question, answer: t.answer.text }));
      setBusy(true);
      setInput("");
      setTurns((prev) => [...prev, { question: q, answer: emptyAnswer() }]);

      try {
        for await (const ev of streamChat(q, history)) {
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
      <div ref={scrollRef} className="scroll-thin min-h-0 flex-1 overflow-y-auto py-6">
        {turns.length === 0 ? (
          <EmptyState onPick={ask} />
        ) : (
          <div className="space-y-9">
            {turns.map((turn, i) => (
              <article key={i} className="animate-fade-in-up space-y-3">
                <div className="flex justify-end">
                  <p
                    dir={dirOf(turn.question)}
                    className="max-w-[82%] rounded-2xl rounded-br-md bg-surface px-4 py-2.5 text-[15px] leading-relaxed text-ink"
                  >
                    {turn.question}
                  </p>
                </div>
                <MessageBubble message={turn.answer} onOpenSource={setDrawerSource} />
                <RetrievalInspector message={turn.answer} onOpenSource={setDrawerSource} />
              </article>
            ))}
          </div>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void ask(input);
        }}
        className="pb-5 pt-3"
      >
        <div className="flex items-center gap-2 rounded-2xl border border-line bg-card p-2 shadow-paper transition focus-within:border-accent/40">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            dir="auto"
            placeholder="Ask about your rights — English, Urdu, or Roman Urdu…"
            disabled={busy}
            className="flex-1 bg-transparent px-3 py-2 text-[15px] text-ink placeholder:text-faint focus:outline-none disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
            aria-label="Send"
            className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-accent text-white transition hover:bg-[#6a2523] disabled:cursor-not-allowed disabled:opacity-40"
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
      </form>

      <SourceDrawer source={drawerSource} onClose={() => setDrawerSource(null)} />
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="mx-auto max-w-xl pt-8 sm:pt-12">
      <h2 className="font-display text-[34px] font-medium leading-[1.08] tracking-tight text-ink sm:text-[42px]">
        Know your rights,
        <br />
        <span className="text-accent">with the source.</span>
      </h2>
      <p className="mt-5 max-w-md text-[15px] leading-relaxed text-muted">
        Ask in plain language — English, Urdu, or Roman Urdu — and get an answer grounded
        in Pakistani law, cited to the exact Article or Section, with an honest
        &ldquo;I don&apos;t know&rdquo; when the law doesn&apos;t cover it.
      </p>

      <p className="mt-8 text-[10px] font-medium uppercase tracking-[0.2em] text-faint">Covers</p>
      <p className="mt-2 text-[13px] leading-relaxed text-muted">{COVERAGE.join("  ·  ")}</p>

      <p className="mt-8 text-[10px] font-medium uppercase tracking-[0.2em] text-faint">
        Try asking
      </p>
      <ul className="mt-1 divide-y divide-line border-y border-line">
        {EXAMPLES.map((q) => (
          <li key={q}>
            <button
              onClick={() => onPick(q)}
              dir={dirOf(q)}
              className="group flex w-full items-center justify-between gap-4 py-3.5 text-left"
            >
              <span className="text-[15px] leading-snug text-ink/90 transition group-hover:text-accent">
                {q}
              </span>
              <span className="shrink-0 text-faint transition group-hover:translate-x-0.5 group-hover:text-accent">
                →
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
