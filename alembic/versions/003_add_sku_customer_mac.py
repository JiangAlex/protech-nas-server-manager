"""Add sku, customer_id, mac_address to devices table.

Revision ID: 003
Revises: 002
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("devices", sa.Column("sku", sa.String(50), nullable=True))
    op.add_column("devices", sa.Column("customer_id", sa.String(100), nullable=True))
    op.add_column("devices", sa.Column("mac_address", sa.String(17), nullable=True))
    op.create_index("ix_devices_sku", "devices", ["sku"])
    op.create_index("ix_devices_customer_id", "devices", ["customer_id"])
    op.create_unique_constraint("uq_devices_mac_address", "devices", ["mac_address"])


def downgrade() -> None:
    op.drop_constraint("uq_devices_mac_address", "devices", type_="unique")
    op.drop_index("ix_devices_customer_id", table_name="devices")
    op.drop_index("ix_devices_sku", table_name="devices")
    op.drop_column("devices", "mac_address")
    op.drop_column("devices", "customer_id")
    op.drop_column("devices", "sku")
