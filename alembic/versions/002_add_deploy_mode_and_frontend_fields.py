"""add deploy_mode and frontend fields

Revision ID: 002
Revises: 001
Create Date: 2026-08-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add deploy_mode to devices
    op.add_column(
        "devices",
        sa.Column("deploy_mode", sa.String(20), nullable=False, server_default="systemd"),
    )

    # Add frontend fields to firmware_versions
    op.add_column(
        "firmware_versions",
        sa.Column("frontend_artifact_path", sa.String(500), nullable=True),
    )
    op.add_column(
        "firmware_versions",
        sa.Column("frontend_checksum", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("firmware_versions", "frontend_checksum")
    op.drop_column("firmware_versions", "frontend_artifact_path")
    op.drop_column("devices", "deploy_mode")
