import hashlib
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


def now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def uid(prefix: str = "") -> str:
    return prefix + uuid.uuid4().hex


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


@event.listens_for(engine, "connect")
def sqlite_foreign_keys(connection, _):
    if engine.dialect.name == "sqlite":
        connection.execute("PRAGMA foreign_keys=ON")


def get_db():
    with SessionLocal() as db:
        yield db


def project_lock(db: Session, project_id: str):
    from .errors import APIError
    from .models import Project

    # Serialize audit appends, policy publication and quota reservations on the project row.
    project = db.scalar(
        select(Project)
        .where(Project.id == project_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if project is None:
        raise APIError(404, "AG_NOT_FOUND", "Project not found.")
    return project
