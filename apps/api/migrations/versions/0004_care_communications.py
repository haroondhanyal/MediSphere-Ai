"""Create communications and virtual visit coordination tables.

Revision ID: 0004_care_communications
"""
from alembic import op
from app.database import Base
from app import models  # noqa: F401

revision = "0004_care_communications"
down_revision = "0003_clinical_orders"
branch_labels = None
depends_on = None


def upgrade():
    names = {"notifications", "chat_messages", "video_sessions"}
    for table in Base.metadata.sorted_tables:
        if table.name in names:
            table.create(bind=op.get_bind(), checkfirst=True)


def downgrade():
    names = {"notifications", "chat_messages", "video_sessions"}
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in names:
            table.drop(bind=op.get_bind(), checkfirst=True)
