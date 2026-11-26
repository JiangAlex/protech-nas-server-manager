"""Add device tokens and the device authentication audit log.

Revision ID: 006
Revises: 005
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("devices", sa.Column("token_hash", sa.String(64), nullable=True))
    op.add_column("devices", sa.Column("token_issued_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("devices", sa.Column("token_last_used_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("devices", sa.Column("token_last_ip", sa.String(45), nullable=True))
    op.create_table(
        "device_auth_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event", sa.String(40), nullable=False),
        sa.Column("endpoint", sa.String(40), nullable=True),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("mac", sa.String(17), nullable=True),
        sa.Column("user_agent", sa.String(200), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
    )
    op.create_index("ix_device_auth_events_device_id", "device_auth_events", ["device_id"])
    op.create_index("ix_device_auth_events_created_at", "device_auth_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_device_auth_events_created_at", table_name="device_auth_events")
    op.drop_index("ix_device_auth_events_device_id", table_name="device_auth_events")
    op.drop_table("device_auth_events")
    op.drop_column("devices", "token_last_ip")
    op.drop_column("devices", "token_last_used_at")
    op.drop_column("devices", "token_issued_at")
    op.drop_column("devices", "token_hash")
