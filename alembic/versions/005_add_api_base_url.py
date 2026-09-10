"""Add api_base_url column to devices table.

Revision ID: 005
Revises: 004
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "devices",
        sa.Column(
            "api_base_url",
            sa.String(255),
            nullable=True,
            comment="Base URL for the device's own API (e.g. http://192.168.1.100:8080)",
        ),
    )


def downgrade() -> None:
    op.drop_column("devices", "api_base_url")
