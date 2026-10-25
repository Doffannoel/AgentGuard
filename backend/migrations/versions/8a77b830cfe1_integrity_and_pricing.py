"""Enforce immutable policy versions and identify unpriced usage."""

import sqlalchemy as sa
from alembic import op

revision = "8a77b830cfe1"
down_revision = "3c13ba9ec899"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "llm_requests",
        sa.Column("pricing_configured", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION reject_policy_version_mutation() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'Policy versions are immutable'; END;
        $$ LANGUAGE plpgsql""")
        op.execute("""CREATE TRIGGER immutable_policy_versions BEFORE UPDATE OR DELETE ON policy_versions
        FOR EACH ROW EXECUTE FUNCTION reject_policy_version_mutation()""")
    else:
        for action in ("UPDATE", "DELETE"):
            op.execute(f"""CREATE TRIGGER immutable_policy_versions_{action.lower()}
            BEFORE {action} ON policy_versions BEGIN SELECT RAISE(ABORT, 'Policy versions are immutable'); END""")


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER immutable_policy_versions ON policy_versions")
        op.execute("DROP FUNCTION reject_policy_version_mutation()")
    else:
        for action in ("update", "delete"):
            op.execute(f"DROP TRIGGER immutable_policy_versions_{action}")
    op.drop_column("llm_requests", "pricing_configured")
