"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/shell/app-shell";
import { PageHeading } from "@/components/shell/page-heading";
import { Button } from "@/components/ui/button";
import { StatePanel } from "@/components/ui/state-panel";
import { ReplayCaseRow } from "@/components/redteam/replay-case-row";
import { createReplayRun, listReplayCases, getReplayRun } from "@/lib/api/replay";
import { demoMode } from "@/lib/api/client";

export function RedTeamPage({ projectId }: { projectId: string }) {
  const cases = useQuery({ queryKey: ["replay-cases", projectId], queryFn: () => listReplayCases(projectId) });
  const create = useMutation({ mutationFn: () => createReplayRun(projectId) });
  const [demoCompleted, setDemoCompleted] = useState(false);
  const run = useQuery({
    queryKey: ["replay-run", create.data?.id],
    queryFn: () => getReplayRun(create.data!.id),
    enabled: !demoMode && !!create.data,
    refetchInterval: (query) => ["completed", "failed"].includes(query.state.data?.status ?? "") ? false : 1000
  });
  useEffect(() => {
    if (!demoMode || !create.data) return;
    setDemoCompleted(false);
    const timer = window.setTimeout(() => setDemoCompleted(true), 1000);
    return () => window.clearTimeout(timer);
  }, [create.data]);
  useEffect(() => {
    if (run.data?.status === "completed") void cases.refetch();
  }, [run.data?.status, cases.refetch]);

  const status = demoMode ? demoCompleted ? "completed" : create.data ? "running" : "idle" : run.data?.status ?? (create.data ? "queued" : "idle");
  const total = demoMode ? 105 : run.data?.total ?? cases.data?.length ?? 0;
  const passed = demoMode ? demoCompleted ? 103 : 101 : run.data?.passed ?? 0;
  const failed = demoMode ? demoCompleted ? 2 : 4 : run.data?.failed ?? 0;
  const completed = demoMode ? demoCompleted ? 105 : 0 : run.data?.completed ?? 0;
  const busy = create.isPending || status === "queued" || status === "running";
  return (
    <AppShell projectId={projectId}>
      <div className="page-wrap">
        <PageHeading eyebrow="Adversarial regression" title="Red Team" description="Replay registered attack cases through the AgentGuard tool policy boundary." action={<Button disabled={busy} onClick={() => create.mutate()}>{busy ? "Running..." : "Run Replay Suite"}</Button>} />
        {(create.error || run.error) && <StatePanel state="error" detail={String(create.error || run.error)} />}
        <section className="grid border-l border-t border-hairline sm:grid-cols-2 lg:grid-cols-4">
          {[["Tests", total], ["Passed", passed], ["Failed", failed], ["Pass rate", `${total ? (passed / total * 100).toFixed(1) : "0.0"}%`]].map(([label, value]) => <div key={label} className="border-b border-r border-hairline p-5"><div className="kicker">{label}</div><div className="metric-value mt-4">{value}</div></div>)}
        </section>
        <section className="mt-10 border border-hairline p-5" aria-live="polite">
          <div className="section-label">[+] Replay state</div>
          <div className="mt-5 text-sm">{status}</div>
          <div className="mt-5 ascii-bar"><span style={{ width: `${total ? completed / total * 100 : 0}%` }} /></div>
          <div className="mt-3 text-xs text-mute">{status === "idle" ? "No active replay run." : status === "completed" ? `Completed · ${completed} / ${total}` : `Processed ${completed} / ${total}`}</div>
          {run.data?.policyVersion && <div className="mt-2 text-xs text-mute">Policy version: {run.data.policyVersion}</div>}
          {run.data?.error && <p role="alert">{run.data.error}</p>}
        </section>
        <section className="mt-14 rule-section">
          <div className="section-label">[+] Cases</div>
          <div className="mt-5 hairline-list border-y border-hairline">{cases.isLoading ? <StatePanel state="loading" /> : cases.error ? <StatePanel state="error" /> : !cases.data?.length ? <StatePanel state="empty" /> : cases.data.map((item) => <ReplayCaseRow key={item.id} item={item} />)}</div>
        </section>
      </div>
    </AppShell>
  );
}
