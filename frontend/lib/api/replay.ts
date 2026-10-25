import { replayCasesSeed } from "@/lib/mock-data";
import type { ReplayCase } from "@/lib/types";
import { apiFetch, delay, demoMode } from "./client";

export async function listReplayCases(projectId: string): Promise<ReplayCase[]> {
  if (!demoMode) return apiFetch<ReplayCase[]>(`/v1/attack-cases?project_id=${encodeURIComponent(projectId)}`);
  await delay();
  return replayCasesSeed;
}

export async function createReplayRun(projectId: string): Promise<{ id: string; status: "queued" }> {
  if (!demoMode) return apiFetch("/v1/replay-runs", { method: "POST", body: JSON.stringify({ projectId }) });
  await delay(250);
  return { id: `replay_${Date.now()}`, status: "queued" };
}

export interface ReplayRun {
  id: string;
  status: "queued" | "running" | "completed" | "failed";
  total: number;
  completed: number;
  passed: number;
  failed: number;
  policyVersion: string | null;
  error?: string;
}

export async function getReplayRun(id: string): Promise<ReplayRun> {
  return apiFetch(`/v1/replay-runs/${id}`);
}
