import pytest
from sqlalchemy import func, select

from app import audit, replay
from app.db import Base, SessionLocal, engine
from app.models import ApiKey, Approval, AttackCase, GuardFinding, LLMRequest, Project, ReplayRun, ToolCall
from app.seed import seed_demo


def test_seed_is_repeatable_and_uses_real_flows(console, monkeypatch):
    email = console.get("/v1/console/auth/session").json()["email"]
    existing = console.post("/v1/console/projects", json={"name": "Keep me"}).json()["id"]
    original = audit.verify
    with monkeypatch.context() as patch:
        patch.setattr(audit, "verify", lambda *_: {"valid": False})
        with pytest.raises(ValueError, match="audit verification"):
            seed_demo(engine, email)
    with SessionLocal() as db:
        assert db.scalar(select(Project).where(Project.name == "Demo Seeder")) is None
        assert db.get(Project, existing).name == "Keep me"
    project_id, created = seed_demo(engine, email)
    assert created
    with SessionLocal() as db:
        counts = {
            table.name: db.scalar(select(func.count()).select_from(table))
            for table in Base.metadata.sorted_tables
        }
    assert seed_demo(engine, email) == (project_id, False)
    with SessionLocal() as db:
        assert counts == {
            table.name: db.scalar(select(func.count()).select_from(table))
            for table in Base.metadata.sorted_tables
        }
        assert db.get(Project, existing).name == "Keep me"
        requests = list(db.scalars(select(LLMRequest).where(LLMRequest.project_id == project_id)))
        assert len(requests) == 6 and all(r.status == "COMPLETED" for r in requests)
        assert "demo@example.com" not in str([r.capture for r in requests])
        assert {
            f.finding["type"]
            for f in db.scalars(select(GuardFinding).where(GuardFinding.project_id == project_id))
        } == {"PII_DETECTED", "SECRET_EXPOSURE", "SUSPICIOUS_INSTRUCTION"}
        assert {a.status for a in db.scalars(select(Approval).where(Approval.project_id == project_id))} == {
            "PENDING",
            "APPROVED",
            "REJECTED",
        }
        assert {c.status for c in db.scalars(select(ToolCall).where(ToolCall.project_id == project_id))} == {
            "EXECUTED",
            "DENIED",
            "APPROVAL_PENDING",
        }
        assert all(k.revoked_at for k in db.scalars(select(ApiKey).where(ApiKey.project_id == project_id)))
        assert (
            db.scalar(select(func.count()).select_from(AttackCase).where(AttackCase.project_id == project_id))
            == 6
        )
        assert original(db, project_id)["valid"]
        db.commit()
        assert replay.run_one(db)
        run = db.scalar(select(ReplayRun).where(ReplayRun.project_id == project_id))
        assert replay.run_view(db, run)["passed"] == 6
        assert original(db, project_id)["valid"]
    with pytest.raises(ValueError, match="administrator"):
        seed_demo(engine, "missing-seeder-user@example.invalid")
