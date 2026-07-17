import { ChatWindow } from "@/components/ChatWindow";

export default function Home() {
  return (
    <main className="mx-auto flex h-[100dvh] max-w-3xl flex-col px-4">
      <header className="flex flex-col gap-2.5 py-4">
        <div className="flex items-center gap-3">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-indigo-500/15 text-base ring-1 ring-inset ring-indigo-400/30">
            ⚖️
          </div>
          <div className="leading-tight">
            <h1 className="text-[15px] font-semibold tracking-tight text-white">
              Pakistan Law Copilot
            </h1>
            <p className="text-xs text-zinc-500">grounded · cited · refuses when unsure</p>
          </div>
        </div>
        <p className="rounded-lg border border-amber-400/15 bg-amber-400/5 px-3 py-2 text-[11px] leading-relaxed text-amber-200/80">
          Legal information, not legal advice. Answers come only from a limited set of
          Pakistani laws (constitutional rights, crime &amp; procedure, family, divorce,
          dowry, contracts, cybercrime, harassment, information, rent, consumer &amp;
          employment) — verify against the cited source and consult a qualified lawyer.
        </p>
      </header>
      <div className="min-h-0 flex-1">
        <ChatWindow />
      </div>
    </main>
  );
}
