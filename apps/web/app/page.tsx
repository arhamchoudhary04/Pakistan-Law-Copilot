import { ChatWindow } from "@/components/ChatWindow";

export default function Home() {
  return (
    <main className="mx-auto flex h-[100dvh] max-w-2xl flex-col px-5">
      <header className="pt-6">
        <div className="flex items-baseline justify-between gap-4">
          <h1 className="font-display text-[22px] font-semibold leading-none tracking-tight text-ink">
            Pakistan Law Copilot
          </h1>
          <span className="hidden text-[10px] uppercase tracking-[0.22em] text-faint sm:block">
            Statutes of Pakistan
          </span>
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
        <ChatWindow />
      </div>
    </main>
  );
}
