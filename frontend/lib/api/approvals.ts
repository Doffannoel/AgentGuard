import { approvalsSeed } from "@/lib/mock-data";
import type { Approval } from "@/lib/types";
import { apiFetch, delay, demoMode } from "./client";

const approvals = approvalsSeed.map((item) => ({ ...item }));

export async function listApprovals(projectId: string): Promise<Approval[]> {
  if (!demoMode) return apiFetch<Approval[]>(`/v1/approvals?project_id=${encodeURIComponent(projectId)}`);
  await delay();
  return approvals.map((item) => ({ ...item }));
}

export async function resolveApproval(id: string, action: "approve" | "reject", comment?: string): Promise<Approval> {
  if (!demoMode) return apiFetch<Approval>(`/v1/approvals/${id}/${action}`, { method: "POST", body: JSON.stringify({ comment }) });
  await delay(360);
  const item = approvals.find((a) => a.id === id);
  if (!item) throw new Error("Approval not found");
  item.status = action === "approve" ? "approved" : "rejected";
  item.resolvedBy = "admin@example.com";
  item.resolvedAt = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  item.comment = comment;
  return { ...item };
}
