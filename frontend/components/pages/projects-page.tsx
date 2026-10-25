"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/shell/app-shell";
import { PageHeading } from "@/components/shell/page-heading";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { StatePanel } from "@/components/ui/state-panel";
import { createProject, deleteProject, listProjects, setProjectEnabled } from "@/lib/api/projects";
import { getApiErrorState } from "@/lib/api/client";
import type { Environment } from "@/lib/types";

export function ProjectsPage() {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const errorState = getApiErrorState(error);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", environment: "development" as Environment, provider: "OpenAI", model: "gpt-x" });
  const toggle = useMutation({ mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => setProjectEnabled(id, enabled), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }) });
  const remove = useMutation({ mutationFn: (id: string) => deleteProject(id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }) });
  const create = useMutation({
    mutationFn: () => createProject(form),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["projects"] }); setOpen(false); setForm((v) => ({ ...v, name: "", description: "" })); }
  });

  return (
    <AppShell>
      <div className="page-wrap">
        <PageHeading eyebrow="Workspace" title="Projects" description="Projects isolate policies, API keys, requests, audit events, and replay suites. Console data is always scoped to a project." action={<Button onClick={() => setOpen(true)}>[+] Create Project</Button>} />
        {(toggle.error || remove.error) && <StatePanel state={getApiErrorState(toggle.error || remove.error)} detail={String(toggle.error || remove.error)} />}
        {isLoading ? <StatePanel state="loading" /> : error ? <StatePanel state={errorState} detail={error instanceof Error ? error.message : String(error)} /> : !data?.length ? <StatePanel state="empty" /> : (
          <div className="border-y border-hairline">
            {data.map((project) => (
              <div key={project.id} className="grid gap-4 border-b border-hairline py-5 last:border-b-0 md:grid-cols-[1.4fr_.8fr_.8fr_auto] md:items-center">
                <div>
                  <Link href={`/projects/${project.id}`} className="focus-ring font-bold underline decoration-hairline-strong underline-offset-4">{project.name}</Link>
                  <p className="mt-1 max-w-xl text-xs leading-6 text-mute">{project.description}</p>
                </div>
                <div><div className="kicker">Environment</div><div className="mt-1 text-sm">{project.environment}</div></div>
                <div><div className="kicker">Provider / Model</div><div className="mt-1 text-sm">{project.provider} / {project.model}</div></div>
                <div className="flex items-center justify-end gap-2"><Button size="sm" variant="secondary" onClick={() => toggle.mutate({ id: project.id, enabled: !project.enabled })}>{project.enabled ? "Disable" : "Enable"}</Button><Button size="sm" variant="danger" onClick={() => remove.mutate(project.id)}>Delete</Button></div>
              </div>
            ))}
          </div>
        )}
      </div>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogTitle className="text-lg font-bold">[+] Create Project</DialogTitle>
          {create.error && <p role="alert" className="mt-3 text-xs decision-deny">{create.error.message}</p>}
          <div className="mt-5 grid gap-4">
            <label className="text-xs font-bold">Name<Input className="mt-2" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Customer Support Agent" /></label>
            <label className="text-xs font-bold">Description<Input className="mt-2" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="What this agent is allowed to do" /></label>
            <label className="text-xs font-bold">Environment<Select className="mt-2 w-full" value={form.environment} onChange={(e) => setForm({ ...form, environment: e.target.value as Environment })}><option value="development">development</option><option value="staging">staging</option><option value="production">production</option></Select></label>
            <div className="grid grid-cols-2 gap-3"><label className="text-xs font-bold">Provider<Input className="mt-2" value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value })} /></label><label className="text-xs font-bold">Default Model<Input className="mt-2" value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} /></label></div>
            <div className="flex justify-end gap-2 border-t border-hairline pt-4"><Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button><Button disabled={!form.name || create.isPending} onClick={() => create.mutate()}>{create.isPending ? "Creating…" : "Create Project"}</Button></div>
          </div>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
