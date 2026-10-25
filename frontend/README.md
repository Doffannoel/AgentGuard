# AgentGuard

Backend FastAPI kini tersedia di [`backend/`](backend/README.md), beserta PostgreSQL, migrasi, worker replay, autentikasi console, gateway, policy, approval, audit, usage, dan telemetry. Lihat [analisis frontend dan pemetaan RFC](docs/BACKEND_IMPLEMENTATION.md).

Security control console for AgentGuard, rebuilt directly from the supplied frontend RFC, core AgentGuard RFC, and OpenCode-derived design system.

## Product intent

AgentGuard sits between AI applications/agents and the model/tool systems they can affect. The frontend does **not** enforce security itself; it explains backend security decisions and gives operators the workflows needed to manage projects, policies, approvals, audit events, replay suites, API keys, usage, and findings.

The console is optimized for answering:

- What did the AI do?
- Why was an action allowed, denied, or sent to approval?
- Which policy/rule produced the decision?
- Is the agent regressing against adversarial scenarios?
- What are the cost and latency characteristics?

## Stack

- Next.js App Router + TypeScript
- Tailwind CSS
- shadcn/ui-style primitives built on Radix + CVA
- TanStack Query for server state
- Zod + YAML for policy validation
- Playwright for E2E coverage

## Design system

The UI adapts the supplied `DESIGN-opencode.ai.md` to an in-product security console:

- warm cream `#fdfcfc` canvas
- near-black `#201d1d` ink
- monospace-only typography
- 4px radius on interactive controls
- squared containers with 1px hairline borders
- no shadows and no gradients
- ASCII markers (`[+]`, `[-]`, `[x]`, `[!]`) instead of decorative iconography
- semantic colors used only for in-product status/decision signals

`Berkeley Mono` is referenced by CSS only. No proprietary font files are bundled. The stack falls back to IBM Plex Mono and system monospace fonts.

## Routes

```text
/login
/projects
/projects/:projectId
/projects/:projectId/policies
/projects/:projectId/activity
/activity/:eventId
/projects/:projectId/approvals
/projects/:projectId/red-team
/projects/:projectId/usage
/projects/:projectId/api-keys
/projects/:projectId/settings
```

## Demo mode

The project runs without a backend. If `NEXT_PUBLIC_AGENTGUARD_API_URL` is blank, typed API modules use a local in-memory demo adapter. This keeps all data access behind `lib/api/*` rather than scattering `fetch()` calls through components.

To wire a real AgentGuard FastAPI backend:

```bash
cp .env.example .env.local
# then set NEXT_PUBLIC_AGENTGUARD_API_URL=https://your-agentguard-api.example.com
```

## Run

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

With an empty API URL, login uses the demo adapter. With a backend URL, sign in using an administrator created through the backend CLI.

## Implemented RFC flows

### P0

- login
- project list/create
- API key list/create/revoke with one-time raw-key reveal
- policy list grouped by allow / approval / deny
- simple policy editor
- policy simulation
- activity table with required filters
- activity decision detail
- human approval/rejection with optional comment

### P1

- security findings summary
- audit-chain verification interaction
- red-team replay state and cases
- replay before/current comparison
- usage/cost/latency/error views

### P2 included as portfolio enhancement

- YAML policy editor validated by YAML + Zod
- policy-version comparison presentation in Red Team

## Security-conscious frontend behavior

- raw API keys are never written to localStorage
- redacted payload examples are used in audit detail
- backend is treated as authoritative for policy validation and security decisions
- tool actions are presented around the `ALLOW`, `DENY`, `REQUIRE_APPROVAL` model
- error-state components cover loading, empty, error, unauthorized, policy_invalid, rate_limited, and backend_unavailable

## Project structure

```text
app/
  login/
  projects/
    [projectId]/
      policies/
      activity/
      approvals/
      red-team/
      usage/
      api-keys/
      settings/
  activity/[eventId]/
components/
  ui/
  shell/
  policy/
  activity/
  approvals/
  redteam/
  charts/
  pages/
lib/
  api/
  schemas/
  mock-data.ts
  types.ts
  utils.ts
tests/e2e/
```

## Notes

The console supports both demo data and the FastAPI backend. Follow [`backend/README.md`](backend/README.md) for setup, tests, and current MVP limits.
