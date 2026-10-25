# AgentGuard Frontend API Contract

The frontend RFC requires a typed API client and the core RFC defines the primary AgentGuard API surface. The modules in `lib/api/` are the only place UI components should talk to the backend.

## Console / project endpoints

These administrative routes are frontend-oriented aliases and should use console authentication, not project API keys.

Console authentication uses an HttpOnly `ag_session` cookie. Clients send `credentials: include`; mutation requests must include an allowed `Origin`. Agent routes use a project API key in `Authorization: Bearer ...`. All console resource access is checked against tenant membership.

```text
POST /v1/console/auth/login
GET  /v1/console/auth/session
POST /v1/console/auth/logout
GET  /v1/console/projects
POST /v1/console/projects
GET  /v1/console/projects/:projectId
PATCH /v1/console/projects/:projectId
DELETE /v1/console/projects/:projectId
GET  /v1/console/projects/:projectId/summary
GET  /v1/console/projects/:projectId/api-keys
POST /v1/console/projects/:projectId/api-keys
POST /v1/console/projects/:projectId/api-keys/:keyId/revoke
GET  /v1/console/projects/:projectId/tools
PUT  /v1/console/projects/:projectId/tools/:name
```

`POST /v1/policies/simulate` requires `{ projectId, tool, arguments, context? }`.
`POST /v1/policies` accepts the existing simple-rule DTO or `{ projectId, document }` for a native policy document / rule array. Publishing a full document replaces the active version; it does not mutate historical versions.
Project deletion archives the project and revokes its keys while retaining audit history.

Gateway routes: `POST /v1/chat/completions`, `POST /v1/tools/authorize`, `POST /v1/tools/execute`. Detailed request schemas are generated at `/docs`. See [backend setup](backend/README.md) for examples and limits.

## Core RFC endpoints used by the console

```text
GET  /v1/approvals
POST /v1/approvals/{id}/approve
POST /v1/approvals/{id}/reject

GET  /v1/audit/events
GET  /v1/audit/events/{id}
POST /v1/audit/verify

GET  /v1/policies
POST /v1/policies
POST /v1/policies/{id}/versions
POST /v1/policies/simulate

GET  /v1/attack-cases
POST /v1/attack-cases
POST /v1/replay-runs
GET  /v1/replay-runs/{id}

GET  /v1/usage
GET  /v1/guard-findings
```

## Decision vocabulary

```text
ALLOW
DENY
REQUIRE_APPROVAL
```

Tool actions should be treated as default-deny when no allow rule matches, subject to the backend's authoritative policy implementation.

## Error mapping

The UI has explicit states for:

```text
loading
empty
error
unauthorized
policy_invalid
rate_limited
backend_unavailable
```

A production client should map backend status/error codes into these presentation states in `lib/api/client.ts` rather than handling them ad hoc in components.

## API keys

A create-key response may include the full raw key **once**. After the user dismisses the one-time reveal view, the frontend should discard that raw value. Never persist it to localStorage.
