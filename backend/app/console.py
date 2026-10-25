from sqlalchemy import func, select

from .audit import append_event
from .db import now, project_lock, uid
from .errors import APIError
from .models import ApiKey, Approval, GuardFinding, LLMRequest, Project, TenantMember, ToolCall


def project_view(project):
    return {
        field: getattr(project, field)
        for field in (
            "id",
            "name",
            "description",
            "environment",
            "provider",
            "model",
            "enabled",
            "capture_mode",
            "requests_per_minute",
            "tokens_per_day",
            "budget_per_day",
        )
    }


def create_project(db, user, data):
    member = db.scalar(
        select(TenantMember)
        .where(TenantMember.user_id == user.id, TenantMember.role == "admin")
        .order_by(TenantMember.tenant_id)
    )
    if not member:
        raise APIError(403, "AG_POLICY_403", "Administrator membership required.")
    project = Project(id=uid("proj_"), tenant_id=member.tenant_id, **data.model_dump())
    db.add(project)
    db.flush()
    append_event(db, project.id, "PROJECT_CREATED", {"user_id": user.id})
    db.commit()
    return project_view(project)


def update_project(db, project, data):
    project = project_lock(db, project.id)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if value is None and field != "budget_per_day":
            raise APIError(422, "AG_INVALID_INPUT", "Project settings cannot be null.")
        setattr(project, field, value)
    append_event(db, project.id, "PROJECT_UPDATED", {"fields": list(changes)})
    db.commit()
    return project_view(project)


def delete_project(db, project):
    project = project_lock(db, project.id)
    project.enabled, project.deleted_at = False, now()
    for key in db.scalars(select(ApiKey).where(ApiKey.project_id == project.id, ApiKey.revoked_at.is_(None))):
        key.revoked_at = now()
    append_event(db, project.id, "PROJECT_DELETED", {})
    db.commit()
    return {"id": project.id}


def summary(db, project_id):
    def count(model, *conditions):
        return (
            db.scalar(
                select(func.count()).select_from(model).where(model.project_id == project_id, *conditions)
            )
            or 0
        )

    return {
        "requests": count(LLMRequest),
        "toolCalls": count(ToolCall),
        "blocked": count(ToolCall, ToolCall.status == "DENIED"),
        "pendingApprovals": count(Approval, Approval.status == "PENDING", Approval.expires_at > now()),
        "securityFindings": count(GuardFinding),
        "unpricedRequests": count(LLMRequest, LLMRequest.pricing_configured.is_(False)),
        "estimatedCost": db.scalar(
            select(func.coalesce(func.sum(LLMRequest.estimated_cost), 0)).where(
                LLMRequest.project_id == project_id
            )
        ),
    }
