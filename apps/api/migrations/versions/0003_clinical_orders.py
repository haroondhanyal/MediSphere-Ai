"""Create prescription, lab and radiology workflow tables.

Revision ID: 0003_clinical_orders
"""
from alembic import op
from app.database import Base
from app import models  # noqa: F401

revision = "0003_clinical_orders"
down_revision = "0002_care_workflows"
branch_labels = None
depends_on = None


def upgrade():
    names = {"prescriptions", "lab_orders", "radiology_orders"}
    for table in Base.metadata.sorted_tables:
        if table.name in names:
            table.create(bind=op.get_bind(), checkfirst=True)


def downgrade():
    names = {"prescriptions", "lab_orders", "radiology_orders"}
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in names:
            table.drop(bind=op.get_bind(), checkfirst=True)
