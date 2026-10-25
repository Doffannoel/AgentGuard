export function StatePanel({ state, detail }: { state: "loading" | "empty" | "error" | "unauthorized" | "policy_invalid" | "rate_limited" | "backend_unavailable"; detail?: string }) {
  const map = {
    loading: ["[~] loading", "Fetching console data…"],
    empty: ["[-] empty", "No records match this view."],
    error: ["[x] error", "The request could not be completed."],
    unauthorized: ["[x] unauthorized", "Your console session is not authorized."],
    policy_invalid: ["[x] policy_invalid", "The policy payload is invalid."],
    rate_limited: ["[!] rate_limited", "Too many requests. Retry after the backend window resets."],
    backend_unavailable: ["[x] backend_unavailable", "AgentGuard API is not reachable."]
  } as const;
  return <div className="border border-hairline bg-surface-soft p-5"><div className="font-bold">{map[state][0]}</div><div className="mt-2 text-sm text-mute">{detail ?? map[state][1]}</div></div>;
}
