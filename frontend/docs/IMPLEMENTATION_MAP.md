# Source → Implementation Map

This project treats the three supplied Markdown documents as source of truth.

## RFC Frontend — AgentGuard

| RFC area | Implementation |
|---|---|
| Login | `/login` |
| Projects | `/projects` |
| Project Dashboard | `/projects/:projectId` |
| API Keys | `/projects/:projectId/api-keys` |
| Policy Management | `/projects/:projectId/policies` |
| Policy Editor | simple + YAML modes on Policies page |
| Policy Simulation | Test Policy block on Policies page |
| Activity | `/projects/:projectId/activity` |
| Activity Detail | `/activity/:eventId` |
| Approval Center | `/projects/:projectId/approvals` |
| Red Team / Replay | `/projects/:projectId/red-team` |
| Usage | `/projects/:projectId/usage` |
| Security Findings | expandable finding detail on project dashboard |
| Audit Integrity | verify-chain interaction on project dashboard |
| Error States | reusable `StatePanel` + state catalogue in Settings |
| Typed API client | `lib/api/*` |
| TanStack Query | all server state queries/mutations |
| Zod | YAML policy validation |
| Playwright | `tests/e2e/smoke.spec.ts` |

## DESIGN-opencode.ai

Implemented directly:

- warm cream canvas `#fdfcfc`
- ink `#201d1d`
- monospace-only type stack
- 4px radius on interactive controls
- square containers
- hairline separators
- no drop shadows
- no gradients
- ASCII markers as primary icon vocabulary
- semantic status colors reserved for security/decision signals

No proprietary font files are included.

## RFC-001 — AgentGuard

UI semantics reflect:

- `ALLOW`, `DENY`, `REQUIRE_APPROVAL`
- default-deny tool-action framing
- deterministic policy context
- human approval flow
- PII/secret redaction findings
- tamper-evident audit verification
- adversarial replay/regression workflow
- usage/cost/latency telemetry
- backend-authoritative security decisions
