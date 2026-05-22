"""add inventory audit logs table

Revision ID: 20260520_0010
Revises: 20260520_0009
Create Date: 2026-05-20 14:50:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260520_0010"
down_revision = "20260520_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False, server_default="scan"),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("scan_code", sa.String(length=255), nullable=True),
        sa.Column("device_id", sa.Integer(), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("zone_id", sa.Integer(), nullable=True),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="SET NULL"),
    )

    op.create_index("ix_inventory_audit_logs_created_at", "inventory_audit_logs", ["created_at"])
    op.create_index("ix_inventory_audit_logs_user_id", "inventory_audit_logs", ["user_id"])
    op.create_index("ix_inventory_audit_logs_source", "inventory_audit_logs", ["source"])
    op.create_index("ix_inventory_audit_logs_action", "inventory_audit_logs", ["action"])
    op.create_index("ix_inventory_audit_logs_success", "inventory_audit_logs", ["success"])
    op.create_index("ix_inventory_audit_logs_scan_code", "inventory_audit_logs", ["scan_code"])
    op.create_index("ix_inventory_audit_logs_device_id", "inventory_audit_logs", ["device_id"])
    op.create_index("ix_inventory_audit_logs_product_id", "inventory_audit_logs", ["product_id"])
    op.create_index("ix_inventory_audit_logs_zone_id", "inventory_audit_logs", ["zone_id"])
    op.create_index("ix_inventory_audit_logs_job_id", "inventory_audit_logs", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_inventory_audit_logs_job_id", table_name="inventory_audit_logs")
    op.drop_index("ix_inventory_audit_logs_zone_id", table_name="inventory_audit_logs")
    op.drop_index("ix_inventory_audit_logs_product_id", table_name="inventory_audit_logs")
    op.drop_index("ix_inventory_audit_logs_device_id", table_name="inventory_audit_logs")
    op.drop_index("ix_inventory_audit_logs_scan_code", table_name="inventory_audit_logs")
    op.drop_index("ix_inventory_audit_logs_success", table_name="inventory_audit_logs")
    op.drop_index("ix_inventory_audit_logs_action", table_name="inventory_audit_logs")
    op.drop_index("ix_inventory_audit_logs_source", table_name="inventory_audit_logs")
    op.drop_index("ix_inventory_audit_logs_user_id", table_name="inventory_audit_logs")
    op.drop_index("ix_inventory_audit_logs_created_at", table_name="inventory_audit_logs")
    op.drop_table("inventory_audit_logs")
