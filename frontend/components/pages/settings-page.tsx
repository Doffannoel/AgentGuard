"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/shell/app-shell";
import { PageHeading } from "@/components/shell/page-heading";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { StatePanel } from "@/components/ui/state-panel";
import { getProject, updateProject } from "@/lib/api/projects";
import type { Project } from "@/lib/types";

export function SettingsPage({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const project = useQuery({ queryKey: ["project", projectId], queryFn: () => getProject(projectId) });
  const [changes, setChanges] = useState<Partial<Project>>({});
  const form = { ...project.data, ...changes };
  const save = useMutation({
    mutationFn: () => updateProject(projectId, changes),
    onSuccess: (data) => { queryClient.setQueryData(["project", projectId], data); setChanges({}); }
  });
  return (
    <AppShell projectId={projectId}>
      <div className="page-wrap">
        <PageHeading eyebrow="Project configuration" title="Settings" description="Configure the project provider, capture mode, and request limits." />
        {project.isLoading ? <StatePanel state="loading" /> : project.error ? <StatePanel state="error" /> : (
          <form className="max-w-3xl border-y border-hairline py-5" onSubmit={(event) => { event.preventDefault(); save.mutate(); }}>
            <div className="grid gap-5 md:grid-cols-2">
              <label className="text-xs font-bold">Project name<Input className="mt-2" required value={form.name ?? ""} onChange={(e) => setChanges({ ...changes, name: e.target.value })} /></label>
              <label className="text-xs font-bold">Environment<Select className="mt-2 w-full" value={form.environment} onChange={(e) => setChanges({ ...changes, environment: e.target.value as Project["environment"] })}><option>production</option><option>staging</option><option>development</option></Select></label>
              <label className="text-xs font-bold">Default provider<Select className="mt-2 w-full" value={form.provider} onChange={(e) => setChanges({ ...changes, provider: e.target.value })}><option>Mock</option><option>OpenAI</option><option>Ollama</option></Select></label>
              <label className="text-xs font-bold">Default model<Input className="mt-2" required value={form.model ?? ""} onChange={(e) => setChanges({ ...changes, model: e.target.value })} /></label>
              <label className="text-xs font-bold md:col-span-2">Audit capture mode<Select className="mt-2 w-full" value={form.capture_mode ?? "REDACTED"} onChange={(e) => setChanges({ ...changes, capture_mode: e.target.value as Project["capture_mode"] })}><option>OFF</option><option>REDACTED</option><option>FULL</option></Select><span className="mt-2 block font-normal text-mute">FULL stores raw prompts. REDACTED is the default.</span></label>
              <label className="text-xs font-bold">Requests per minute<Input className="mt-2" type="number" min="1" value={form.requests_per_minute ?? 60} onChange={(e) => setChanges({ ...changes, requests_per_minute: Number(e.target.value) })} /></label>
              <label className="text-xs font-bold">Tokens per day<Input className="mt-2" type="number" min="1" value={form.tokens_per_day ?? 1000000} onChange={(e) => setChanges({ ...changes, tokens_per_day: Number(e.target.value) })} /></label>
              <label className="text-xs font-bold">Daily budget (USD, blank for none)<Input className="mt-2" type="number" min="0" step="0.01" value={form.budget_per_day ?? ""} onChange={(e) => setChanges({ ...changes, budget_per_day: e.target.value === "" ? null : Number(e.target.value) })} /></label>
            </div>
            <div className="mt-6 flex items-center gap-3 border-t border-hairline pt-4"><Button type="submit" disabled={save.isPending}>Save settings</Button>{save.isSuccess && <span role="status" className="text-xs decision-allow">[+] Settings saved</span>}</div>
            {save.error && <p role="alert" className="mt-3 text-xs decision-deny">{save.error.message}</p>}
          </form>
        )}
      </div>
    </AppShell>
  );
}
