import json
import operator
import re
import time

from sqlalchemy import select

from .db import project_lock, uid
from .errors import APIError
from .models import Policy, PolicyVersion

OPS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "gt": operator.gt,
    "gte": operator.ge,
    "lt": operator.lt,
    "lte": operator.le,
    "in": lambda a, b: a in b,
}
PRIORITY = {"ALLOW": 0, "REQUIRE_APPROVAL": 1, "DENY": 2}


def validate_document(document):
    if isinstance(document, list):
        document = {"version": 1, "defaults": {"tool_action": "deny"}, "rules": document}
    if (
        not isinstance(document, dict)
        or set(document) - {"version", "defaults", "rules"}
        or document.get("version") != 1
    ):
        raise APIError(422, "AG_INVALID_POLICY", "Expected policy format version 1.")
    if document.get("defaults", {"tool_action": "deny"}) != {"tool_action": "deny"}:
        raise APIError(422, "AG_INVALID_POLICY", "Tool actions must default to deny.")
    rules = document.get("rules")
    if not isinstance(rules, list) or len(rules) > 1000:
        raise APIError(422, "AG_INVALID_POLICY", "Policy rules must be an array of at most 1000 rules.")
    ids = set()
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) - {"id", "match", "effect", "enabled", "description"}:
            raise APIError(422, "AG_INVALID_POLICY", "Unknown policy rule fields.")
        rid = rule.get("id")
        match = rule.get("match", {})
        if (
            not isinstance(rid, str)
            or not 1 <= len(rid) <= 120
            or rid in ids
            or rule.get("effect") not in ("allow", "deny", "require_approval")
        ):
            raise APIError(422, "AG_INVALID_POLICY", "Rules require unique IDs and a valid effect.")
        ids.add(rid)
        if not isinstance(rule.get("enabled", True), bool):
            raise APIError(422, "AG_INVALID_POLICY", "enabled must be boolean.")
        if not isinstance(match, dict) or set(match) - {"tool", "conditions", "action"}:
            raise APIError(422, "AG_INVALID_POLICY", "Invalid rule match.")
        if not isinstance(match.get("tool", "*"), str) or match.get("action", "tool") not in ("tool", "llm"):
            raise APIError(422, "AG_INVALID_POLICY", "Invalid tool or action match.")
        conditions = match.get("conditions", {})
        if not isinstance(conditions, dict):
            raise APIError(422, "AG_INVALID_POLICY", "Conditions must be an object.")
        for field, comparisons in conditions.items():
            if (
                not re.fullmatch(r"[A-Za-z_][\w.]*", field)
                or not isinstance(comparisons, dict)
                or not comparisons
            ):
                raise APIError(422, "AG_INVALID_POLICY", "Invalid condition.")
            for op, value in comparisons.items():
                if (
                    op not in OPS
                    or (op == "in" and not isinstance(value, list))
                    or (
                        op in {"gt", "gte", "lt", "lte"}
                        and (isinstance(value, bool) or not isinstance(value, (int, float)))
                    )
                ):
                    raise APIError(422, "AG_INVALID_POLICY", "Unsupported comparison or operand.")
    return document


def simple_rule(data):
    conditions = {}
    if data.condition:
        match = re.fullmatch(r"\s*([A-Za-z_][\w.]*)\s*(>=|<=|==|!=|>|<)\s*(.+?)\s*", data.condition)
        if not match:
            raise APIError(422, "AG_INVALID_POLICY", "Use a comparison such as amount > 500000.")
        field, op, raw = match.groups()
        try:
            value = json.loads(raw)
        except ValueError:
            value = raw
        conditions[field] = {
            {">=": "gte", "<=": "lte", "==": "eq", "!=": "ne", ">": "gt", "<": "lt"}[op]: value
        }
    return {
        "id": uid("rule_"),
        "description": data.description,
        "match": {"tool": data.tool, "conditions": conditions},
        "effect": data.effect.lower(),
        "enabled": data.enabled,
    }


def active_policy(db, project_id):
    policy = db.scalar(select(Policy).where(Policy.project_id == project_id))
    return (
        db.scalar(
            select(PolicyVersion).where(
                PolicyVersion.policy_id == policy.id, PolicyVersion.version == policy.active_version
            )
        )
        if policy
        else None
    )


def publish(db, project_id, document, append=False):
    from .audit import append_event

    project_lock(db, project_id)
    policy = db.scalar(select(Policy).where(Policy.project_id == project_id))
    if not policy:
        policy = Policy(project_id=project_id, active_version=0)
        db.add(policy)
        db.flush()
    if append:
        current = active_policy(db, project_id)
        document = {
            "version": 1,
            "defaults": {"tool_action": "deny"},
            "rules": (current.document["rules"] if current else []) + [document],
        }
    document = validate_document(document)
    policy.active_version += 1
    version = PolicyVersion(policy_id=policy.id, version=policy.active_version, document=document)
    db.add(version)
    db.flush()
    append_event(db, project_id, "POLICY_PUBLISHED", {"policy_version": version.id})
    db.commit()
    return version


def evaluate(document, context, action="tool"):
    from .observability import policy_latency

    started = time.perf_counter()
    matches = []
    for rule in (document or {}).get("rules", []):
        match = rule["match"]
        if not rule.get("enabled", True) or match.get("action", "tool") != action:
            continue
        if match.get("tool", "*") not in ("*", context.get("tool", {}).get("name")):
            continue
        matched = True
        for field, comparisons in match.get("conditions", {}).items():
            value = (
                context
                if field.split(".")[0]
                in {"tenant", "project", "actor", "tool", "environment", "security", "arguments"}
                else context.get("arguments", {})
            )
            for part in field.split("."):
                value = value.get(part) if isinstance(value, dict) else None
            for op, expected in comparisons.items():
                try:
                    if (
                        value is None
                        or (
                            op in {"gt", "gte", "lt", "lte"}
                            and (isinstance(value, bool) or not isinstance(value, (int, float)))
                        )
                        or not OPS[op](value, expected)
                    ):
                        matched = False
                except (TypeError, ValueError):
                    matched = False
        if matched:
            matches.append(rule)
    winner = max(matches, key=lambda rule: PRIORITY[rule["effect"].upper()]) if matches else None
    policy_latency.observe(time.perf_counter() - started)
    return {
        "decision": winner["effect"].upper() if winner else ("ALLOW" if action == "llm" else "DENY"),
        "rule_id": winner["id"] if winner else None,
        "reason_code": "RULE_MATCHED" if winner else "DEFAULT_" + ("ALLOW" if action == "llm" else "DENY"),
    }


def rule_view(rule):
    return {
        "id": rule["id"],
        "description": rule.get("description", ""),
        "tool": rule["match"].get("tool", "*"),
        "condition": json.dumps(rule["match"].get("conditions", {})),
        "effect": rule["effect"].upper(),
        "enabled": rule.get("enabled", True),
    }
