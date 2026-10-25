"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AsciiLogo } from "./ascii-logo";
import { cn } from "@/lib/utils";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getSession, signOut } from "@/lib/auth/session";
import { demoMode } from "@/lib/api/client";
import { getProject } from "@/lib/api/projects";

const globalItems = [
  ["Overview", "/projects/customer-support-agent"],
  ["Projects", "/projects"],
  ["Policies", "/projects/customer-support-agent/policies"],
  ["Activity", "/projects/customer-support-agent/activity"],
  ["Approvals", "/projects/customer-support-agent/approvals"],
  ["Red Team", "/projects/customer-support-agent/red-team"],
  ["Usage", "/projects/customer-support-agent/usage"],
  ["Settings", "/projects/customer-support-agent/settings"]
] as const;

export function AppShell({ children, projectId = "customer-support-agent" }: { children: React.ReactNode; projectId?: string }) {
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const session = useQuery({ queryKey: ["session"], queryFn: getSession, enabled: !demoMode, retry: false });
  const project = useQuery({ queryKey: ["project", projectId], queryFn: () => getProject(projectId), enabled: !demoMode && pathname.startsWith(`/projects/${projectId}`) });
  const projectBase = `/projects/${projectId}`;
  const projectItems = [
    ["Overview", projectBase],
    ["Policies", `${projectBase}/policies`],
    ["Activity", `${projectBase}/activity`],
    ["Approvals", `${projectBase}/approvals`],
    ["Red Team", `${projectBase}/red-team`],
    ["Usage", `${projectBase}/usage`],
    ["API Keys", `${projectBase}/api-keys`],
    ["Settings", `${projectBase}/settings`]
  ] as const;
  const selected = pathname.startsWith(projectBase);
  const projectLabel = project.data?.name ?? (projectId === "customer-support-agent" ? "Customer Support Agent" : projectId.replace(/-/g, " "));
  const items = selected ? projectItems : demoMode ? globalItems : [["Projects", "/projects"]];

  return (
    <div className="console-shell">
      <aside className="console-rail">
        <Link href="/projects" className="focus-ring inline-flex py-1"><AsciiLogo /></Link>
        <div className="mt-8 border-t border-hairline pt-4">
          {selected && (
            <div className="mb-5">
              <div className="kicker">Project</div>
              <div className="mt-1 text-sm font-bold capitalize">{projectLabel}</div>
              <div className="mt-1 text-xs text-mute">{demoMode ? "production · OpenAI · gpt-x" : project.data ? `${project.data.environment} · ${project.data.provider} · ${project.data.model}` : "Loading project..."}</div>
            </div>
          )}
          <nav className="flex flex-col">
            {items.map(([label, href]) => {
              const active = pathname === href || (href !== projectBase && pathname.startsWith(`${href}/`));
              return (
                <Link key={href} href={href} className={cn("focus-ring border-t border-hairline px-1 py-2.5 text-sm", active ? "font-bold text-ink" : "text-mute")}>
                  <span className="mr-2">{active ? "[+]" : "[-]"}</span>{label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="mt-auto border-t border-hairline pt-4 text-xs leading-6 text-mute">
          <div>{demoMode ? "Demo mode" : session.isSuccess ? "Console connected" : "Connecting..."}</div>
          {selected && <div>capture: {demoMode ? "REDACTED" : project.data?.capture_mode ?? "..."}</div>}
        </div>
      </aside>

      <div className="console-main">
        <header className="console-header">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="md:hidden"><AsciiLogo compact /></div>
            <div className="hidden md:block text-xs text-mute">console / {pathname.split("/").filter(Boolean).join(" / ") || "overview"}</div>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <span className="hidden sm:inline text-mute">{demoMode ? "admin@example.com" : session.data?.email}</span>
            <button onClick={async () => { await signOut(); queryClient.clear(); window.location.assign("/login"); }} className="focus-ring underline underline-offset-4">sign out</button>
          </div>
        </header>
        <main>{children}</main>
      </div>
    </div>
  );
}
