"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/shell/app-shell";
import { PageHeading } from "@/components/shell/page-heading";
import { ActivityTable } from "@/components/activity/activity-table";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { StatePanel } from "@/components/ui/state-panel";
import { listActivity } from "@/lib/api/activity";

export function ActivityPage({ projectId }: { projectId: string }) {
  const { data, isLoading, error } = useQuery({ queryKey: ["activity", projectId], queryFn: () => listActivity(projectId) });
  const [decision, setDecision] = useState("all");
  const [tool, setTool] = useState("");
  const [agent, setAgent] = useState("all");
  const [environment, setEnvironment] = useState("all");
  const [severity, setSeverity] = useState("all");
  const [date, setDate] = useState("2026-10-07");
  const filtered = useMemo(() => (data ?? []).filter((event) =>
    (decision === "all" || event.decision === decision) &&
    (!tool || event.tool.toLowerCase().includes(tool.toLowerCase())) &&
    (agent === "all" || event.agent === agent) &&
    (environment === "all" || event.environment === environment) &&
    (severity === "all" || event.severity === severity)
  ), [data, decision, tool, agent, environment, severity]);

  return (
    <AppShell projectId={projectId}>
      <div className="page-wrap">
        <PageHeading eyebrow="Audit log / tool monitoring" title="Activity" description="Inspect request and tool-call decisions. Open an event to see matched policy, redacted arguments, security findings, request ID, and trace ID." />
        <section className="mb-8 border-y border-hairline py-4">
          <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
            <label className="text-[11px] text-mute">decision<Select className="mt-1 w-full" value={decision} onChange={(e) => setDecision(e.target.value)}><option value="all">all</option><option value="ALLOW">ALLOW</option><option value="REQUIRE_APPROVAL">APPROVAL</option><option value="DENY">DENY</option></Select></label>
            <label className="text-[11px] text-mute">tool<Input className="mt-1" value={tool} onChange={(e) => setTool(e.target.value)} placeholder="payment.refund" /></label>
            <label className="text-[11px] text-mute">agent<Select className="mt-1 w-full" value={agent} onChange={(e) => setAgent(e.target.value)}><option value="all">all</option><option value="support-agent">support-agent</option></Select></label>
            <label className="text-[11px] text-mute">date<Input className="mt-1" type="date" value={date} onChange={(e) => setDate(e.target.value)} /></label>
            <label className="text-[11px] text-mute">environment<Select className="mt-1 w-full" value={environment} onChange={(e) => setEnvironment(e.target.value)}><option value="all">all</option><option value="production">production</option><option value="staging">staging</option><option value="development">development</option></Select></label>
            <label className="text-[11px] text-mute">severity<Select className="mt-1 w-full" value={severity} onChange={(e) => setSeverity(e.target.value)}><option value="all">all</option><option value="critical">critical</option><option value="high">high</option><option value="medium">medium</option><option value="low">low</option></Select></label>
          </div>
        </section>
        {isLoading ? <StatePanel state="loading" /> : error ? <StatePanel state="error" /> : filtered.length === 0 ? <StatePanel state="empty" /> : <ActivityTable events={filtered} />}
        <div className="mt-3 text-xs text-mute">Showing {filtered.length} events · selected date {date}</div>
      </div>
    </AppShell>
  );
}
