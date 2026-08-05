"""initial tables

Revision ID: 001
Revises:
Create Date: 2026-08-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # device_types
    op.create_table(
        "device_types",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("update_method", sa.String(50), nullable=False, server_default="git_pull"),
        sa.Column("health_check_method", sa.String(50), nullable=False, server_default="http"),
        sa.Column("config", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # devices
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_type_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("current_version", sa.String(50), nullable=True),
        sa.Column("current_git_hash", sa.String(40), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("ssh_host", sa.String(255), nullable=True),
        sa.Column("ssh_port", sa.Integer(), nullable=False, server_default=sa.text("22")),
        sa.Column("ssh_user", sa.String(50), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_update_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("config", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.ForeignKeyConstraint(["device_type_id"], ["device_types.id"]),
    )

    # firmware_versions
    op.create_table(
        "firmware_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_type_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("git_hash", sa.String(40), nullable=True),
        sa.Column("git_hash_short", sa.String(8), nullable=True),
        sa.Column("version_display", sa.String(100), nullable=True),
        sa.Column("changelog", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("file_checksum", sa.String(64), nullable=True),
        sa.Column("git_repo_url", sa.String(500), nullable=True),
        sa.Column("git_branch", sa.String(100), nullable=True),
        sa.Column("is_latest", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_stable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["device_type_id"], ["device_types.id"]),
    )

    # update_logs
    op.create_table(
        "update_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("from_version", sa.String(50), nullable=True),
        sa.Column("to_version", sa.String(50), nullable=False),
        sa.Column("to_git_hash", sa.String(40), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("triggered_by", sa.String(20), nullable=False, server_default="admin"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
    )

    # notification_configs
    op.create_table(
        "notification_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("config", postgresql.JSONB(), nullable=True),
        sa.Column(
            "notify_on_update", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "notify_on_failure", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "notify_on_offline", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("platform"),
    )


def downgrade() -> None:
    op.drop_table("notification_configs")
    op.drop_table("update_logs")
    op.drop_table("firmware_versions")
    op.drop_table("devices")
    op.drop_table("device_types")
