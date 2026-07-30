"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { MessageBubble } from "./MessageBubble";
import { RetrievalInspector } from "./RetrievalInspector";
import { SourceDrawer } from "./SourceDrawer";
import { streamChat } from "@/lib/sse";
import {
  createConversation,
  saveTurn,
  uploadDocument,
  type ConversationSummary,
  type UploadedDoc,
} from "@/lib/api";
import { dirOf } from "@/lib/text";
import type { AssistantMessage, CitationEvent, ChatTurn, SourceItem } from "@/lib/types";

const EXAMPLES = [
  "What are my rights if I am arrested by the police?",
  "How does a court decide who gets custody of a child?",
  "What is the punishment for falsely accusing someone of a crime?",
  "Kya mujhe taleem ka haq hasil hai?", // Roman Urdu: do I have the right to education?
  "What is the capital of France?", // triggers the honest refusal
];

const COVERAGE = [
  "Fundamental Rights",
  "Penal Code",
  "Criminal Procedure",
  "Family & Divorce",
  "Child Custody",
  "Guardianship",
  "False Accusation",
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

export function ChatWindow({
  seed,
  conversationId = null,
  initialTurns,
  token,
  onConversationCreated,
  onSaved,
}: {
  seed?: { q: string; id: number };
  conversationId?: string | null;
  initialTurns?: ChatTurn[];
  token: string;
  onConversationCreated?: (summary: ConversationSummary) => void;
  onSaved?: () => void;
}) {
  const [turns, setTurns] = useState<ChatTurn[]>(initialTurns ?? []);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [drawerSource, setDrawerSource] = useState<SourceItem | null>(null);
  const [doc, setDoc] = useState<UploadedDoc | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const turnsRef = useRef<ChatTurn[]>(initialTurns ?? []);
  const docRef = useRef<UploadedDoc | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  // The conversation this chat saves into. Set lazily on the first question.
  const convIdRef = useRef<string | null>(conversationId);
  // `busy` state drives the UI, but it cannot gate re-entry: two calls in the same
  // commit both read the pre-update value, so a second one slips through. StrictMode
  // invokes the seed effect twice on mount and used to fire the question twice.
  const busyRef = useRef(false);
  // Which seed id has already been submitted, so a re-run of the effect is a no-op.
  const seedRef = useRef<number | null>(null);

  useEffect(() => {
    docRef.current = doc;
  }, [doc]);

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
      if (!q || busyRef.current) return;
      busyRef.current = true;
      // Recent completed turns → follow-up context (kept short).
      const history = turnsRef.current
        .filter((t) => t.answer.text && !t.answer.streaming && !t.answer.error)
        .slice(-4)
        .map((t) => ({ question: t.question, answer: t.answer.text }));
      setBusy(true);
      setInput("");
      setTurns((prev) => [...prev, { question: q, answer: emptyAnswer() }]);

      // Uploaded-document chats are ephemeral (the doc lives only in memory), so
      // only the law-corpus conversation is persisted to the user's history.
      const persist = !docRef.current;
      if (persist && !convIdRef.current) {
        try {
          const summary = await createConversation(q.slice(0, 80), token);
          convIdRef.current = summary.id;
          onConversationCreated?.(summary);
        } catch {
          /* couldn't create, so answer anyway and don't persist this turn */
        }
      }

      // Accumulate the finished answer locally so we can persist it after streaming.
      let text = "";
      const citations: CitationEvent[] = [];
      let sources: SourceItem[] = [];
      let status: AssistantMessage["status"] = null;
      let attempts = 1;
      try {
        for await (const ev of streamChat(q, history, docRef.current?.doc_id ?? null)) {
          switch (ev.event) {
            case "stage":
              patchLast((a) => ({ ...a, stages: [...a.stages, ev.data] }));
              break;
            case "token":
              text += ev.data.text;
              patchLast((a) => ({ ...a, text: a.text + ev.data.text }));
              break;
            case "citation":
              citations.push(ev.data);
              patchLast((a) => ({ ...a, citations: [...a.citations, ev.data] }));
              break;
            case "sources":
              sources = ev.data.retrieved;
              patchLast((a) => ({ ...a, sources: ev.data.retrieved }));
              break;
            case "done":
              status = ev.data.answer_status;
              attempts = ev.data.attempts;
              patchLast((a) => ({
                ...a,
                status: ev.data.answer_status,
                attempts: ev.data.attempts,
                streaming: false,
              }));
              break;
          }
        }
        if (persist && convIdRef.current && status) {
          try {
            await saveTurn(
              convIdRef.current,
              { question: q, answer: text, meta: { status, attempts, citations, sources } },
              token,
            );
            onSaved?.();
          } catch {
            /* non-fatal: the answer is shown even if saving history fails */
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
        busyRef.current = false;
        setBusy(false);
      }
    },
    [patchLast, token, onConversationCreated, onSaved],
  );

  const onFile = useCallback(async (file: File | undefined) => {
    if (!file) return;
    setUploadError(null);
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadError("Only PDF files are supported.");
      return;
    }
    setUploading(true);
    try {
      const uploaded = await uploadDocument(file);
      setDoc(uploaded);
      // Fresh conversation for the new document; law-corpus turns don't apply.
      setTurns([]);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }, []);

  const clearDoc = useCallback(() => {
    setDoc(null);
    setUploadError(null);
    setTurns([]);
    convIdRef.current = null; // back to the law corpus, so start a fresh saved chat
  }, []);

  // A question deep-linked from Home / Browse: submit it once when it arrives.
  useEffect(() => {
    if (!seed?.q || seedRef.current === seed.id) return;
    seedRef.current = seed.id;
    void ask(seed.q);
  }, [seed?.id, seed?.q, ask]);

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="scroll-thin min-h-0 flex-1 overflow-y-auto py-6">
        {turns.length === 0 ? (
          <EmptyState onPick={ask} onUpload={() => fileRef.current?.click()} activeDoc={doc} />
        ) : (
          <div className="space-y-9">
            {turns.map((turn, i) => (
              <article key={i} className="animate-fade-in-up space-y-3">
                <div className="flex justify-end">
                  <p
                    dir={dirOf(turn.question)}
                    className="max-w-[82%] rounded-2xl rounded-br-md border border-line bg-elevated px-4 py-2.5 text-[15px] leading-relaxed text-ink"
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
        {doc ? (
          <div className="mb-2 flex items-center gap-2.5 rounded-xl border border-accent/30 bg-accent/10 px-3 py-2 text-[13px]">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden className="shrink-0 text-accent">
              <path d="M14 3v4a1 1 0 0 0 1 1h4M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5Z" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span className="min-w-0 flex-1 truncate text-ink" title={doc.filename}>
              Answering from <span className="font-medium">{doc.filename}</span>
            </span>
            <span className="shrink-0 text-faint">{doc.chunks} passages</span>
            <button
              type="button"
              onClick={clearDoc}
              aria-label="Remove document and return to the law corpus"
              className="shrink-0 rounded-md px-1 text-faint transition hover:text-accent"
            >
              ✕
            </button>
          </div>
        ) : uploadError ? (
          <p className="mb-2 px-1 text-[13px] text-idk">{uploadError}</p>
        ) : null}

        <div className="flex items-center gap-2 rounded-2xl border border-line-strong bg-card p-2 shadow-lift transition focus-within:border-accent/45 focus-within:ring-2 focus-within:ring-accent/10">
          <input
            ref={fileRef}
            type="file"
            accept="application/pdf,.pdf"
            className="hidden"
            onChange={(e) => void onFile(e.target.files?.[0])}
          />
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={busy || uploading}
            aria-label={doc ? "Replace document" : "Upload a PDF to ask about it"}
            title={doc ? "Replace document" : "Upload a PDF to ask about it"}
            className="grid h-10 w-10 shrink-0 place-items-center rounded-xl text-muted transition hover:bg-elevated hover:text-accent disabled:cursor-not-allowed disabled:opacity-40"
          >
            {uploading ? (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
                <path d="M21.44 11.05 12.25 20.24a5 5 0 0 1-7.07-7.07l9.19-9.19a3 3 0 0 1 4.24 4.24l-9.2 9.19a1 1 0 0 1-1.41-1.41l8.49-8.49" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </button>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            dir="auto"
            placeholder={
              doc
                ? `Ask about ${doc.filename}…`
                : "Ask about your rights in English, Urdu, or Roman Urdu…"
            }
            disabled={busy}
            className="flex-1 bg-transparent px-1 py-2 text-[15px] text-ink placeholder:text-faint focus:outline-none disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
            aria-label="Send"
            className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-accent text-canvas shadow-brass transition hover:bg-accent-hi disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy ? (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-canvas/30 border-t-canvas" />
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

function EmptyState({
  onPick,
  onUpload,
  activeDoc,
}: {
  onPick: (q: string) => void;
  onUpload: () => void;
  activeDoc: UploadedDoc | null;
}) {
  if (activeDoc) {
    return (
      <div className="animate-fade-in-up pt-8 sm:pt-12">
        <h2 className="font-display text-[34px] font-medium leading-[1.08] tracking-tight text-ink sm:text-[42px]">
          Ask your document,
          <br />
          <span className="text-accent">grounded in its pages.</span>
        </h2>
        <p className="mt-5 max-w-lg text-[15px] leading-relaxed text-muted">
          <span className="font-medium text-ink">{activeDoc.filename}</span> is ready
          ({activeDoc.chunks} passages indexed). Ask anything about it, and answers are drawn
          only from the document, cited to the page, with an honest &ldquo;I don&apos;t
          know&rdquo; when it isn&apos;t covered.
        </p>
      </div>
    );
  }
  return (
    <div className="animate-fade-in-up pt-8 sm:pt-12">
      <h2 className="font-display text-[34px] font-medium leading-[1.08] tracking-tight text-ink sm:text-[42px]">
        Know your rights,
        <br />
        <span className="text-accent">with the source.</span>
      </h2>
      <p className="mt-5 max-w-lg text-[15px] leading-relaxed text-muted">
        Ask in plain language (English, Urdu, or Roman Urdu) and get an answer grounded
        in Pakistani law, cited to the exact Article or Section, with an honest
        &ldquo;I don&apos;t know&rdquo; when the law doesn&apos;t cover it.
      </p>

      <p className="mt-9 text-[10px] font-medium uppercase tracking-[0.2em] text-faint">
        Try asking
      </p>
      <ul className="mt-3 space-y-2">
        {EXAMPLES.map((q) => (
          <li key={q}>
            <button
              onClick={() => onPick(q)}
              dir={dirOf(q)}
              className="group flex w-full items-center justify-between gap-4 rounded-xl border border-line bg-card px-4 py-3 text-left shadow-paper transition hover:-translate-y-0.5 hover:border-accent/35 hover:shadow-lift"
            >
              <span className="text-[14.5px] leading-snug text-ink/90 transition group-hover:text-accent">
                {q}
              </span>
              <span className="shrink-0 text-faint transition group-hover:translate-x-0.5 group-hover:text-accent">
                &rarr;
              </span>
            </button>
          </li>
        ))}
      </ul>

      <button
        onClick={onUpload}
        className="group mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-line-strong px-4 py-3 text-[13.5px] text-muted transition hover:border-accent/40 hover:text-accent"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden className="shrink-0">
          <path d="M21.44 11.05 12.25 20.24a5 5 0 0 1-7.07-7.07l9.19-9.19a3 3 0 0 1 4.24 4.24l-9.2 9.19a1 1 0 0 1-1.41-1.41l8.49-8.49" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        Or upload a PDF and ask about your own document
      </button>

      <p className="mt-9 text-[10px] font-medium uppercase tracking-[0.2em] text-faint">Covers</p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {COVERAGE.map((c) => (
          <span
            key={c}
            className="rounded-full border border-line bg-surface px-2.5 py-1 text-[12px] text-muted"
          >
            {c}
          </span>
        ))}
      </div>
    </div>
  );
}
