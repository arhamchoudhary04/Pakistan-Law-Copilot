import { ChatWindow } from "@/components/ChatWindow";

export default function Home() {
  return (
    <main className="mx-auto flex h-screen max-w-4xl flex-col">
      <header className="border-b border-slate-800 px-4 py-3">
        <h1 className="text-base font-semibold text-slate-100">
          Knowledge Copilot
          <span className="ml-2 text-xs font-normal text-slate-500">
            grounded · cited · refuses when unsure
          </span>
        </h1>
      </header>
      <div className="min-h-0 flex-1">
        <ChatWindow />
      </div>
    </main>
  );
}
