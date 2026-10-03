"""Add per-device credentials for remote reading ingestion.

Revision ID: 0008_device_ingest_tokens
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_device_ingest_tokens"
down_revision = "0007_monitoring_alerts"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("devices")}
    if "ingest_token_hash" not in columns:
        op.add_column("devices", sa.Column("ingest_token_hash", sa.String(length=64), nullable=True))
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("devices")}
    if "ix_devices_ingest_token_hash" not in indexes:
        op.create_index("ix_devices_ingest_token_hash", "devices", ["ingest_token_hash"], unique=True)


def downgrade():
    op.drop_index("ix_devices_ingest_token_hash", table_name="devices")
    op.drop_column("devices", "ingest_token_hash")
