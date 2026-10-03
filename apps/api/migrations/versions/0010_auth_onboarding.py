"""Add signup profile fields and expiring password reset tokens.

Revision ID: 0010_auth_onboarding
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_auth_onboarding"
down_revision = "0009_profiles"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    for column in (
        sa.Column("session_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("phone_e164", sa.String(length=20), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("region", sa.String(length=120), nullable=True),
        sa.Column("profile_image_data", sa.String(length=700000), nullable=True),
    ):
        if column.name not in columns:
            op.add_column("users", column)

    if "password_reset_tokens" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
        op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)
        op.create_index("ix_password_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"])


def downgrade():
    bind = op.get_bind()
    if "password_reset_tokens" in sa.inspect(bind).get_table_names():
        op.drop_index("ix_password_reset_tokens_expires_at", table_name="password_reset_tokens")
        op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
        op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
        op.drop_table("password_reset_tokens")
    columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    for column_name in ("profile_image_data", "region", "country_code", "phone_e164", "session_version"):
        if column_name in columns:
            op.drop_column("users", column_name)
