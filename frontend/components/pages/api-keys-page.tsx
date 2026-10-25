"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/shell/app-shell";
import { PageHeading } from "@/components/shell/page-heading";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { StatePanel } from "@/components/ui/state-panel";
import { createApiKey, listApiKeys, revokeApiKey } from "@/lib/api/api-keys";

export function ApiKeysPage({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const keys = useQuery({ queryKey: ["api-keys", projectId], queryFn: () => listApiKeys(projectId) });
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("Production Key");
  const [environment, setEnvironment] = useState<"live" | "test">("live");
  const [rawKey, setRawKey] = useState<string | null>(null);
  const create = useMutation({ gcTime: 0, mutationFn: () => createApiKey(projectId, name, environment), onSuccess: (data) => { setCreateOpen(false); setRawKey(data.rawKey); queryClient.invalidateQueries({ queryKey: ["api-keys", projectId] }); } });
  const revoke = useMutation({ mutationFn: (id: string) => revokeApiKey(projectId, id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["api-keys", projectId] }) });
  const dismissKey = () => { setRawKey(null); create.reset(); };

  return (
    <AppShell projectId={projectId}>
      <div className="page-wrap">
        <PageHeading eyebrow="Project authentication" title="API Keys" description="Project API keys authenticate AgentGuard gateway traffic. The backend stores only key metadata and a hash; the raw secret is displayed once." action={<Button onClick={() => setCreateOpen(true)}>[+] Create API Key</Button>} />
        {(create.error || revoke.error) && <StatePanel state="error" detail={String(create.error || revoke.error)} />}
        {keys.isLoading ? <StatePanel state="loading" /> : keys.error ? <StatePanel state="error" /> : <div className="border-y border-hairline">{keys.data?.map((key) => <div key={key.id} className="grid gap-4 border-b border-hairline py-5 last:border-0 lg:grid-cols-[1fr_1fr_1fr_auto] lg:items-center"><div><div className="font-bold">{key.name}</div><div className="mt-2 text-xs text-mute">{key.prefix}**********</div></div><div><div className="kicker">Created</div><div className="mt-1 text-sm">{key.createdAt}</div></div><div><div className="kicker">Last Used</div><div className="mt-1 text-sm">{key.lastUsedAt}</div></div><div>{key.revokedAt ? <span className="text-xs decision-deny">[x] revoked</span> : <Button size="sm" variant="danger" onClick={() => revoke.mutate(key.id)}>Revoke</Button>}</div></div>)}</div>}
        <div className="mt-6 border border-hairline bg-surface-soft p-4 text-xs leading-6 text-mute">[-] Raw API keys are never stored in localStorage by this frontend. After the one-time reveal dialog closes, the raw value is discarded from React state.</div>
      </div>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}><DialogContent><DialogTitle className="text-lg font-bold">[+] Create API Key</DialogTitle><div className="mt-5 grid gap-4"><label className="text-xs font-bold">Name<Input className="mt-2" value={name} onChange={(e) => setName(e.target.value)} /></label><label className="text-xs font-bold">Environment<Select className="mt-2 w-full" value={environment} onChange={(e) => setEnvironment(e.target.value as "live" | "test")}><option value="live">live</option><option value="test">test</option></Select></label><div className="flex justify-end gap-2 border-t border-hairline pt-4"><Button variant="secondary" onClick={() => setCreateOpen(false)}>Cancel</Button><Button disabled={!name || create.isPending} onClick={() => create.mutate()}>{create.isPending ? "Creating…" : "Create key"}</Button></div></div></DialogContent></Dialog>

      <Dialog open={Boolean(rawKey)} onOpenChange={(open) => !open && dismissKey()}><DialogContent><DialogTitle className="text-lg font-bold">[!] Copy this key now.</DialogTitle><p className="mt-2 text-xs leading-6 text-mute">You won't be able to see it again. This raw value exists only in this dialog's in-memory state.</p><div className="mt-5 break-all rounded-sm bg-surface-card p-4 text-sm">{rawKey}</div><div className="mt-4 flex justify-end gap-2"><Button variant="secondary" onClick={() => rawKey && navigator.clipboard.writeText(rawKey)}>Copy key</Button><Button onClick={dismissKey}>I saved it</Button></div></DialogContent></Dialog>
    </AppShell>
  );
}
