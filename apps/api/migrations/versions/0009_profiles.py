"""Add organization and practitioner profile details.

Revision ID: 0009_profiles
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_profiles"
down_revision = "0008_device_ingest_tokens"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    for table_name, column in (
        ("organizations", sa.Column("logo_url", sa.String(length=2048), nullable=True)),
        ("organizations", sa.Column("contact_phone", sa.String(length=40), nullable=True)),
        ("practitioners", sa.Column("phone", sa.String(length=40), nullable=True)),
        ("practitioners", sa.Column("role", sa.String(length=80), nullable=False, server_default="Practitioner")),
    ):
        columns = {item["name"] for item in sa.inspect(bind).get_columns(table_name)}
        if column.name not in columns:
            op.add_column(table_name, column)


def downgrade():
    op.drop_column("practitioners", "role")
    op.drop_column("practitioners", "phone")
    op.drop_column("organizations", "contact_phone")
    op.drop_column("organizations", "logo_url")
