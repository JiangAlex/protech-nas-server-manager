"""Add metrics_snapshots table.

Revision ID: 004
Revises: 003
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "metrics_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("cpu_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("memory_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("disk_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("network_io", sa.Text(), nullable=False),
        sa.Column("temperature", sa.Text(), nullable=False),
        sa.Column("raw_json", sa.Text(), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_metrics_snapshots_device_id", "metrics_snapshots", ["device_id"])
    op.create_index("ix_metrics_snapshots_collected_at", "metrics_snapshots", ["collected_at"])


def downgrade() -> None:
    op.drop_index("ix_metrics_snapshots_collected_at", table_name="metrics_snapshots")
    op.drop_index("ix_metrics_snapshots_device_id", table_name="metrics_snapshots")
    op.drop_table("metrics_snapshots")
