"use client";

import { useState } from "react";
import { useAuth } from "./AuthProvider";
import { forgotPassword } from "@/lib/api";

type Mode = "login" | "signup" | "forgot" | "reset";

const SUBTITLE: Record<Mode, string> = {
  login: "Sign in to pick up your conversations.",
  signup: "Create an account to save your conversations.",
  forgot: "Enter your email and we'll help you reset your password.",
  reset: "Choose a new password for your account.",
};

/** Auth gate: sign in, sign up, or reset a forgotten password. */
export function AuthScreen() {
  const { login, signup, resetPassword } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [resetToken, setResetToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const go = (next: Mode) => {
    setMode(next);
    setError(null);
    setNotice(null);
    setPassword("");
    setConfirm("");
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (busy) return;
    setError(null);
    setNotice(null);

    if ((mode === "signup" || mode === "reset") && password !== confirm) {
      setError("Passwords do not match.");
      return;
    }

    setBusy(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else if (mode === "signup") {
        await signup(email, name, password);
      } else if (mode === "forgot") {
        const res = await forgotPassword(email);
        if (res.reset_token) {
          // Dev mode: no email service, so continue straight to setting a new password.
          setResetToken(res.reset_token);
          go("reset");
          setNotice("Verified. Choose a new password below.");
        } else {
          setNotice(res.message);
        }
      } else if (mode === "reset" && resetToken) {
        await resetPassword(resetToken, password);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  };

  const cta =
    mode === "login"
      ? "Sign in"
      : mode === "signup"
        ? "Create account"
        : mode === "forgot"
          ? "Continue"
          : "Reset password";

  return (
    <main className="mx-auto flex min-h-[100dvh] max-w-md flex-col justify-center px-6 py-10">
      <div className="animate-fade-in-up">
        <h1 className="font-display text-[26px] font-semibold leading-none tracking-tight text-ink">
          Pakistan Law Copilot
        </h1>
        <p className="mt-2.5 text-[14px] leading-relaxed text-muted">{SUBTITLE[mode]}</p>

        <div className="mt-7 rounded-2xl border border-line bg-card p-6 shadow-paper">
          {(mode === "login" || mode === "signup") && (
            <div className="mb-5 flex rounded-xl bg-surface p-1 text-[13px] font-medium">
              {(["login", "signup"] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => go(m)}
                  className={`flex-1 rounded-lg py-1.5 transition ${
                    mode === m ? "bg-card text-ink shadow-paper" : "text-muted hover:text-ink"
                  }`}
                >
                  {m === "login" ? "Sign in" : "Create account"}
                </button>
              ))}
            </div>
          )}

          {(mode === "forgot" || mode === "reset") && (
            <button
              type="button"
              onClick={() => go("login")}
              className="mb-4 text-[13px] text-muted transition hover:text-accent"
            >
              ← Back to sign in
            </button>
          )}

          <form onSubmit={submit} className="space-y-3.5">
            {mode === "signup" && (
              <Field label="Full name" type="text" value={name} onChange={setName}
                placeholder="Your name" autoComplete="name" />
            )}

            {mode !== "reset" && (
              <Field label="Email" type="email" value={email} onChange={setEmail}
                placeholder="you@example.com" autoComplete="email" />
            )}

            {mode !== "forgot" && (
              <Field
                label={mode === "reset" ? "New password" : "Password"}
                type="password"
                value={password}
                onChange={setPassword}
                placeholder={mode === "login" ? "••••••••" : "At least 6 characters"}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
              />
            )}

            {(mode === "signup" || mode === "reset") && (
              <Field label="Confirm password" type="password" value={confirm} onChange={setConfirm}
                placeholder="Re-enter your password" autoComplete="new-password" />
            )}

            {mode === "login" && (
              <div className="flex justify-end">
                <button type="button" onClick={() => go("forgot")}
                  className="text-[12px] text-muted transition hover:text-accent">
                  Forgot password?
                </button>
              </div>
            )}

            {notice && <p className="text-[13px] leading-relaxed text-grounded">{notice}</p>}
            {error && <p className="text-[13px] text-accent">{error}</p>}

            <button
              type="submit"
              disabled={busy}
              className="mt-1 flex w-full items-center justify-center rounded-xl bg-accent px-4 py-2.5 text-[14px] font-medium text-white transition hover:bg-[#6a2523] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {busy ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
              ) : (
                cta
              )}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-[12px] leading-relaxed text-faint">
          Legal information, not legal advice. Answers are grounded in cited statutes and may be
          incomplete.
        </p>
      </div>
    </main>
  );
}

function Field({
  label,
  type,
  value,
  onChange,
  placeholder,
  autoComplete,
}: {
  label: string;
  type: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  autoComplete: string;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-[0.14em] text-faint">
        {label}
      </span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete={autoComplete}
        required
        className="w-full rounded-xl border border-line bg-paper px-3.5 py-2.5 text-[14px] text-ink placeholder:text-faint transition focus:border-accent/40 focus:outline-none"
      />
    </label>
  );
}
