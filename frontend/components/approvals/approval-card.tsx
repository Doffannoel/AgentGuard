import type { Approval } from "@/lib/types";
import { formatRupiah } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export function ApprovalCard({ approval, onResolve }: { approval: Approval; onResolve: (approval: Approval, action: "approve" | "reject") => void }) {
  return (
    <article className="border-t border-hairline py-5">
      <div className="grid gap-5 lg:grid-cols-[1fr_240px]">
        <div>
          <div className="flex items-center gap-3"><h3 className="font-bold">{approval.title}</h3><span className={`text-xs ${approval.status === "approved" ? "decision-allow" : approval.status === "rejected" ? "decision-deny" : "decision-approval"}`}>[{approval.status}]</span></div>
          <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div><div className="kicker">Agent</div><div className="mt-1">{approval.agent}</div></div>
            <div><div className="kicker">Customer</div><div className="mt-1">{approval.customer}</div></div>
            <div><div className="kicker">Amount</div><div className="mt-1 font-bold">{formatRupiah(approval.amount)}</div></div>
            <div><div className="kicker">Policy</div><div className="mt-1">{approval.policy}</div></div>
          </div>
          <p className="mt-4 text-xs leading-6 text-mute">{approval.reason}</p>
          {approval.status === "expired" ? <div className="mt-4 text-xs text-mute">Approval expired. The agent must request authorization again.</div> : approval.status !== "pending" && <div className="mt-4 border-t border-hairline pt-3 text-xs text-mute"><div>{approval.status === "approved" ? "Approved" : "Rejected"} by: {approval.resolvedBy}</div><div className="mt-1">Resolved at: {approval.resolvedAt}</div>{approval.comment && <div className="mt-1">Comment: {approval.comment}</div>}</div>}
        </div>
        {approval.status === "pending" && <div className="flex items-end justify-end gap-2"><Button variant="danger" onClick={() => onResolve(approval, "reject")}>Reject</Button><Button onClick={() => onResolve(approval, "approve")}>Approve</Button></div>}
      </div>
    </article>
  );
}
