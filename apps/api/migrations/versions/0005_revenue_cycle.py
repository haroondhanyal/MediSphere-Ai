"""Create coverage, claims, authorization and billing tables.

Revision ID: 0005_revenue_cycle
"""
from alembic import op
from app.database import Base
from app import models  # noqa: F401

revision = "0005_revenue_cycle"
down_revision = "0004_care_communications"
branch_labels = None
depends_on = None


def upgrade():
    names = {"insurance_policies", "claims", "prior_authorizations", "invoices", "payments"}
    for table in Base.metadata.sorted_tables:
        if table.name in names:
            table.create(bind=op.get_bind(), checkfirst=True)


def downgrade():
    names = {"insurance_policies", "claims", "prior_authorizations", "invoices", "payments"}
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in names:
            table.drop(bind=op.get_bind(), checkfirst=True)
