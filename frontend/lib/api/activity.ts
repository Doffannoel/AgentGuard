import { activitySeed } from "@/lib/mock-data";
import type { ActivityEvent } from "@/lib/types";
import { apiFetch, delay, demoMode } from "./client";

export async function listActivity(projectId: string): Promise<ActivityEvent[]> {
  if (!demoMode) return apiFetch<ActivityEvent[]>(`/v1/audit/events?project_id=${encodeURIComponent(projectId)}`);
  await delay();
  return activitySeed;
}

export async function getActivity(eventId: string): Promise<ActivityEvent> {
  if (!demoMode) return apiFetch<ActivityEvent>(`/v1/audit/events/${eventId}`);
  await delay(140);
  return activitySeed.find((event) => event.id === eventId) ?? activitySeed[0];
}

export async function verifyAudit(projectId: string): Promise<{ checked: number; valid: boolean; verifiedAt: string }> {
  if (!demoMode) return apiFetch(`/v1/audit/verify?project_id=${encodeURIComponent(projectId)}`, { method: "POST" });
  await delay(700);
  return { checked: 14295, valid: true, verifiedAt: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) };
}
