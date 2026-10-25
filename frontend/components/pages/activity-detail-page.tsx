"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/shell/app-shell";
import { PageHeading } from "@/components/shell/page-heading";
import { DecisionBadge } from "@/components/shell/decision";
import { Button } from "@/components/ui/button";
import { StatePanel } from "@/components/ui/state-panel";
import { getActivity } from "@/lib/api/activity";

export function ActivityDetailPage({ eventId }: { eventId: string }) {
  const event = useQuery({ queryKey: ["activity-detail", eventId], queryFn: () => getActivity(eventId) });
  if (event.isLoading) return <AppShell><div className="page-wrap"><StatePanel state="loading" /></div></AppShell>;
  if (event.error || !event.data) return <AppShell><div className="page-wrap"><StatePanel state="error" /></div></AppShell>;
  const e = event.data;
  return (
    <AppShell>
      <div className="page-wrap">
        <PageHeading eyebrow={`Event / ${e.id}`} title={e.tool} description={e.reason} action={<Button asChild variant="secondary"><Link href={`/projects/${e.projectId ?? "customer-support-agent"}/activity`}>← Activity</Link></Button>} />
        <div className="grid gap-10 lg:grid-cols-[1fr_360px]">
          <section>
            <div className="section-label">[+] Decision context</div>
            <div className="border-y border-hairline">
              {[
                ["Decision", <DecisionBadge key="decision" decision={e.decision} />], ["Agent", e.agent], ["Environment", e.environment], ["Policy", e.policy], ["Rule", e.rule ?? "—"], ["Reason", e.reason], ["Request ID", e.requestId], ["Trace ID", e.traceId], ["Latency", `${e.latencyMs}ms`]
              ].map(([label, value]) => <div key={String(label)} className="grid gap-2 border-b border-hairline py-3 last:border-0 md:grid-cols-[170px_1fr]"><div className="text-xs text-mute">{label}</div><div className="text-sm">{value}</div></div>)}
            </div>
            <div className="mt-10 section-label">[+] Arguments / redacted</div>
            <pre className="overflow-auto border border-hairline bg-surface-soft p-4 text-xs leading-6">{JSON.stringify(e.arguments, null, 2)}</pre>
          </section>
          <aside>
            <div className="section-label">[+] Security findings</div>
            {e.findings?.length ? <div className="border-y border-hairline">{e.findings.map((finding, index) => <div className="border-b border-hairline py-4 last:border-0" key={`${finding.type}-${index}`}><div className="font-bold">{finding.type}</div><div className="mt-2 text-xs text-mute">Detected: {finding.detected}</div><div className="mt-2 text-xs decision-approval">Action: {finding.action}</div></div>)}</div> : <StatePanel state="empty" detail="No security findings were attached to this event." />}
            <div className="mt-10 section-label">[+] Execution boundary</div>
            <div className="border border-hairline p-4 text-xs leading-6 text-mute">model output → tool proposal → policy decision → {e.decision === "ALLOW" ? "execute" : e.decision === "DENY" ? "blocked" : "approval request"}</div>
          </aside>
        </div>
      </div>
    </AppShell>
  );
}
