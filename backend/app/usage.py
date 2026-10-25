import math
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select

from .db import now, project_lock
from .errors import APIError
from .models import LLMRequest, ModelPricing, RateBucket


def rate_limit(db, key):
    project = project_lock(db, key.project_id)
    db.refresh(key)
    if not project.enabled or project.deleted_at or key.revoked_at:
        raise APIError(401, "AG_AUTH_401", "Project or API key is disabled.")
    minute = now().replace(second=0, microsecond=0)
    for key_id in ("", key.id):
        bucket = db.get(RateBucket, (project.id, key_id, minute))
        if not bucket:
            bucket = RateBucket(project_id=project.id, api_key_id=key_id, minute=minute, count=0)
            db.add(bucket)
        if bucket.count >= project.requests_per_minute:
            db.rollback()
            raise APIError(429, "AG_RATE_LIMIT_EXCEEDED", "Request rate limit exceeded.")
        bucket.count += 1
    db.commit()


def pricing(db, provider, model):
    return db.scalar(
        select(ModelPricing)
        .where(
            ModelPricing.provider == provider,
            ModelPricing.model == model,
            ModelPricing.effective_from <= now(),
        )
        .order_by(ModelPricing.effective_from.desc())
        .limit(1)
    )


def cost(price, input_tokens, output_tokens):
    if not price:
        return Decimal(0)
    return (
        Decimal(input_tokens) * price.input_price_per_million
        + Decimal(output_tokens) * price.output_price_per_million
    ) / Decimal(1_000_000)


def reserve(db, project, record, input_ceiling, max_output):
    project = project_lock(db, project.id)
    price = pricing(db, record.provider, record.model)
    record.pricing_configured = price is not None
    if project.budget_per_day is not None and not price:
        raise APIError(403, "AG_PRICING_REQUIRED", "Configure model pricing before using a daily budget.")
    tokens, spent = db.execute(
        select(
            func.coalesce(func.sum(LLMRequest.reserved_tokens), 0),
            func.coalesce(func.sum(LLMRequest.reserved_cost), 0),
        ).where(
            LLMRequest.project_id == project.id,
            LLMRequest.created_at >= now().replace(hour=0, minute=0, second=0, microsecond=0),
        )
    ).one()
    record.reserved_tokens = input_ceiling + max_output
    record.reserved_cost = cost(price, input_ceiling, max_output)
    if tokens + record.reserved_tokens > project.tokens_per_day:
        raise APIError(429, "AG_RATE_LIMIT_EXCEEDED", "Daily token quota exceeded.")
    if project.budget_per_day is not None and spent + record.reserved_cost > project.budget_per_day:
        raise APIError(403, "BUDGET_EXCEEDED", "Daily budget would be exceeded.")
    db.add(record)
    db.flush()
    return price


def usage_rows(
    db,
    project_id,
    provider=None,
    model=None,
    environment=None,
    feature=None,
    since=None,
    until=None,
    period=None,
):
    query = select(LLMRequest).where(LLMRequest.project_id == project_id)
    for column, value in [
        (LLMRequest.provider, provider),
        (LLMRequest.model, model),
        (LLMRequest.environment, environment),
        (LLMRequest.feature, feature),
    ]:
        if value:
            query = query.where(column == value)
    if since:
        query = query.where(LLMRequest.created_at >= since)
    if until:
        query = query.where(LLMRequest.created_at < until)
    groups = {}
    for row in db.scalars(query):
        label = (
            row.created_at.strftime("%Y-%m-%dT%H:00Z" if period == "hourly" else "%Y-%m-%d")
            if period
            else row.model
        )
        key = (label, row.provider, row.model, row.environment, row.feature)
        groups.setdefault(key, []).append(row)
    output = []
    for (label, provider_name, model_name, env, feature_name), rows in groups.items():
        latencies = sorted(r.latency_ms for r in rows)
        output.append(
            {
                "label": label,
                "provider": provider_name,
                "model": model_name,
                "environment": env,
                "feature": feature_name,
                "requests": len(rows),
                "cost": float(sum(r.estimated_cost for r in rows)),
                "pricingConfigured": all(r.pricing_configured for r in rows),
                "inputTokens": sum(r.input_tokens for r in rows),
                "outputTokens": sum(r.output_tokens for r in rows),
                "p95": latencies[max(0, math.ceil(0.95 * len(rows)) - 1)],
                "averageLatency": sum(latencies) / len(rows),
                "errors": 100 * sum(r.status == "FAILED" for r in rows) / len(rows),
            }
        )
    return output


def expire_reservations(db):
    # Crashed calls keep their conservative reservation; do not pretend no provider spend occurred.
    for row in db.scalars(
        select(LLMRequest).where(
            LLMRequest.status == "PENDING", LLMRequest.created_at < now() - timedelta(minutes=10)
        )
    ):
        row.status = "FAILED"
