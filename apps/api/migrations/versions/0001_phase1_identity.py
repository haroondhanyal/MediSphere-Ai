"""Create Phase 1 identity, tenant and RBAC tables.

Revision ID: 0001_phase1_identity
"""
from alembic import op
from app.database import Base
from app import models  # noqa: F401

revision = "0001_phase1_identity"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    names = {"organizations", "organization_settings", "organization_subscriptions", "users", "roles", "permissions", "role_permissions", "organization_memberships", "audit_logs"}
    for table in Base.metadata.sorted_tables:
        if table.name in names:
            table.create(bind=op.get_bind(), checkfirst=True)


def downgrade():
    names = {"organizations", "organization_settings", "organization_subscriptions", "users", "roles", "permissions", "role_permissions", "organization_memberships", "audit_logs"}
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in names:
            table.drop(bind=op.get_bind(), checkfirst=True)
