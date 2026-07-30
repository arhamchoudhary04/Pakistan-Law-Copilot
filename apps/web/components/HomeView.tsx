"use client";

import { TOPICS } from "@/lib/topics";

/** A few real starter questions, drawn from the topic map so they always resolve. */
const STARTERS = [
  "What are my rights if I am arrested by the police?",
  "Do I have a right to a fair trial?",
  "How does a court decide who gets custody of a child?",
  "Someone shared my private photos without consent. What does the law say?",
  "Kya mujhe taleem ka haq hasil hai?",
];

const STATS = [
  { value: "16", label: "statutes indexed", note: "constitutional to consumer" },
  { value: "1,872", label: "provisions searchable", note: "one heading per section" },
  { value: "96%", label: "provision accuracy", note: "exact section, 50-question set" },
  { value: "3", label: "languages", note: "English, Urdu, Roman Urdu" },
];

/** Landing view: explains the tool and offers ways in (ask, browse, or upload a PDF). */
export function HomeView({
  onStartAsk,
  onBrowse,
  onAsk,
}: {
  onStartAsk: () => void;
  onBrowse: () => void;
  onAsk: (question: string) => void;
}) {
  return (
    <div className="scroll-thin h-full overflow-y-auto pb-10 pt-8">
      <div className="animate-fade-in-up">
        {/* Hero: copy on the left, a worked example on the right, so the page has
            something to look at above the fold instead of one column of text. */}
        <section className="grid items-center gap-10 lg:grid-cols-[minmax(0,1fr)_400px] lg:gap-14">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1 text-[11px] uppercase tracking-[0.16em] text-faint">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" />
              Pakistani law, cited
            </span>
            <h2 className="mt-5 font-display text-[40px] font-medium leading-[1.04] tracking-tight text-ink sm:text-[56px]">
              Know your rights,
              <br />
              <span className="text-accent">grounded in the law.</span>
            </h2>
            <p className="mt-5 max-w-xl text-[15px] leading-relaxed text-muted">
              Ask everyday questions about Pakistani law, in English, Urdu, or Roman Urdu, and
              get an answer drawn only from the statutes, cited to the exact Article or
              Section, with an honest &ldquo;I don&apos;t know&rdquo; when the law
              doesn&apos;t cover it.
            </p>
            <div className="mt-7 flex flex-wrap items-center gap-3">
              <button
                onClick={onStartAsk}
                className="rounded-xl bg-accent px-5 py-2.5 text-[14px] font-semibold text-canvas shadow-brass transition hover:bg-accent-hi"
              >
                Ask a question
              </button>
              <button
                onClick={onBrowse}
                className="rounded-xl border border-line-strong bg-card px-5 py-2.5 text-[14px] font-medium text-ink shadow-paper transition hover:border-accent/40 hover:text-accent"
              >
                Browse the law
              </button>
            </div>
          </div>

          <SampleAnswer />
        </section>

        {/* Measured numbers. The accuracy figure is the provision-level one, which is
            the honest metric rather than the flattering document-level one. */}
        <section className="mt-14 grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
          {STATS.map((s) => (
            <div key={s.label} className="bg-card px-4 py-5">
              <p className="font-display text-[28px] font-medium leading-none text-accent">
                {s.value}
              </p>
              <p className="mt-2 text-[13px] font-medium text-ink">{s.label}</p>
              <p className="mt-0.5 text-[12px] leading-relaxed text-faint">{s.note}</p>
            </div>
          ))}
        </section>

        {/* Starters: a cold landing page with no obvious first move is what reads as
            empty, so offer real questions that resolve against the corpus. */}
        <section className="mt-14">
          <SectionLabel>Try one of these</SectionLabel>
          <div className="mt-4 grid gap-2.5 sm:grid-cols-2">
            {STARTERS.map((q) => (
              <button
                key={q}
                onClick={() => onAsk(q)}
                className="group flex items-start gap-3 rounded-xl border border-line bg-card px-4 py-3 text-left shadow-paper transition hover:-translate-y-0.5 hover:border-accent/35 hover:shadow-lift"
              >
                <span className="mt-[3px] font-mono text-[11px] text-accent/70 transition group-hover:text-accent">
                  ?
                </span>
                <span className="flex-1 text-[13.5px] leading-relaxed text-ink/90">{q}</span>
                <span className="mt-[2px] shrink-0 text-[13px] text-faint transition group-hover:translate-x-0.5 group-hover:text-accent">
                  &rarr;
                </span>
              </button>
            ))}
            <button
              onClick={onStartAsk}
              className="flex items-center justify-center gap-2 rounded-xl border border-dashed border-line-strong px-4 py-3 text-[13.5px] text-muted transition hover:border-accent/40 hover:text-accent"
            >
              Or write your own question
            </button>
          </div>
        </section>

        {/* Ways in */}
        <section className="mt-14">
          <SectionLabel>Three ways in</SectionLabel>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <EntryCard
              n="01"
              title="Ask a question"
              body="Plain-language answers with citations you can open and verify against the statute."
              cta="Start asking"
              onClick={onStartAsk}
              primary
            />
            <EntryCard
              n="02"
              title="Browse the law"
              body={`Explore ${TOPICS.length} everyday topics and the statutes behind each one.`}
              cta="Browse"
              onClick={onBrowse}
            />
            <EntryCard
              n="03"
              title="Your own document"
              body="Upload a PDF and ask questions grounded in its pages, cited to the page."
              cta="Upload"
              onClick={onStartAsk}
            />
          </div>
        </section>

        {/* How it works: the trust story */}
        <section className="mt-14">
          <SectionLabel>Why you can check it</SectionLabel>
          <div className="mt-4 grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-3">
            <Step
              n="01"
              title="Grounded"
              body="Answers come only from official statutes, never the model's own memory."
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
        </section>

        {/* Coverage */}
        <section className="mt-14">
          <div className="flex items-baseline justify-between gap-4">
            <SectionLabel>Covers {TOPICS.length} areas</SectionLabel>
            <button
              onClick={onBrowse}
              className="shrink-0 text-[12px] text-muted transition hover:text-accent"
            >
              See all &rarr;
            </button>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {TOPICS.map((t) => (
              <button
                key={t.id}
                onClick={onBrowse}
                title={t.blurb}
                className="rounded-full border border-line bg-card px-3.5 py-1.5 text-[13px] text-ink/85 transition hover:border-accent/40 hover:bg-elevated hover:text-accent"
              >
                {t.title}
              </button>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3">
      <p className="shrink-0 text-[10px] font-medium uppercase tracking-[0.2em] text-faint">
        {children}
      </p>
      <span className="rule-fade min-w-0 flex-1" />
    </div>
  );
}

/** A static worked example. Mirrors the real answer card so the hero shows the
 *  product rather than describing it. */
function SampleAnswer() {
  return (
    <div className="relative">
      <div className="pointer-events-none absolute -inset-3 rounded-3xl bg-sheen blur-xl" />
      <div className="relative rounded-2xl border border-line bg-card p-5 shadow-lift">
        <p className="text-[13px] text-faint">Do I have a right to a fair trial?</p>
        <div className="mt-3 h-px bg-line" />
        <p className="mt-3 text-[14px] leading-7 text-ink">
          Yes. For the determination of civil rights and obligations or in any criminal
          charge, a person is entitled to a fair trial and due process
          <sup className="relative -top-[0.2em] mx-[2px] text-[0.7em] font-semibold text-accent underline decoration-accent/40 underline-offset-2">
            1
          </sup>
          .
        </p>
        <div className="mt-4 rounded-xl border border-line bg-surface p-3">
          <p className="font-mono text-[10px] uppercase tracking-wider text-faint">Source 1</p>
          <p className="mt-1 text-[13px] font-medium text-ink">
            Article 10A. Right to fair trial
          </p>
          <p className="text-[12px] text-muted">Constitution of Pakistan, Fundamental Rights</p>
        </div>
        <div className="mt-4 flex items-center gap-2.5 border-t border-line pt-3">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-grounded/12 px-2.5 py-1 text-[11px] font-medium text-grounded ring-1 ring-inset ring-grounded/30">
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            Grounded
          </span>
          <span className="font-mono text-[11px] text-faint">cosine 0.83</span>
        </div>
      </div>
    </div>
  );
}

function EntryCard({
  n,
  title,
  body,
  cta,
  onClick,
  primary = false,
}: {
  n: string;
  title: string;
  body: string;
  cta: string;
  onClick: () => void;
  primary?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`group flex flex-col rounded-2xl border p-5 text-left shadow-paper transition hover:-translate-y-0.5 hover:shadow-lift ${
        primary
          ? "border-accent/35 bg-card bg-sheen"
          : "border-line bg-card hover:border-line-strong"
      }`}
    >
      <span className="font-mono text-[11px] text-accent/70">{n}</span>
      <span className="mt-2 font-display text-[18px] font-medium text-ink">{title}</span>
      <span className="mt-2 flex-1 text-[13px] leading-relaxed text-muted">{body}</span>
      <span className="mt-4 text-[13px] font-medium text-accent transition group-hover:translate-x-0.5">
        {cta} &rarr;
      </span>
    </button>
  );
}

function Step({ n, title, body }: { n: string; title: string; body: string }) {
  return (
    <div className="bg-card p-5 transition hover:bg-elevated">
      <div className="flex items-center gap-2.5">
        <span className="grid h-6 w-6 place-items-center rounded-md border border-accent/25 font-mono text-[10px] text-accent">
          {n}
        </span>
        <span className="font-display text-[16px] font-medium text-ink">{title}</span>
      </div>
      <p className="mt-2.5 text-[13px] leading-relaxed text-muted">{body}</p>
    </div>
  );
}
