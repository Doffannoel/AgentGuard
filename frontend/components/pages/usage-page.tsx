"use client";

import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/shell/app-shell";
import { PageHeading } from "@/components/shell/page-heading";
import { Select } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { StatePanel } from "@/components/ui/state-panel";
import { AsciiBars } from "@/components/charts/ascii-bars";
import { getUsage } from "@/lib/api/usage";

export function UsagePage({ projectId }: { projectId: string }) {
  const [filters, setFilters] = useState({ feature: "", model: "", provider: "", environment: "", since: "", until: "" });
  const usage = useQuery({ queryKey: ["usage", projectId, filters], queryFn: () => getUsage(projectId, filters), placeholderData: keepPreviousData });
  if (usage.isLoading) return <AppShell projectId={projectId}><div className="page-wrap"><StatePanel state="loading" /></div></AppShell>;
  if (usage.error || !usage.data) return <AppShell projectId={projectId}><div className="page-wrap"><StatePanel state="error" /></div></AppShell>;
  const totals = usage.data.reduce((acc, row) => ({ requests: acc.requests + row.requests, input: acc.input + row.inputTokens, output: acc.output + row.outputTokens, cost: acc.cost + row.cost, weightedLatency: acc.weightedLatency + (row.averageLatency ?? row.p95) * row.requests, errors: acc.errors + row.errors * row.requests }), { requests: 0, input: 0, output: 0, cost: 0, weightedLatency: 0, errors: 0 });
  const metrics = [
    ["Requests", totals.requests.toLocaleString()], ["Input Tokens", totals.input.toLocaleString()], ["Output Tokens", totals.output.toLocaleString()], ["Estimated Cost", `$${totals.cost.toFixed(2)}`], ["Average Latency", `${Math.round(totals.weightedLatency / (totals.requests || 1))}ms`], ["Error Rate", `${(totals.errors / (totals.requests || 1)).toFixed(1)}%`]
  ];
  return (
    <AppShell projectId={projectId}>
      <div className="page-wrap">
        <PageHeading eyebrow="Usage / cost / latency" title="Usage" description="Provider-neutral telemetry for requests, tokens, estimated cost, latency, and errors. Charts stay secondary to security decisions." />
        <section className="mb-8 border-y border-hairline py-4"><div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
          <label className="text-[11px] text-mute">Feature<Input className="mt-1" value={filters.feature} onChange={(e) => setFilters({ ...filters, feature: e.target.value })} placeholder="all" /></label>
          <label className="text-[11px] text-mute">Model<Input className="mt-1" value={filters.model} onChange={(e) => setFilters({ ...filters, model: e.target.value })} placeholder="all" /></label>
          <label className="text-[11px] text-mute">Provider<Select className="mt-1 w-full" value={filters.provider} onChange={(e) => setFilters({ ...filters, provider: e.target.value })}><option value="">all</option><option>Mock</option><option>OpenAI</option><option>Ollama</option></Select></label>
          <label className="text-[11px] text-mute">Environment<Select className="mt-1 w-full" value={filters.environment} onChange={(e) => setFilters({ ...filters, environment: e.target.value })}><option value="">all</option><option>production</option><option>staging</option><option>development</option></Select></label>
          <label className="text-[11px] text-mute">Since (UTC)<Input className="mt-1" type="date" value={filters.since} onChange={(e) => setFilters({ ...filters, since: e.target.value })} /></label>
          <label className="text-[11px] text-mute">Before (UTC)<Input className="mt-1" type="date" value={filters.until} onChange={(e) => setFilters({ ...filters, until: e.target.value })} /></label>
        </div></section>
        {usage.data.some((row) => row.pricingConfigured === false) && <p className="mb-4 text-xs text-mute">Some requests have no pricing configured. Their costs are excluded from this estimate.</p>}
        <section className="grid border-l border-t border-hairline sm:grid-cols-2 lg:grid-cols-3">{metrics.map(([label, value]) => <div key={label} className="border-b border-r border-hairline p-5"><div className="kicker">{label}</div><div className="mt-4 text-2xl font-bold">{value}</div></div>)}</section>
        <section className="mt-14 grid gap-10 lg:grid-cols-2">
          <div className="rule-section"><div className="section-label">[+] Cost by model</div><AsciiBars rows={usage.data} value="cost" format={(v) => `$${v.toFixed(2)}`} /></div>
          <div className="rule-section"><div className="section-label">[+] Requests by model</div><AsciiBars rows={usage.data} value="requests" format={(v) => v.toLocaleString()} /></div>
          <div className="rule-section"><div className="section-label">[+] Token usage / input</div><AsciiBars rows={usage.data} value="inputTokens" format={(v) => v.toLocaleString()} /></div>
          <div className="rule-section"><div className="section-label">[+] Latency p95</div><AsciiBars rows={usage.data} value="p95" format={(v) => `${v}ms`} /></div>
          <div className="rule-section lg:col-span-2"><div className="section-label">[+] Error rate</div><AsciiBars rows={usage.data} value="errors" format={(v) => `${v.toFixed(1)}%`} /></div>
        </section>
      </div>
    </AppShell>
  );
}
