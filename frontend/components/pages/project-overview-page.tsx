"use client";

import Link from "next/link";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/shell/app-shell";
import { PageHeading } from "@/components/shell/page-heading";
import { DecisionBadge } from "@/components/shell/decision";
import { Button } from "@/components/ui/button";
import { StatePanel } from "@/components/ui/state-panel";
import { listActivity, verifyAudit } from "@/lib/api/activity";
import { listFindings } from "@/lib/api/findings";
import { getProject, getProjectSummary } from "@/lib/api/projects";

export function ProjectOverviewPage({ projectId }: { projectId: string }) {
  const project = useQuery({ queryKey: ["project", projectId], queryFn: () => getProject(projectId) });
  const summary = useQuery({ queryKey: ["summary", projectId], queryFn: () => getProjectSummary(projectId) });
  const activity = useQuery({ queryKey: ["activity", projectId], queryFn: () => listActivity(projectId) });
  const findings = useQuery({ queryKey: ["findings", projectId], queryFn: () => listFindings(projectId) });
  const verify = useMutation({ mutationFn: () => verifyAudit(projectId) });

  if (project.isLoading || summary.isLoading) return <AppShell projectId={projectId}><div className="page-wrap"><StatePanel state="loading" /></div></AppShell>;
  if (project.error || summary.error || !project.data || !summary.data) return <AppShell projectId={projectId}><div className="page-wrap"><StatePanel state="error" /></div></AppShell>;

  const s = summary.data;
  const metrics = [
    ["Requests", s.requests.toLocaleString()], ["Tool Calls", s.toolCalls.toLocaleString()], ["Blocked Actions", s.blocked.toLocaleString()], ["Pending Approvals", s.pendingApprovals.toLocaleString()], ["Security Findings", s.securityFindings.toLocaleString()], ["Estimated Cost", `$${Number(s.estimatedCost).toFixed(2)}`]
  ];

  return (
    <AppShell projectId={projectId}>
      <div className="page-wrap">
        <PageHeading eyebrow={`${project.data.environment} / ${project.data.provider} / ${project.data.model}`} title={project.data.name} description="Security decisions are authoritative from the backend. This console explains what the agent did, which policy matched, and what requires human action." action={<Button asChild><Link href={`/projects/${projectId}/approvals`}>Review approvals [{s.pendingApprovals}]</Link></Button>} />

        <section>
          {!!s.unpricedRequests && <p className="mb-3 text-xs text-mute">{s.unpricedRequests} requests have no pricing configured and are excluded from the cost estimate.</p>}
          <div className="section-label">[+] Totals</div>
          <div className="grid border-l border-t border-hairline sm:grid-cols-2 lg:grid-cols-3">
            {metrics.map(([label, value]) => <div key={label} className="border-b border-r border-hairline p-5"><div className="kicker">{label}</div><div className="metric-value mt-4">{value}</div></div>)}
          </div>
        </section>

        <section className="mt-14 rule-section">
          <div className="flex items-center justify-between"><div className="section-label">[+] Recent security activity</div><Link className="text-xs underline underline-offset-4" href={`/projects/${projectId}/activity`}>view all →</Link></div>
          <div className="border-y border-hairline">
            {activity.data?.slice(0, 4).map((event) => (
              <Link key={event.id} href={`/activity/${event.id}`} className="focus-ring grid gap-2 border-b border-hairline py-4 last:border-0 md:grid-cols-[70px_1fr_190px_1fr] md:items-center">
                <div className="text-xs text-mute">{event.time}</div><div><div className="font-bold">{event.tool}</div><div className="mt-1 text-xs text-mute">{event.agent} · {event.traceId}</div></div><div><DecisionBadge decision={event.decision} /></div><div className="text-xs text-mute">{event.rule ? `Rule: ${event.rule}` : event.reason}</div>
              </Link>
            ))}
          </div>
        </section>

        <div className="mt-14 grid gap-10 lg:grid-cols-2">
          <section className="rule-section">
            <div className="section-label">[+] Security findings</div>
            <div className="grid grid-cols-2 border-l border-t border-hairline text-sm">
              {[['Secret Findings', 'SECRET_EXPOSURE'], ['PII Findings', 'PII_DETECTED'], ['Suspicious Instructions', 'SUSPICIOUS_INSTRUCTION'], ['Budget Violations', 'BUDGET_VIOLATION']].map(([label, type]) => <div key={label} className="border-b border-r border-hairline p-4"><div className="text-2xl font-bold">{findings.data?.filter((finding) => finding.type === type).length ?? 0}</div><div className="mt-2 text-xs text-mute">{label}</div></div>)}
            </div>
            <div className="mt-4 border-y border-hairline">{findings.data?.map((finding) => <details key={finding.id} className="border-b border-hairline py-3 last:border-0"><summary className="focus-ring cursor-pointer list-none text-xs font-bold">[+] {finding.type} <span className="font-normal text-mute">· {finding.action}</span></summary><div className="mt-3 grid gap-2 pl-5 text-xs text-mute"><div>Detected: <span className="text-ink">{finding.detected}</span></div><div>Severity: <span className={`severity-${finding.severity}`}>{finding.severity}</span></div><div>Action: <span className="text-ink">{finding.action}</span></div><div>Request: <span className="text-ink">{finding.requestId}</span></div></div></details>)}</div>
          </section>
          <section className="rule-section">
            <div className="section-label">[+] Audit integrity</div>
            <div className="border border-hairline p-5">
              <div className="flex items-start justify-between gap-4"><div><div className="text-2xl font-bold">{verify.data ? `${verify.data.checked.toLocaleString()} Events` : "Not verified"}</div><div className={`mt-2 text-sm ${verify.data?.valid ? "decision-allow" : "decision-deny"}`}>{verify.data ? verify.data.valid ? "[+] Hash Chain Valid" : "[x] Integrity check failed" : "Run verification to check integrity."}</div><div className="mt-2 text-xs text-mute">Last verified: {verify.data?.verifiedAt ?? "Never"}</div></div><Button variant="secondary" size="sm" disabled={verify.isPending} onClick={() => verify.mutate()}>{verify.isPending ? "Verifying…" : "Verify Audit Chain"}</Button></div>
              {verify.error && <p role="alert" className="mt-3 text-xs decision-deny">{verify.error.message}</p>}
            </div>
          </section>
        </div>
      </div>
    </AppShell>
  );
}
