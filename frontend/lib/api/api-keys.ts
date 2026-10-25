import { apiKeysSeed } from "@/lib/mock-data";
import type { ApiKeyRecord } from "@/lib/types";
import { apiFetch, delay, demoMode } from "./client";

const keys = apiKeysSeed.map((key) => ({ ...key }));

export async function listApiKeys(projectId: string): Promise<ApiKeyRecord[]> {
  if (!demoMode) return apiFetch<ApiKeyRecord[]>(`/v1/console/projects/${projectId}/api-keys`);
  await delay();
  return keys.map((key) => ({ ...key }));
}

export async function createApiKey(projectId: string, name: string, environment: "live" | "test"): Promise<{ record: ApiKeyRecord; rawKey: string }> {
  if (!demoMode) return apiFetch(`/v1/console/projects/${projectId}/api-keys`, { method: "POST", body: JSON.stringify({ name, environment }) });
  await delay(340);
  const prefix = `ag_${environment}_${Math.random().toString(36).slice(2, 6).toUpperCase()}`;
  const record: ApiKeyRecord = { id: `key_${Date.now()}`, name, prefix, environment, createdAt: new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }), lastUsedAt: "Never" };
  keys.push(record);
  return { record, rawKey: `${prefix}_${crypto.randomUUID().replace(/-/g, "")}` };
}

export async function revokeApiKey(projectId: string, id: string): Promise<ApiKeyRecord> {
  if (!demoMode) return apiFetch(`/v1/console/projects/${projectId}/api-keys/${id}/revoke`, { method: "POST" });
  await delay();
  const key = keys.find((item) => item.id === id);
  if (!key) throw new Error("API key not found");
  key.revokedAt = new Date().toISOString();
  return { ...key };
}
