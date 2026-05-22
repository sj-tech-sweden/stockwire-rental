"""add product metadata and advanced device/location fields

Revision ID: 20260520_0006
Revises: 20260520_0005
Create Date: 2026-05-20 18:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260520_0006"
down_revision = "20260520_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("brand", sa.String(length=120), nullable=True))
    op.add_column("products", sa.Column("manufacturer", sa.String(length=120), nullable=True))
    op.add_column(
        "products",
        sa.Column("product_type", sa.String(length=50), nullable=False, server_default="equipment"),
    )
    op.add_column("products", sa.Column("weight_kg", sa.Numeric(10, 3), nullable=True))
    op.add_column("products", sa.Column("height_cm", sa.Numeric(10, 2), nullable=True))
    op.add_column("products", sa.Column("width_cm", sa.Numeric(10, 2), nullable=True))
    op.add_column("products", sa.Column("depth_cm", sa.Numeric(10, 2), nullable=True))
    op.add_column("products", sa.Column("maintenance_interval_days", sa.Integer(), nullable=True))
    op.add_column("products", sa.Column("power_consumption_watts", sa.Numeric(10, 2), nullable=True))

    op.create_index("ix_products_brand", "products", ["brand"], unique=False)
    op.create_index("ix_products_manufacturer", "products", ["manufacturer"], unique=False)
    op.create_index("ix_products_product_type", "products", ["product_type"], unique=False)

    op.add_column("devices", sa.Column("barcode", sa.String(length=255), nullable=True))
    op.add_column("devices", sa.Column("qr_code", sa.String(length=255), nullable=True))
    op.add_column("devices", sa.Column("rfid", sa.String(length=255), nullable=True))
    op.add_column("devices", sa.Column("location_zone_id", sa.Integer(), nullable=True))
    op.add_column("devices", sa.Column("condition", sa.String(length=50), nullable=False, server_default="good"))
    op.add_column("devices", sa.Column("purchase_date", sa.Date(), nullable=True))
    op.add_column("devices", sa.Column("warranty_end_date", sa.Date(), nullable=True))
    op.add_column("devices", sa.Column("retire_date", sa.Date(), nullable=True))
    op.add_column("devices", sa.Column("usage_hours", sa.Numeric(10, 2), nullable=True))

    op.create_index("ix_devices_barcode", "devices", ["barcode"], unique=False)
    op.create_index("ix_devices_qr_code", "devices", ["qr_code"], unique=False)
    op.create_index("ix_devices_rfid", "devices", ["rfid"], unique=False)
    op.create_index("ix_devices_location_zone_id", "devices", ["location_zone_id"], unique=False)
    op.create_index("ix_devices_condition", "devices", ["condition"], unique=False)
    op.create_foreign_key(
        "fk_devices_location_zone_id_zones",
        "devices",
        "zones",
        ["location_zone_id"],
        ["id"],
    )

    op.add_column("zones", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("zones", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))


def downgrade() -> None:
    op.drop_column("zones", "is_active")
    op.drop_column("zones", "sort_order")

    op.drop_constraint("fk_devices_location_zone_id_zones", "devices", type_="foreignkey")
    op.drop_index("ix_devices_condition", table_name="devices")
    op.drop_index("ix_devices_location_zone_id", table_name="devices")
    op.drop_index("ix_devices_rfid", table_name="devices")
    op.drop_index("ix_devices_qr_code", table_name="devices")
    op.drop_index("ix_devices_barcode", table_name="devices")

    op.drop_column("devices", "usage_hours")
    op.drop_column("devices", "retire_date")
    op.drop_column("devices", "warranty_end_date")
    op.drop_column("devices", "purchase_date")
    op.drop_column("devices", "condition")
    op.drop_column("devices", "location_zone_id")
    op.drop_column("devices", "rfid")
    op.drop_column("devices", "qr_code")
    op.drop_column("devices", "barcode")

    op.drop_index("ix_products_product_type", table_name="products")
    op.drop_index("ix_products_manufacturer", table_name="products")
    op.drop_index("ix_products_brand", table_name="products")

    op.drop_column("products", "power_consumption_watts")
    op.drop_column("products", "maintenance_interval_days")
    op.drop_column("products", "depth_cm")
    op.drop_column("products", "width_cm")
    op.drop_column("products", "height_cm")
    op.drop_column("products", "weight_kg")
    op.drop_column("products", "product_type")
    op.drop_column("products", "manufacturer")
    op.drop_column("products", "brand")
