"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import {
  fetchMe,
  login as loginApi,
  resetPassword as resetPasswordApi,
  signup as signupApi,
  type AuthUser,
} from "@/lib/api";

const TOKEN_KEY = "plc_token";

interface AuthState {
  user: AuthUser | null;
  token: string | null;
  ready: boolean; // finished the initial token check
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, name: string, password: string) => Promise<void>;
  resetPassword: (token: string, newPassword: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  // On first load, restore a saved token and confirm it's still valid.
  useEffect(() => {
    const saved = typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null;
    if (!saved) {
      setReady(true);
      return;
    }
    fetchMe(saved)
      .then((u) => {
        setUser(u);
        setToken(saved);
      })
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setReady(true));
  }, []);

  const apply = useCallback((result: { token: string; user: AuthUser }) => {
    localStorage.setItem(TOKEN_KEY, result.token);
    setToken(result.token);
    setUser(result.user);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => apply(await loginApi(email, password)),
    [apply],
  );
  const signup = useCallback(
    async (email: string, name: string, password: string) =>
      apply(await signupApi(email, name, password)),
    [apply],
  );
  const resetPassword = useCallback(
    async (token: string, newPassword: string) =>
      apply(await resetPasswordApi(token, newPassword)),
    [apply],
  );
  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, token, ready, login, signup, resetPassword, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
