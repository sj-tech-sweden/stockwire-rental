"""add route planner tables

Revision ID: 20260717_0047
Revises: 20260717_0046
Create Date: 2026-07-17 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260717_0047"
down_revision = "20260717_0046"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vehicles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("vehicle_type", sa.String(50), nullable=False),
        sa.Column("license_plate", sa.String(20), nullable=True),
        sa.Column("max_weight_kg", sa.Numeric(10, 2), nullable=True),
        sa.Column("max_volume_m3", sa.Numeric(10, 3), nullable=True),
        sa.Column("length_cm", sa.Numeric(10, 2), nullable=True),
        sa.Column("width_cm", sa.Numeric(10, 2), nullable=True),
        sa.Column("height_cm", sa.Numeric(10, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "delivery_routes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="planned", index=True),
        sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "route_stops",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("route_id", sa.Integer(), sa.ForeignKey("delivery_routes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("stop_order", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_route_stops_route_id", "route_stops", ["route_id"])
    op.create_index("ix_route_stops_job_id", "route_stops", ["job_id"])


def downgrade():
    op.drop_table("route_stops")
    op.drop_table("delivery_routes")
    op.drop_table("vehicles")
