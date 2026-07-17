"""add multi-vehicle route support

Revision ID: 20260717_0048
Revises: 20260717_0047
Create Date: 2026-07-17 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260717_0048"
down_revision = "20260717_0047"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("vehicles", sa.Column("can_pull_trailer", sa.Boolean(), server_default=sa.text("false")))
    op.add_column("vehicles", sa.Column("max_tow_weight_kg", sa.Numeric(10, 2), nullable=True))
    op.add_column("vehicles", sa.Column("interior_length_cm", sa.Numeric(10, 2), nullable=True))
    op.add_column("vehicles", sa.Column("interior_width_cm", sa.Numeric(10, 2), nullable=True))
    op.add_column("vehicles", sa.Column("interior_height_cm", sa.Numeric(10, 2), nullable=True))

    op.create_table(
        "route_vehicles",
        sa.Column("route_id", sa.Integer(), sa.ForeignKey("delivery_routes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("load_order", sa.Integer(), server_default=sa.text("0")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("route_id", "vehicle_id"),
    )
    op.create_index("ix_route_vehicles_route_id", "route_vehicles", ["route_id"])
    op.create_index("ix_route_vehicles_vehicle_id", "route_vehicles", ["vehicle_id"])

    op.drop_column("delivery_routes", "vehicle_id")


def downgrade():
    op.add_column("delivery_routes", sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), nullable=True))
    op.execute("""
        UPDATE delivery_routes dr SET vehicle_id = rv.vehicle_id
        FROM route_vehicles rv WHERE rv.route_id = dr.id AND rv.load_order = 0
    """)
    op.drop_table("route_vehicles")
    op.drop_column("vehicles", "interior_height_cm")
    op.drop_column("vehicles", "interior_width_cm")
    op.drop_column("vehicles", "interior_length_cm")
    op.drop_column("vehicles", "max_tow_weight_kg")
    op.drop_column("vehicles", "can_pull_trailer")
