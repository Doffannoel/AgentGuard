const BASE_URL = process.env.NEXT_PUBLIC_AGENTGUARD_API_URL?.replace(/\/$/, "") ?? "";

export const demoMode = !BASE_URL;

export type ApiErrorKind = "error" | "unauthorized" | "policy_invalid" | "rate_limited" | "backend_unavailable";

export class ApiError extends Error {
  constructor(public readonly kind: ApiErrorKind, message: string, public readonly status?: number) {
    super(message);
    this.name = "ApiError";
  }
}

export function parseApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (error instanceof Error) {
    return new ApiError("error", error.message);
  }
  return new ApiError("error", "AgentGuard API request failed.");
}

export function getApiErrorState(error: unknown): "error" | "unauthorized" | "policy_invalid" | "rate_limited" | "backend_unavailable" {
  const apiError = parseApiError(error);
  if (apiError.kind === "backend_unavailable") return "backend_unavailable";
  if (apiError.kind === "unauthorized") return "unauthorized";
  if (apiError.kind === "policy_invalid") return "policy_invalid";
  if (apiError.kind === "rate_limited") return "rate_limited";
  return "error";
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  if (!BASE_URL) throw new Error("Demo adapter should handle this request.");

  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      credentials: "include",
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) }
    });

    if (!response.ok) {
      const body = await response.json().catch(() => null);
      const message = body?.error?.message || body?.message || `AgentGuard API ${response.status}`;

      if (response.status === 401) {
        if (typeof window !== "undefined" && !path.includes("/auth/login")) {
          window.location.assign("/login");
        }
        throw new ApiError("unauthorized", "Your console session is not authorized.", response.status);
      }

      if (response.status === 429) {
        throw new ApiError("rate_limited", "Too many requests. Retry after the backend window resets.", response.status);
      }
      if (response.status === 400 && (message.toLowerCase().includes("policy") || message.toLowerCase().includes("yaml") || message.toLowerCase().includes("invalid"))) {
        throw new ApiError("policy_invalid", message, response.status);
      }
      throw new ApiError("error", message, response.status);
    }

    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof TypeError) {
      throw new ApiError("backend_unavailable", "AgentGuard API is not reachable.");
    }
    throw error;
  }
}

export async function delay(ms = 220) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}
