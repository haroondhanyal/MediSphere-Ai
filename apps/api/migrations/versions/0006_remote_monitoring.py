"""Create device and observation tables.

Revision ID: 0006_remote_monitoring
"""
from alembic import op
from app.database import Base
from app import models  # noqa: F401

revision = "0006_remote_monitoring"
down_revision = "0005_revenue_cycle"
branch_labels = None
depends_on = None


def upgrade():
    names = {"devices", "device_readings"}
    for table in Base.metadata.sorted_tables:
        if table.name in names:
            table.create(bind=op.get_bind(), checkfirst=True)


def downgrade():
    names = {"devices", "device_readings"}
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in names:
            table.drop(bind=op.get_bind(), checkfirst=True)
