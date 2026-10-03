"""Add configurable remote-monitoring rules and alerts.

Revision ID: 0007_monitoring_alerts
"""
from alembic import op
from app.database import Base
from app import models  # noqa: F401

revision = "0007_monitoring_alerts"
down_revision = "0006_remote_monitoring"
branch_labels = None
depends_on = None


def upgrade():
    names = {"monitoring_rules", "monitoring_alerts"}
    for table in Base.metadata.sorted_tables:
        if table.name in names:
            table.create(bind=op.get_bind(), checkfirst=True)


def downgrade():
    names = {"monitoring_rules", "monitoring_alerts"}
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in names:
            table.drop(bind=op.get_bind(), checkfirst=True)
