import { apiFetch, delay, demoMode } from "./client";
import { dashboardSeed, projectsSeed } from "@/lib/mock-data";
import type { DashboardSummary, Project } from "@/lib/types";

const projects = [...projectsSeed];

export async function listProjects(): Promise<Project[]> {
  if (!demoMode) return apiFetch<Project[]>("/v1/console/projects");
  await delay();
  return [...projects];
}

export async function getProject(projectId: string): Promise<Project> {
  if (!demoMode) return apiFetch<Project>(`/v1/console/projects/${projectId}`);
  await delay(120);
  return projects.find((p) => p.id === projectId) ?? projects[0];
}

export async function getProjectSummary(projectId: string): Promise<DashboardSummary> {
  if (!demoMode) return apiFetch<DashboardSummary>(`/v1/console/projects/${projectId}/summary`);
  await delay(180);
  return dashboardSeed;
}

export async function createProject(input: Omit<Project, "id" | "enabled">): Promise<Project> {
  if (!demoMode) return apiFetch<Project>("/v1/console/projects", { method: "POST", body: JSON.stringify(input) });
  await delay();
  const p: Project = { ...input, id: input.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || `project-${Date.now()}`, enabled: true };
  projects.unshift(p);
  return p;
}

export async function setProjectEnabled(projectId: string, enabled: boolean): Promise<Project> {
  if (!demoMode) return apiFetch<Project>(`/v1/console/projects/${projectId}`, { method: "PATCH", body: JSON.stringify({ enabled }) });
  await delay(180);
  const project = projects.find((item) => item.id === projectId);
  if (!project) throw new Error("Project not found");
  project.enabled = enabled;
  return { ...project };
}

export async function deleteProject(projectId: string): Promise<{ id: string }> {
  if (!demoMode) return apiFetch<{ id: string }>(`/v1/console/projects/${projectId}`, { method: "DELETE" });
  await delay(180);
  const index = projects.findIndex((item) => item.id === projectId);
  if (index >= 0) projects.splice(index, 1);
  return { id: projectId };
}

export async function updateProject(projectId: string, input: Partial<Project>): Promise<Project> {
  if (!demoMode) return apiFetch(`/v1/console/projects/${projectId}`, { method: "PATCH", body: JSON.stringify(input) });
  const project = projects.find((item) => item.id === projectId);
  if (!project) throw new Error("Project not found");
  Object.assign(project, input);
  return { ...project };
}
