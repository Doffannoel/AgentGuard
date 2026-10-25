from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import audit, auth, console, gateway, policies, replay, schemas, tools, usage
from .config import settings
from .db import get_db, now, project_lock
from .errors import APIError
from .models import (
    ApiKey,
    Approval,
    AttackCase,
    AuditEvent,
    ConsoleSession,
    GuardFinding,
    Policy,
    PolicyVersion,
    Project,
    ReplayRun,
    TenantMember,
    Tool,
    User,
)

router = APIRouter(prefix="/v1")


def resource(db, model, resource_id):
    row = db.get(model, resource_id)
    if not row:
        raise APIError(404, "AG_NOT_FOUND", "Resource not found.")
    return row


@router.post("/console/auth/login")
def login(data: schemas.LoginInput, request: Request, response: Response, db: Session = Depends(get_db)):
    user, raw = auth.login(
        db, data.email, data.password, request.client.host if request.client else "unknown"
    )
    response.set_cookie(
        "ag_session",
        raw,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=settings.session_hours * 3600,
        path="/",
    )
    return {"email": user.email, "authenticated": True}


@router.get("/console/auth/session")
def session(user: User = Depends(auth.console_user)):
    return {"email": user.email, "authenticated": True}


@router.post("/console/auth/logout")
def logout(
    request: Request,
    response: Response,
    user: User = Depends(auth.console_user),
    db: Session = Depends(get_db),
):
    row = db.scalar(
        select(ConsoleSession).where(
            ConsoleSession.token_hash == auth.token_hash(request.cookies.get("ag_session", ""))
        )
    )
    if row:
        db.delete(row)
        db.commit()
    response.delete_cookie("ag_session", path="/")
    return {"authenticated": False}


@router.get("/console/projects")
def list_projects(user: User = Depends(auth.console_user), db: Session = Depends(get_db)):
    return [
        console.project_view(p)
        for p in db.scalars(
            select(Project)
            .join(TenantMember, Project.tenant_id == TenantMember.tenant_id)
            .where(TenantMember.user_id == user.id, Project.deleted_at.is_(None))
            .order_by(Project.name)
        )
    ]


@router.post("/console/projects", status_code=201)
def create_project(
    data: schemas.ProjectInput, user: User = Depends(auth.console_user), db: Session = Depends(get_db)
):
    return console.create_project(db, user, data)


@router.get("/console/projects/{project_id}")
def get_project(project_id: str, user: User = Depends(auth.console_user), db: Session = Depends(get_db)):
    return console.project_view(auth.access_project(db, user, project_id))


@router.patch("/console/projects/{project_id}")
def patch_project(
    project_id: str,
    data: schemas.ProjectPatch,
    user: User = Depends(auth.console_user),
    db: Session = Depends(get_db),
):
    return console.update_project(db, auth.access_project(db, user, project_id, True), data)


@router.delete("/console/projects/{project_id}")
def delete_project(project_id: str, user: User = Depends(auth.console_user), db: Session = Depends(get_db)):
    return console.delete_project(db, auth.access_project(db, user, project_id, True))


@router.get("/console/projects/{project_id}/summary")
def summary(project_id: str, user: User = Depends(auth.console_user), db: Session = Depends(get_db)):
    auth.access_project(db, user, project_id)
    return console.summary(db, project_id)


@router.get("/console/projects/{project_id}/api-keys")
def keys(project_id: str, user: User = Depends(auth.console_user), db: Session = Depends(get_db)):
    auth.access_project(db, user, project_id, True)
    return [auth.key_view(k) for k in db.scalars(select(ApiKey).where(ApiKey.project_id == project_id))]


@router.post("/console/projects/{project_id}/api-keys", status_code=201)
def create_key(
    project_id: str,
    data: schemas.KeyInput,
    user: User = Depends(auth.console_user),
    db: Session = Depends(get_db),
):
    auth.access_project(db, user, project_id, True)
    return auth.create_key(db, project_id, data.name, data.environment)


@router.post("/console/projects/{project_id}/api-keys/{key_id}/revoke")
def revoke_key(
    project_id: str, key_id: str, user: User = Depends(auth.console_user), db: Session = Depends(get_db)
):
    auth.access_project(db, user, project_id, True)
    project_lock(db, project_id)
    key = resource(db, ApiKey, key_id)
    if key.project_id != project_id:
        raise APIError(404, "AG_NOT_FOUND", "Key not found.")
    key.revoked_at = now()
    audit.append_event(db, project_id, "API_KEY_REVOKED", {"key_id": key.id})
    db.commit()
    return auth.key_view(key)


@router.get("/policies")
def list_policies(project_id: str, user: User = Depends(auth.console_user), db: Session = Depends(get_db)):
    auth.access_project(db, user, project_id)
    version = policies.active_policy(db, project_id)
    return [policies.rule_view(rule) for rule in version.document["rules"]] if version else []


@router.post("/policies", status_code=201)
def publish_policy(
    data: schemas.SimpleRule | schemas.PolicyInput,
    user: User = Depends(auth.console_user),
    db: Session = Depends(get_db),
):
    auth.access_project(db, user, data.projectId, True)
    if isinstance(data, schemas.SimpleRule):
        rule = policies.simple_rule(data)
        policies.publish(db, data.projectId, rule, append=True)
        return policies.rule_view(rule)
    version = policies.publish(db, data.projectId, data.document)
    return {
        "id": version.policy_id,
        "version": version.version,
        "version_id": version.id,
        "document": version.document,
    }


@router.post("/policies/simulate")
def simulate(
    data: schemas.SimulateInput, user: User = Depends(auth.console_user), db: Session = Depends(get_db)
):
    project = auth.access_project(db, user, data.projectId)
    result = tools.inspect_tool(db, project, data, user.id, policies.active_policy(db, project.id))[0]
    return {**result, "matchedRule": result["rule_id"] or "default-deny", "reason": result["reason_code"]}


@router.get("/policies/versions")
def policy_versions(project_id: str, user: User = Depends(auth.console_user), db: Session = Depends(get_db)):
    auth.access_project(db, user, project_id)
    return [
        {"id": v.id, "policy_id": v.policy_id, "version": v.version, "document": v.document}
        for v in db.scalars(
            select(PolicyVersion)
            .join(Policy)
            .where(Policy.project_id == project_id)
            .order_by(PolicyVersion.version.desc())
        )
    ]


@router.post("/policies/{policy_id}/versions", status_code=201)
def new_policy_version(
    policy_id: str,
    data: schemas.PolicyInput,
    user: User = Depends(auth.console_user),
    db: Session = Depends(get_db),
):
    policy = resource(db, Policy, policy_id)
    auth.access_project(db, user, policy.project_id, True)
    if data.projectId != policy.project_id:
        raise APIError(404, "AG_NOT_FOUND", "Policy not found.")
    version = policies.publish(db, policy.project_id, data.document)
    return {"id": version.id, "version": version.version, "document": version.document}


@router.get("/console/projects/{project_id}/tools")
def list_tools(project_id: str, user: User = Depends(auth.console_user), db: Session = Depends(get_db)):
    auth.access_project(db, user, project_id)
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "risk_level": t.risk_level,
            "executor_type": t.executor_type,
            "input_schema": t.input_schema,
            "enabled": t.enabled,
        }
        for t in db.scalars(select(Tool).where(Tool.project_id == project_id))
    ]


@router.put("/console/projects/{project_id}/tools/{name}")
def register_tool(
    project_id: str,
    name: str,
    data: schemas.ToolInput,
    user: User = Depends(auth.console_user),
    db: Session = Depends(get_db),
):
    auth.access_project(db, user, project_id, True)
    return tools.register(db, project_id, name, data, user.id)


@router.post("/chat/completions")
async def chat(
    data: schemas.CanonicalLLMRequest,
    request: Request,
    key: ApiKey = Depends(auth.agent_key),
    db: Session = Depends(get_db),
):
    return await gateway.chat(db, key, data, request.state.request_id)


@router.post("/tools/authorize")
def authorize(
    data: schemas.ToolRequest, key: ApiKey = Depends(auth.agent_key), db: Session = Depends(get_db)
):
    usage.rate_limit(db, key)
    result = tools.authorize(db, key, data)
    db.commit()
    return result


@router.post("/tools/execute")
def execute(data: schemas.ExecuteInput, key: ApiKey = Depends(auth.agent_key), db: Session = Depends(get_db)):
    usage.rate_limit(db, key)
    return tools.execute(db, key, data)


@router.get("/approvals")
def approvals(project_id: str, user: User = Depends(auth.console_user), db: Session = Depends(get_db)):
    auth.access_project(db, user, project_id)
    return [
        tools.approval_view(db, a)
        for a in db.scalars(
            select(Approval).where(Approval.project_id == project_id).order_by(Approval.requested_at.desc())
        )
    ]


@router.post("/approvals/{approval_id}/{action}")
def resolve_approval(
    approval_id: str,
    action: Literal["approve", "reject"],
    data: schemas.ResolveInput,
    user: User = Depends(auth.console_user),
    db: Session = Depends(get_db),
):
    approval = resource(db, Approval, approval_id)
    auth.access_project(db, user, approval.project_id, True)
    return tools.resolve_approval(db, approval, user, action, data.comment)


@router.get("/audit/events")
def events(
    project_id: str,
    limit: int = 200,
    offset: int = 0,
    user: User = Depends(auth.console_user),
    db: Session = Depends(get_db),
):
    project = auth.access_project(db, user, project_id)
    query = (
        select(AuditEvent)
        .where(AuditEvent.project_id == project_id)
        .order_by(AuditEvent.sequence.desc())
        .limit(max(1, min(limit, 1000)))
        .offset(max(0, offset))
    )
    return [audit.activity_view(e, project) for e in db.scalars(query)]


@router.get("/audit/events/{event_id}")
def event(event_id: str, user: User = Depends(auth.console_user), db: Session = Depends(get_db)):
    row = resource(db, AuditEvent, event_id)
    return audit.activity_view(row, auth.access_project(db, user, row.project_id))


@router.post("/audit/verify")
def verify(project_id: str, user: User = Depends(auth.console_user), db: Session = Depends(get_db)):
    auth.access_project(db, user, project_id)
    return audit.verify(db, project_id)


@router.get("/guard-findings")
def findings(project_id: str, user: User = Depends(auth.console_user), db: Session = Depends(get_db)):
    auth.access_project(db, user, project_id)
    return [
        {"id": f.id, "requestId": f.request_id, **f.finding}
        for f in db.scalars(select(GuardFinding).where(GuardFinding.project_id == project_id).limit(1000))
    ]


@router.get("/usage")
def get_usage(
    project_id: str,
    provider: str | None = None,
    model: str | None = None,
    environment: str | None = None,
    feature: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    period: Literal["hourly", "daily"] | None = None,
    user: User = Depends(auth.console_user),
    db: Session = Depends(get_db),
):
    auth.access_project(db, user, project_id)
    return usage.usage_rows(db, project_id, provider, model, environment, feature, since, until, period)


@router.get("/attack-cases")
def cases(project_id: str, user: User = Depends(auth.console_user), db: Session = Depends(get_db)):
    auth.access_project(db, user, project_id)
    return [
        replay.case_view(db, c)
        for c in db.scalars(select(AttackCase).where(AttackCase.project_id == project_id))
    ]


@router.post("/attack-cases", status_code=201)
def create_case(
    data: schemas.AttackInput, user: User = Depends(auth.console_user), db: Session = Depends(get_db)
):
    auth.access_project(db, user, data.projectId, True)
    case = AttackCase(project_id=data.projectId, **data.model_dump(exclude={"projectId"}))
    db.add(case)
    db.flush()
    audit.append_event(db, data.projectId, "ATTACK_CASE_CREATED", {"case_id": case.id, "user_id": user.id})
    db.commit()
    return replay.case_view(db, case)


@router.post("/replay-runs", status_code=202)
def create_run(
    data: schemas.ReplayInput, user: User = Depends(auth.console_user), db: Session = Depends(get_db)
):
    auth.access_project(db, user, data.projectId, True)
    return replay.enqueue(db, data.projectId)


@router.get("/replay-runs/{run_id}")
def get_run(run_id: str, user: User = Depends(auth.console_user), db: Session = Depends(get_db)):
    run = resource(db, ReplayRun, run_id)
    auth.access_project(db, user, run.project_id)
    return replay.run_view(db, run)
