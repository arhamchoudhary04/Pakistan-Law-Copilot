import { ChatWindow } from "@/components/ChatWindow";

export default function Home() {
  return (
    <main className="mx-auto flex h-screen max-w-4xl flex-col">
      <header className="border-b border-slate-800 px-4 py-3">
        <h1 className="text-base font-semibold text-slate-100">
          Pakistan Law Copilot
          <span className="ml-2 text-xs font-normal text-slate-500">
            grounded · cited · refuses when unsure
          </span>
        </h1>
        <p className="mt-1 text-xs text-idk">
          ⚖️ Legal information, not legal advice. Answers come only from a limited set
          of Pakistani laws (constitutional rights, crime &amp; criminal procedure,
          family, cybercrime, harassment, information, rent, consumer &amp; employment) —
          verify against the cited source and consult a qualified lawyer.
        </p>
      </header>
      <div className="min-h-0 flex-1">
        <ChatWindow />
      </div>
    </main>
  );
}
