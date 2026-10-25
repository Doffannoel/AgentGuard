from sqlalchemy import select

from .db import digest, now, project_lock, uid
from .guards import inspect
from .models import AuditEvent


def event_hash(event):
    return digest(
        {
            "event_id": event.id,
            "project_id": event.project_id,
            "sequence": event.sequence,
            "event_type": event.event_type,
            "timestamp": event.timestamp.isoformat(),
            "payload": event.payload,
            "previous_hash": event.previous_hash,
        }
    )


def append_event(db, project_id, event_type, payload):
    project = project_lock(db, project_id)
    event = AuditEvent(
        id=uid("evt_"),
        project_id=project_id,
        sequence=project.audit_count + 1,
        event_type=event_type,
        timestamp=now(),
        payload=inspect(payload)[0],
        previous_hash=project.audit_head,
    )
    event.event_hash = event_hash(event)
    project.audit_head, project.audit_count = event.event_hash, event.sequence
    db.add(event)
    db.flush()
    return event


def verify(db, project_id):
    project = project_lock(db, project_id)
    previous = ""
    count = 0
    for event in db.scalars(
        select(AuditEvent).where(AuditEvent.project_id == project_id).order_by(AuditEvent.sequence)
    ):
        count += 1
        if (
            event.sequence != count
            or event.previous_hash != previous
            or event.event_hash != event_hash(event)
        ):
            return {
                "valid": False,
                "checked": count,
                "verified_events": count - 1,
                "failed_event": event.id,
                "verifiedAt": now().isoformat(),
            }
        previous = event.event_hash
    return {
        "valid": count == project.audit_count and previous == project.audit_head,
        "checked": count,
        "verified_events": count,
        "head": previous,
        "verifiedAt": now().isoformat(),
    }


def activity_view(event, project):
    payload = event.payload
    return {
        "id": event.id,
        "projectId": event.project_id,
        "time": event.timestamp.isoformat() + "Z",
        "agent": payload.get("actor", "agent"),
        "action": event.event_type,
        "tool": payload.get("tool", event.event_type.lower()),
        "decision": payload.get(
            "decision",
            "DENY"
            if "DENIED" in event.event_type
            else "REQUIRE_APPROVAL"
            if event.event_type == "APPROVAL_REQUESTED"
            else "ALLOW",
        ),
        "latencyMs": payload.get("latency_ms", 0),
        "traceId": payload.get("trace_id", ""),
        "requestId": payload.get("request_id", ""),
        "environment": project.environment,
        "severity": payload.get("severity", "low"),
        "policy": payload.get("policy_version", "default"),
        "rule": payload.get("rule_id"),
        "reason": payload.get("reason_code", event.event_type),
        "arguments": payload.get("arguments", {}),
        "findings": payload.get("findings", []),
        "event_type": event.event_type,
        "payload": payload,
        "previous_hash": event.previous_hash,
        "event_hash": event.event_hash,
        "sequence": event.sequence,
    }
