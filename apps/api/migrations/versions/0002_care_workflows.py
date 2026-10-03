"""Create patient, practitioner, appointment and encounter tables.

Revision ID: 0002_care_workflows
"""
from alembic import op
from app.database import Base
from app import models  # noqa: F401

revision = "0002_care_workflows"
down_revision = "0001_phase1_identity"
branch_labels = None
depends_on = None


def upgrade():
    names = {"patients", "practitioners", "appointments", "encounters"}
    for table in Base.metadata.sorted_tables:
        if table.name in names:
            table.create(bind=op.get_bind(), checkfirst=True)


def downgrade():
    names = {"patients", "practitioners", "appointments", "encounters"}
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in names:
            table.drop(bind=op.get_bind(), checkfirst=True)
