import type { Decision, PolicyRule } from "@/lib/types";
import { policySeed } from "@/lib/mock-data";
import { apiFetch, delay, demoMode } from "./client";

const rules = [...policySeed];

export async function listPolicies(projectId: string): Promise<PolicyRule[]> {
  if (!demoMode) return apiFetch<PolicyRule[]>(`/v1/policies?project_id=${encodeURIComponent(projectId)}`);
  await delay();
  return [...rules];
}

export async function createPolicy(projectId: string, input: Omit<PolicyRule, "id">): Promise<PolicyRule> {
  if (!demoMode) return apiFetch<PolicyRule>("/v1/policies", { method: "POST", body: JSON.stringify({ projectId, ...input }) });
  await delay();
  const rule = { ...input, id: `${input.tool.replace(/\./g, "-")}-${Date.now().toString().slice(-4)}` };
  rules.push(rule);
  return rule;
}

export async function simulatePolicy(projectId: string, input: { tool: string; arguments: Record<string, unknown> }): Promise<{ decision: Decision; matchedRule: string; reason: string }> {
  if (!demoMode) return apiFetch("/v1/policies/simulate", { method: "POST", body: JSON.stringify({ ...input, projectId }) });
  await delay(320);
  const amount = Number(input.arguments.amount ?? 0);
  if (input.tool === "customer.delete" || input.tool === "customer.export_all") return { decision: "DENY", matchedRule: input.tool === "customer.delete" ? "deny-user-delete" : "deny-customer-export", reason: "Explicit deny rule matched." };
  if (input.tool === "payment.refund" && amount > 500000) return { decision: "REQUIRE_APPROVAL", matchedRule: "large-refund", reason: "Refund exceeds automatic threshold." };
  if (input.tool === "customer.search") return { decision: "ALLOW", matchedRule: "allow-customer-search", reason: "Explicit allow rule matched." };
  return { decision: "DENY", matchedRule: "default-deny", reason: "No allow rule matched for tool action." };
}

export async function publishPolicyDocument(projectId: string, document: unknown) {
  if (demoMode) throw new Error("YAML publication requires a backend connection.");
  return apiFetch("/v1/policies", { method: "POST", body: JSON.stringify({ projectId, document }) });
}
