"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AsciiLogo } from "@/components/shell/ascii-logo";
import { signIn } from "@/lib/auth/session";
import { demoMode } from "@/lib/api/client";

export function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState(demoMode ? "admin@example.com" : "");
  const [password, setPassword] = useState(demoMode ? "demo-password" : "");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      await signIn(email, password);
      setPassword("");
      router.push(demoMode ? "/projects/customer-support-agent" : "/projects");
    } catch (error) {
      setError(error instanceof Error ? error.message : "Sign-in failed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="min-h-screen bg-canvas px-4 py-8 md:px-8 md:py-16">
      <div className="mx-auto grid min-h-[680px] max-w-[1100px] border border-hairline md:grid-cols-[1.1fr_.9fr]">
        <section className="dark-panel flex min-h-[360px] flex-col justify-between p-7 md:p-10">
          <div>
            <AsciiLogo />
            <div className="mt-8 text-xs text-ash">security control console</div>
          </div>
          <div>
            <div className="max-w-xl text-2xl font-bold leading-relaxed md:text-4xl">Assume the model can be manipulated.</div>
            <p className="mt-4 max-w-lg text-sm leading-7 text-ash">Restrict what manipulated models are allowed to do. Inspect policy decisions, approve sensitive actions, and replay adversarial scenarios.</p>
            <div className="mt-8 space-y-2 text-sm text-ash">
              <div>[+] deterministic policy decisions</div>
              <div>[+] tamper-evident audit trail</div>
              <div>[+] human approval for sensitive tools</div>
              <div>[+] security regression replay</div>
            </div>
          </div>
        </section>
        <section className="flex items-center p-7 md:p-10">
          <form className="w-full" onSubmit={submit}>
            <div className="kicker">AgentGuard</div>
            <h1 className="mt-2 text-3xl font-bold">Secure your AI agents.</h1>
            <p className="mt-3 text-sm leading-7 text-mute">{demoMode ? "Demo authentication is local." : "Sign in with your AgentGuard console account."}</p>
            <label className="mt-8 block text-xs font-bold">Email</label>
            <Input className="mt-2" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
            <label className="mt-5 block text-xs font-bold">Password</label>
            <Input className="mt-2" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
            <Button className="mt-7 w-full" type="submit" disabled={pending}>{pending ? "Signing in..." : "Sign In"}</Button>
            {error && <p role="alert" className="mt-3 text-xs decision-deny">{error}</p>}
            {demoMode && <div className="mt-5 border-t border-hairline pt-4 text-xs text-mute">demo → admin@example.com / any password</div>}
          </form>
        </section>
      </div>
    </main>
  );
}
