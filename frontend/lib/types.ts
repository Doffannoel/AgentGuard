export type Decision = "ALLOW" | "DENY" | "REQUIRE_APPROVAL";
export type Environment = "production" | "staging" | "development";
export type Severity = "critical" | "high" | "medium" | "low";

export interface Project {
  id: string;
  name: string;
  description: string;
  environment: Environment;
  provider: string;
  model: string;
  enabled: boolean;
  capture_mode?: "OFF" | "REDACTED" | "FULL";
  requests_per_minute?: number;
  tokens_per_day?: number;
  budget_per_day?: number | null;
}

export interface DashboardSummary {
  requests: number;
  toolCalls: number;
  blocked: number;
  pendingApprovals: number;
  securityFindings: number;
  estimatedCost: number;
  unpricedRequests?: number;
}

export interface ActivityEvent {
  id: string;
  projectId?: string;
  time: string;
  agent: string;
  action: string;
  tool: string;
  decision: Decision;
  latencyMs: number;
  traceId: string;
  requestId: string;
  environment: Environment;
  severity: Severity;
  policy: string;
  rule?: string;
  reason: string;
  arguments: Record<string, unknown>;
  findings?: Array<{ type: string; detected: string; action: "REDACTED" | "FLAGGED" }>;
}

export interface PolicyRule {
  id: string;
  description: string;
  tool: string;
  condition?: string;
  effect: Decision;
  enabled: boolean;
}

export interface Approval {
  id: string;
  title: string;
  agent: string;
  customer: string;
  amount: number;
  reason: string;
  policy: string;
  status: "pending" | "approved" | "rejected" | "expired";
  resolvedBy?: string;
  resolvedAt?: string;
  comment?: string;
}

export interface ApiKeyRecord {
  id: string;
  name: string;
  prefix: string;
  environment: "live" | "test";
  createdAt: string;
  lastUsedAt: string;
  revokedAt?: string;
}

export interface SecurityFinding {
  id: string;
  type: "SECRET_EXPOSURE" | "PII_DETECTED" | "SUSPICIOUS_INSTRUCTION" | "BUDGET_VIOLATION";
  detected: string;
  action: "REDACTED" | "FLAGGED" | "BLOCKED";
  severity: Severity;
  requestId: string;
}

export interface ReplayCase {
  id: string;
  suite: string;
  attack: string;
  input: string;
  expectedTool: string;
  expectedDecision: Decision;
  actualTool: string;
  actualDecision: Decision | null;
  passed: boolean | null;
}
