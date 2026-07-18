"use client";

import { TOPICS } from "@/lib/topics";

/**
 * The landing view. Instead of dropping straight into a chat box, it explains
 * what the tool is, how to trust it, and offers clear ways in (ask, browse, or
 * bring your own document).
 */
export function HomeView({
  onStartAsk,
  onBrowse,
}: {
  onStartAsk: () => void;
  onBrowse: () => void;
}) {
  return (
    <div className="scroll-thin h-full overflow-y-auto py-8">
      <div className="animate-fade-in-up">
        {/* Hero */}
        <h2 className="font-display text-[38px] font-medium leading-[1.05] tracking-tight text-ink sm:text-[52px]">
          Know your rights,
          <br />
          <span className="text-accent">grounded in the law.</span>
        </h2>
        <p className="mt-5 max-w-lg text-[15px] leading-relaxed text-muted">
          Ask everyday questions about Pakistani law — in English, Urdu, or Roman Urdu —
          and get an answer drawn only from the statutes, cited to the exact Article or
          Section, with an honest &ldquo;I don&apos;t know&rdquo; when the law doesn&apos;t
          cover it.
        </p>

        {/* Ways in */}
        <div className="mt-8 grid gap-3 sm:grid-cols-3">
          <EntryCard
            title="Ask a question"
            body="Plain-language answers with citations you can open and verify."
            cta="Start asking →"
            onClick={onStartAsk}
            primary
          />
          <EntryCard
            title="Browse the law"
            body={`Explore ${TOPICS.length} everyday topics across the statutes.`}
            cta="Browse →"
            onClick={onBrowse}
          />
          <EntryCard
            title="Your own document"
            body="Upload a PDF and ask questions grounded in its pages."
            cta="Upload →"
            onClick={onStartAsk}
          />
        </div>

        {/* How it works — the trust story */}
        <div className="mt-12">
          <p className="text-[10px] font-medium uppercase tracking-[0.2em] text-faint">
            How it works
          </p>
          <div className="mt-3 grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-3">
            <Step
              n="01"
              title="Grounded"
              body="Answers come only from official statutes — never the model's own memory."
            />
            <Step
              n="02"
              title="Cited"
              body="Every legal claim links to the exact provision behind it, so you can check it."
            />
            <Step
              n="03"
              title="Honest"
              body="When the sources don't cover your question, it says so instead of guessing."
            />
          </div>
        </div>

        {/* Coverage */}
        <div className="mt-12">
          <div className="flex items-baseline justify-between">
            <p className="text-[10px] font-medium uppercase tracking-[0.2em] text-faint">
              Covers {TOPICS.length} areas
            </p>
            <button
              onClick={onBrowse}
              className="text-[12px] text-muted transition hover:text-accent"
            >
              See all →
            </button>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {TOPICS.map((t) => (
              <button
                key={t.id}
                onClick={onBrowse}
                className="rounded-full border border-line bg-card px-3 py-1.5 text-[13px] text-ink/80 transition hover:border-accent/40 hover:text-accent"
              >
                {t.title}
              </button>
            ))}
          </div>
        </div>

        <p className="mt-12 border-t border-line pt-5 text-[12px] leading-relaxed text-faint">
          Legal information, not legal advice. Answers may be incomplete — verify against the
          cited source and consult a qualified lawyer for your situation.
        </p>
      </div>
    </div>
  );
}

function EntryCard({
  title,
  body,
  cta,
  onClick,
  primary = false,
}: {
  title: string;
  body: string;
  cta: string;
  onClick: () => void;
  primary?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`group flex flex-col rounded-2xl border p-4 text-left shadow-paper transition hover:-translate-y-0.5 hover:shadow-lift ${
        primary ? "border-accent/30 bg-accent/[0.04]" : "border-line bg-card"
      }`}
    >
      <span className="font-display text-[17px] font-medium text-ink">{title}</span>
      <span className="mt-1.5 flex-1 text-[13px] leading-relaxed text-muted">{body}</span>
      <span className="mt-3 text-[13px] font-medium text-accent transition group-hover:translate-x-0.5">
        {cta}
      </span>
    </button>
  );
}

function Step({ n, title, body }: { n: string; title: string; body: string }) {
  return (
    <div className="bg-card p-4">
      <div className="flex items-center gap-2">
        <span className="font-mono text-[11px] text-accent">{n}</span>
        <span className="font-display text-[15px] font-medium text-ink">{title}</span>
      </div>
      <p className="mt-1.5 text-[13px] leading-relaxed text-muted">{body}</p>
    </div>
  );
}
