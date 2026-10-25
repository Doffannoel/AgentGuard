export interface ConsoleSession {
  email: string;
  authenticated: boolean;
}

export const demoSession: ConsoleSession = {
  email: "admin@example.com",
  authenticated: true
};
import { apiFetch, demoMode } from "@/lib/api/client";


export async function signIn(email: string, password: string): Promise<ConsoleSession> {
  if (demoMode) return demoSession;
  return apiFetch("/v1/console/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
}

export async function getSession(): Promise<ConsoleSession> {
  return demoMode ? demoSession : apiFetch("/v1/console/auth/session");
}

export async function signOut() {
  if (!demoMode) await apiFetch("/v1/console/auth/logout", { method: "POST" });
}
