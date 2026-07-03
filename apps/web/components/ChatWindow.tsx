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
      <div ref={scrollRef} className="scroll-thin flex-1 space-y-6 overflow-y-auto px-4 py-6">
        {turns.length === 0 ? (
          <EmptyState onPick={ask} />
        ) : (
          turns.map((turn, i) => (
            <div key={i} className="space-y-2">
              <div className="flex justify-end">
                <div
                  dir={dirOf(turn.question)}
                  className="max-w-[85%] rounded-2xl rounded-tr-sm bg-sky-600 px-4 py-2.5 text-[15px] text-white"
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
        className="border-t border-slate-800 bg-slate-950/80 p-4 backdrop-blur"
      >
        <div className="mx-auto flex max-w-3xl items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            dir="auto"
            placeholder="Ask about your rights (English, Urdu, or Roman Urdu)…"
            disabled={busy}
            className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-[15px] text-slate-100 placeholder:text-slate-500 focus:border-sky-500 focus:outline-none disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
            className="rounded-xl bg-sky-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? "…" : "Ask"}
          </button>
        </div>
      </form>

      <SourceDrawer source={drawerSource} onClose={() => setDrawerSource(null)} />
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="mx-auto max-w-3xl pt-10 text-center">
      <h2 className="text-lg font-semibold text-slate-200">Ask about your rights</h2>
      <p className="mt-1 text-sm text-slate-500">
        Answers are grounded in Pakistani law (Constitution — Fundamental Rights, and
        PECA 2016), cited to the exact provision, and refused when the law doesn&apos;t
        cover it. Try one:
      </p>
      <div className="mt-5 grid gap-2 sm:grid-cols-2">
        {EXAMPLES.map((q) => (
          <button
            key={q}
            onClick={() => onPick(q)}
            className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 text-left text-sm text-slate-300 transition hover:border-sky-600 hover:text-slate-100"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
