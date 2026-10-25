"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/shell/app-shell";
import { PageHeading } from "@/components/shell/page-heading";
import { ApprovalCard } from "@/components/approvals/approval-card";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { StatePanel } from "@/components/ui/state-panel";
import { Textarea } from "@/components/ui/textarea";
import { listApprovals, resolveApproval } from "@/lib/api/approvals";
import type { Approval } from "@/lib/types";

export function ApprovalsPage({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const approvals = useQuery({ queryKey: ["approvals", projectId], queryFn: () => listApprovals(projectId) });
  const [target, setTarget] = useState<{ approval: Approval; action: "approve" | "reject" } | null>(null);
  const [comment, setComment] = useState("");
  const resolve = useMutation({
    mutationFn: () => target ? resolveApproval(target.approval.id, target.action, comment || undefined) : Promise.reject(new Error("No approval selected")),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["approvals", projectId] }); queryClient.invalidateQueries({ queryKey: ["summary", projectId] }); setTarget(null); setComment(""); }
  });

  const pending = approvals.data?.filter((a) => a.status === "pending").length ?? 0;
  return (
    <AppShell projectId={projectId}>
      <div className="page-wrap">
        <PageHeading eyebrow="Human approval" title="Approval Center" description="Sensitive tool calls pause at the policy boundary. Review redacted context, add an optional reason, then approve or reject the action." action={<div className="text-sm font-bold decision-approval">[!] {pending} pending</div>} />
        {approvals.isLoading ? <StatePanel state="loading" /> : approvals.error ? <StatePanel state="error" /> : !approvals.data?.length ? <StatePanel state="empty" /> : <div className="border-b border-hairline">{approvals.data.map((approval) => <ApprovalCard key={approval.id} approval={approval} onResolve={(item, action) => setTarget({ approval: item, action })} />)}</div>}
      </div>
      <Dialog open={Boolean(target)} onOpenChange={(open) => !open && setTarget(null)}>
        <DialogContent>
          <DialogTitle className="text-lg font-bold">[{target?.action === "approve" ? "+" : "x"}] {target?.action === "approve" ? "Approve action" : "Reject action"}</DialogTitle>
          <div className="mt-4 text-sm">{target?.approval.title} · {target?.approval.policy}</div>
          {resolve.error && <p role="alert" className="mt-3 text-xs decision-deny">{resolve.error.message}</p>}
          <label className="mt-5 block text-xs font-bold">Approval reason <span className="font-normal text-mute">(optional)</span><Textarea className="mt-2" value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Verified with customer service ticket." /></label>
          <div className="mt-5 flex justify-end gap-2 border-t border-hairline pt-4"><Button variant="secondary" onClick={() => setTarget(null)}>Cancel</Button><Button variant={target?.action === "reject" ? "danger" : "primary"} disabled={resolve.isPending} onClick={() => resolve.mutate()}>{resolve.isPending ? "Saving…" : target?.action === "approve" ? "Approve" : "Reject"}</Button></div>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
