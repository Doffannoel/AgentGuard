import hashlib
import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db, now
from .errors import APIError
from .models import ApiKey, ConsoleSession, LoginAttempt, Project, TenantMember, User

passwords = PasswordHasher()
DUMMY_HASH = passwords.hash(secrets.token_urlsafe(32))


def token_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def login(db: Session, email: str, password: str, ip: str):
    key = token_hash(ip)
    insert = pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
    db.execute(insert(LoginAttempt).values(key=key, count=0, window=now()).on_conflict_do_nothing())
    bucket = db.scalars(select(LoginAttempt).where(LoginAttempt.key == key).with_for_update()).one()
    if bucket.window < now() - timedelta(minutes=1):
        bucket.count, bucket.window = 0, now()
    bucket.count += 1
    db.commit()
    if bucket.count > 10:
        raise APIError(429, "AG_RATE_LIMIT_EXCEEDED", "Too many login attempts.")
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    try:
        valid = passwords.verify(user.password_hash if user else DUMMY_HASH, password)
    except VerificationError:
        valid = False
    if not user or not valid:
        raise APIError(401, "AG_AUTH_401", "Invalid email or password.")
    raw = secrets.token_urlsafe(48)
    db.add(
        ConsoleSession(
            user_id=user.id,
            token_hash=token_hash(raw),
            expires_at=now() + timedelta(hours=settings.session_hours),
        )
    )
    db.commit()
    return user, raw


def console_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("ag_session", "")
    session = db.scalar(
        select(ConsoleSession).where(
            ConsoleSession.token_hash == token_hash(token), ConsoleSession.expires_at > now()
        )
    )
    if not session:
        raise APIError(401, "AG_AUTH_401", "Console sign-in required.")
    user = db.get(User, session.user_id)
    if not user:
        raise APIError(401, "AG_AUTH_401", "Console sign-in required.")
    return user


def access_project(db: Session, user: User, project_id: str, admin: bool = False) -> Project:
    project = db.get(Project, project_id)
    member = db.get(TenantMember, (user.id, project.tenant_id)) if project else None
    if not project or project.deleted_at or not member:
        raise APIError(404, "AG_NOT_FOUND", "Project not found.")
    if admin and member.role != "admin":
        raise APIError(403, "AG_POLICY_403", "Administrator access required.")
    return project


def agent_key(request: Request, db: Session = Depends(get_db)) -> ApiKey:
    scheme, _, raw = request.headers.get("authorization", "").partition(" ")
    key = (
        db.scalar(select(ApiKey).where(ApiKey.secret_hash == token_hash(raw), ApiKey.revoked_at.is_(None)))
        if scheme.lower() == "bearer"
        else None
    )
    project = db.get(Project, key.project_id) if key else None
    if not key or not project or not project.enabled or project.deleted_at:
        raise APIError(401, "AG_AUTH_401", "Invalid, revoked or disabled project API key.")
    key.last_used_at = now()
    db.commit()
    return key


def create_key(db: Session, project_id: str, name: str, environment: str):
    from .audit import append_event

    prefix = f"ag_{environment}_{secrets.token_hex(5)}"
    raw = f"{prefix}_{secrets.token_urlsafe(32)}"
    record = ApiKey(
        project_id=project_id, name=name, environment=environment, prefix=prefix, secret_hash=token_hash(raw)
    )
    db.add(record)
    db.flush()
    append_event(db, project_id, "API_KEY_CREATED", {"key_id": record.id, "prefix": prefix})
    db.commit()
    return {"record": key_view(record), "rawKey": raw}


def key_view(key: ApiKey):
    return {
        "id": key.id,
        "name": key.name,
        "prefix": key.prefix,
        "environment": key.environment,
        "createdAt": key.created_at.isoformat(),
        "lastUsedAt": key.last_used_at.isoformat() if key.last_used_at else "Never",
        "revokedAt": key.revoked_at.isoformat() if key.revoked_at else None,
    }
