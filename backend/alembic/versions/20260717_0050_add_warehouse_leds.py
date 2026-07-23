"""add warehouse LED controller tables

Revision ID: 20260717_0050
Revises: 20260717_0049
Create Date: 2026-07-17 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260717_0050"
down_revision = "20260717_0049"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "led_controllers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("controller_id", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("mac_address", sa.String(17), nullable=True, index=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("hostname", sa.String(255), nullable=True),
        sa.Column("firmware_version", sa.String(50), nullable=True),
        sa.Column("led_count", sa.Integer(), server_default="300"),
        sa.Column("topic_suffix", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), server_default="offline", index=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("wifi_rssi", sa.Integer(), nullable=True),
        sa.Column("uptime_seconds", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "led_controller_zones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "controller_id",
            sa.Integer(),
            sa.ForeignKey("led_controllers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "zone_id",
            sa.Integer(),
            sa.ForeignKey("zones.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("controller_id", "zone_id", name="uq_led_controller_zone"),
    )

    op.create_table(
        "led_bin_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "controller_id",
            sa.Integer(),
            sa.ForeignKey("led_controllers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "zone_id",
            sa.Integer(),
            sa.ForeignKey("zones.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("shelf_label", sa.String(50), nullable=True, index=True),
        sa.Column("bin_label", sa.String(50), nullable=False, index=True),
        sa.Column("pixel_start", sa.Integer(), server_default="0"),
        sa.Column("pixel_end", sa.Integer(), server_default="0"),
        sa.Column("default_color", sa.String(20), server_default="#FF6600"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("controller_id", "bin_label", name="uq_led_bin_mapping"),
    )


def downgrade():
    op.drop_table("led_bin_mappings")
    op.drop_table("led_controller_zones")
    op.drop_table("led_controllers")
