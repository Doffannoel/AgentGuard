import { findingsSeed } from "@/lib/mock-data";
import type { SecurityFinding } from "@/lib/types";
import { apiFetch, delay, demoMode } from "./client";

export async function listFindings(projectId: string): Promise<SecurityFinding[]> {
  if (!demoMode) return apiFetch<SecurityFinding[]>(`/v1/guard-findings?project_id=${encodeURIComponent(projectId)}`);
  await delay(160);
  return findingsSeed;
}
