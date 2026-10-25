import os
import tempfile
from pathlib import Path

import pytest

_test_dir = tempfile.TemporaryDirectory(prefix="agentguard-tests-")
os.environ["AG_DATABASE_URL"] = os.environ.get(
    "AG_TEST_DATABASE_URL", "sqlite:///" + (Path(_test_dir.name) / "test.db").as_posix()
)

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import login, passwords  # noqa: E402
from app.db import SessionLocal, engine, uid  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Tenant, TenantMember, User  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database():
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config("alembic.ini"), "head")
    yield
    engine.dispose()
    _test_dir.cleanup()


@pytest.fixture
def console():
    with SessionLocal() as db:
        tenant = Tenant(name="Test tenant")
        user = User(email=uid() + "@example.com", password_hash=passwords.hash("test-password-123"))
        db.add_all([tenant, user])
        db.flush()
        db.add(TenantMember(user_id=user.id, tenant_id=tenant.id, role="admin"))
        db.commit()
        _, cookie = login(db, user.email, "test-password-123", uid())
    with TestClient(app, headers={"Origin": "http://localhost:3000"}) as client:
        client.cookies.set("ag_session", cookie)
        yield client


@pytest.fixture
def project(console):
    response = console.post(
        "/v1/console/projects", json={"name": "Test", "provider": "Mock", "model": "mock-model"}
    )
    assert response.status_code == 201, response.text
    project = response.json()
    key = console.post(
        f"/v1/console/projects/{project['id']}/api-keys", json={"name": "test", "environment": "test"}
    ).json()
    return project, key


@pytest.fixture
def agent(project):
    with TestClient(app, headers={"Authorization": "Bearer " + project[1]["rawKey"]}) as client:
        yield client


def register(console, project_id, name="payment.refund"):
    response = console.put(
        f"/v1/console/projects/{project_id}/tools/{name}",
        json={
            "name": name,
            "input_schema": {
                "type": "object",
                "properties": {"amount": {"type": "number"}},
                "additionalProperties": True,
            },
        },
    )
    assert response.status_code == 200, response.text


def publish(console, project_id, effect="require_approval"):
    response = console.post(
        "/v1/policies",
        json={
            "projectId": project_id,
            "document": [{"id": "refund", "match": {"tool": "payment.refund"}, "effect": effect}],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
