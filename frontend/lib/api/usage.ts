import { usageSeries } from "@/lib/mock-data";
import { apiFetch, delay, demoMode } from "./client";

export interface UsageRow { label: string; requests: number; cost: number; inputTokens: number; outputTokens: number; p95: number; errors: number; averageLatency?: number; pricingConfigured?: boolean; }

export async function getUsage(projectId: string, filters: Record<string, string> = {}): Promise<UsageRow[]> {
  const query = new URLSearchParams({ project_id: projectId });
  Object.entries(filters).forEach(([key, value]) => { if (value) query.set(key, value); });
  if (!demoMode) return apiFetch<UsageRow[]>(`/v1/usage?${query}`);
  await delay();
  return usageSeries;
}
