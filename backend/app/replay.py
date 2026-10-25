import time

from sqlalchemy import select

from .audit import append_event
from .db import now, project_lock
from .models import AttackCase, PolicyVersion, Project, ReplayResult, ReplayRun
from .observability import replay_fail, replay_pass
from .policies import active_policy
from .schemas import ToolRequest
from .tools import inspect_tool


def enqueue(db, project_id):
    project_lock(db, project_id)
    version = active_policy(db, project_id)
    cases = list(db.scalars(select(AttackCase).where(AttackCase.project_id == project_id)))
    run = ReplayRun(
        project_id=project_id,
        policy_version_id=version.id if version else None,
        case_snapshot=[
            {"id": c.id, "input": c.input, "expected": c.expected_decision, "expected_tool": c.expected_tool}
            for c in cases
        ],
    )
    db.add(run)
    db.flush()
    append_event(db, project_id, "REPLAY_QUEUED", {"run_id": run.id, "policy_version": run.policy_version_id})
    db.commit()
    return {"id": run.id, "status": run.status}


def run_one(db):
    # One transaction owns a bounded deterministic suite; crash rolls it back to queued.
    run = db.scalar(
        select(ReplayRun)
        .where(ReplayRun.status == "queued")
        .order_by(ReplayRun.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if not run:
        return False
    run.status = "running"
    project = db.get(Project, run.project_id)
    version = db.get(PolicyVersion, run.policy_version_id) if run.policy_version_id else None
    for case in run.case_snapshot:
        started = time.perf_counter()
        error = None
        actual = "DENY"
        try:
            request = ToolRequest.model_validate(case["input"])
            actual = inspect_tool(db, project, request, "replay", version)[0]["decision"]
        except (ValueError, TypeError):
            error = "Invalid stored replay input"
        passed = not error and actual == case["expected"] and case["input"]["tool"] == case["expected_tool"]
        db.add(
            ReplayResult(
                run_id=run.id,
                attack_case_id=case["id"],
                expected=case["expected"],
                actual=actual,
                passed=passed,
                latency=round((time.perf_counter() - started) * 1000),
                error=error,
            )
        )
        (replay_pass if passed else replay_fail).inc()
    run.status, run.completed_at = "completed", now()
    append_event(
        db,
        project.id,
        "REPLAY_COMPLETED",
        {"run_id": run.id, "policy_version": run.policy_version_id, "cases": len(run.case_snapshot)},
    )
    db.commit()
    return True


def run_view(db, run):
    results = list(db.scalars(select(ReplayResult).where(ReplayResult.run_id == run.id)))
    return {
        "id": run.id,
        "status": run.status,
        "policyVersion": run.policy_version_id,
        "total": len(run.case_snapshot),
        "completed": len(results),
        "passed": sum(r.passed for r in results),
        "failed": sum(not r.passed for r in results),
        "error": run.error,
        "results": [
            {
                "caseId": r.attack_case_id,
                "expected": r.expected,
                "actual": r.actual,
                "passed": r.passed,
                "latency": r.latency,
                "error": r.error,
            }
            for r in results
        ],
    }


def case_view(db, case):
    result = db.scalar(
        select(ReplayResult)
        .join(ReplayRun)
        .where(ReplayResult.attack_case_id == case.id, ReplayRun.status == "completed")
        .order_by(ReplayRun.completed_at.desc())
        .limit(1)
    )
    return {
        "id": case.id,
        "suite": case.category,
        "attack": case.name,
        "input": str(case.input),
        "expectedTool": case.expected_tool,
        "expectedDecision": case.expected_decision,
        "actualTool": case.input.get("tool", "") if result else "",
        "actualDecision": result.actual if result else None,
        "passed": result.passed if result else None,
    }
