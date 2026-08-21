from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InventoryCategory(Base):
    __tablename__ = "inventory_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    parent: Mapped["InventoryCategory | None"] = relationship(
        "InventoryCategory", remote_side="InventoryCategory.id", back_populates="children"
    )
    children: Mapped[list["InventoryCategory"]] = relationship(
        "InventoryCategory", back_populates="parent", cascade="all, delete-orphan"
    )
    products: Mapped[list["Product"]] = relationship(back_populates="category_node")
    translations: Mapped[list["CategoryTranslation"]] = relationship(
        "CategoryTranslation", back_populates="category", cascade="all, delete-orphan"
    )


class CategoryTranslation(Base):
    __tablename__ = "category_translations"
    __table_args__ = (UniqueConstraint("category_id", "locale", name="uq_category_locale"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("inventory_categories.id", ondelete="CASCADE"), nullable=False, index=True)
    locale: Mapped[str] = mapped_column(String(5), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    category: Mapped["InventoryCategory"] = relationship(back_populates="translations")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[str] = mapped_column(String(100), default="general")
    category_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    manufacturer: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    product_type: Mapped[str] = mapped_column(String(50), default="equipment", index=True)
    is_rental_product: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    rental_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    external_source: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    external_reference: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    eventory_available_qty: Mapped[int] = mapped_column(Integer, default=0)
    eventory_packlists_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    width_cm: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    depth_cm: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    maintenance_interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    power_consumption_watts: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    daily_rate: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    replace_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    min_stock_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_order_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    crew_skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    crew_certifications: Mapped[str | None] = mapped_column(Text, nullable=True)
    crew_rate_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    crew_hourly_rate: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    category_node: Mapped["InventoryCategory | None"] = relationship(back_populates="products")
    devices: Mapped[list["Device"]] = relationship(back_populates="product")
    requirements: Mapped[list["JobRequirement"]] = relationship(
        back_populates="product", overlaps="product"
    )
    supplier_links: Mapped[list["ProductSupplier"]] = relationship(
        "ProductSupplier", back_populates="product", cascade="all, delete-orphan"
    )
    accessories_as_parent: Mapped[list["ProductAccessory"]] = relationship(
        "ProductAccessory",
        foreign_keys="ProductAccessory.parent_product_id",
        back_populates="parent_product",
        cascade="all, delete-orphan",
    )
    accessories_as_child: Mapped[list["ProductAccessory"]] = relationship(
        "ProductAccessory",
        foreign_keys="ProductAccessory.accessory_product_id",
        back_populates="accessory_product",
        cascade="all, delete-orphan",
    )
    components_as_parent: Mapped[list["ProductComponent"]] = relationship(
        "ProductComponent",
        foreign_keys="ProductComponent.parent_product_id",
        back_populates="parent_product",
        cascade="all, delete-orphan",
    )
    components_as_child: Mapped[list["ProductComponent"]] = relationship(
        "ProductComponent",
        foreign_keys="ProductComponent.component_product_id",
        back_populates="component_product",
        cascade="all, delete-orphan",
    )
    required_certifications: Mapped[list["EquipmentRequiredCertification"]] = relationship(
        "EquipmentRequiredCertification",
        back_populates="product",
        cascade="all, delete-orphan",
    )


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    asset_tag: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    serial_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source_serial_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    qr_code: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    rfid: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    location_zone_id: Mapped[int | None] = mapped_column(ForeignKey("zones.id", ondelete="SET NULL"), nullable=True, index=True)
    case_device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_component_device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="available", index=True)
    condition: Mapped[str] = mapped_column(String(50), default="good", index=True)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    purchased_from: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    sold_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    finance_upto: Mapped[str | None] = mapped_column(String(255), nullable=True)
    finance_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    finance_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pre_prep: Mapped[str | None] = mapped_column(String(255), nullable=True)
    warranty_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    retire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    usage_hours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    product: Mapped[Product] = relationship(back_populates="devices")
    supplier: Mapped["Customer | None"] = relationship("Customer", foreign_keys=[supplier_id])
    location_zone: Mapped["Zone | None"] = relationship(back_populates="devices")
    case_device: Mapped["Device | None"] = relationship(
        "Device",
        remote_side="Device.id",
        back_populates="contained_devices",
        foreign_keys=[case_device_id],
    )
    contained_devices: Mapped[list["Device"]] = relationship(
        "Device",
        back_populates="case_device",
        foreign_keys="Device.case_device_id",
    )
    parent_component_device: Mapped["Device | None"] = relationship(
        "Device",
        remote_side="Device.id",
        back_populates="component_devices",
        foreign_keys=[parent_component_device_id],
    )
    component_devices: Mapped[list["Device"]] = relationship(
        "Device",
        back_populates="parent_component_device",
        foreign_keys="Device.parent_component_device_id",
    )
    maintenance_records: Mapped[list["DeviceMaintenance"]] = relationship(
        "DeviceMaintenance", back_populates="device", cascade="all, delete-orphan"
    )
    defect_reports: Mapped[list["DefectReport"]] = relationship(
        "DefectReport", back_populates="device", cascade="all, delete-orphan"
    )


class ProductAccessory(Base):
    __tablename__ = "product_accessories"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    accessory_product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    is_scannable: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    parent_product: Mapped[Product] = relationship(
        "Product",
        foreign_keys=[parent_product_id],
        back_populates="accessories_as_parent",
    )
    accessory_product: Mapped[Product] = relationship(
        "Product",
        foreign_keys=[accessory_product_id],
        back_populates="accessories_as_child",
    )


class ProductComponent(Base):
    __tablename__ = "product_components"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    component_product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    is_scannable: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    parent_product: Mapped[Product] = relationship(
        "Product",
        foreign_keys=[parent_product_id],
        back_populates="components_as_parent",
    )
    component_product: Mapped[Product] = relationship(
        "Product",
        foreign_keys=[component_product_id],
        back_populates="components_as_child",
    )


class ProductSupplier(Base):
    __tablename__ = "product_suppliers"
    __table_args__ = (UniqueConstraint("product_id", "supplier_id", name="uq_product_supplier"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    supplier_company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_cost: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    product: Mapped[Product] = relationship("Product", back_populates="supplier_links")
    supplier_legacy: Mapped["Customer"] = relationship("Customer", back_populates="supplied_products")
    supplier_company: Mapped["Company | None"] = relationship("Company", back_populates="supplied_products")


class DeviceMaintenanceSchedule(Base):
    __tablename__ = "device_maintenance_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    maintenance_type: Mapped[str] = mapped_column(String(80), default="inspection")
    interval_mode: Mapped[str] = mapped_column(String(20), default="calendar")
    interval_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    maintenance_records: Mapped[list["DeviceMaintenance"]] = relationship(
        "DeviceMaintenance",
        back_populates="schedule",
    )


class DeviceMaintenance(Base):
    __tablename__ = "device_maintenance"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    schedule_id: Mapped[int | None] = mapped_column(ForeignKey("device_maintenance_schedules.id", ondelete="SET NULL"), nullable=True, index=True)
    maintenance_type: Mapped[str] = mapped_column(String(80), default="scheduled")
    status: Mapped[str] = mapped_column(String(40), default="scheduled", index=True)
    interval_mode: Mapped[str] = mapped_column(String(20), default="calendar")
    interval_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    due_usage_hours: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    completed_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    device: Mapped[Device] = relationship(back_populates="maintenance_records")
    schedule: Mapped[DeviceMaintenanceSchedule | None] = relationship(back_populates="maintenance_records")
    defect_reports: Mapped[list["DefectReport"]] = relationship(
        "DefectReport",
        back_populates="maintenance",
    )
    comments: Mapped[list["MaintenanceComment"]] = relationship(
        "MaintenanceComment",
        back_populates="maintenance",
        cascade="all, delete-orphan",
    )


class MaintenanceComment(Base):
    __tablename__ = "maintenance_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    maintenance_id: Mapped[int] = mapped_column(ForeignKey("device_maintenance.id", ondelete="CASCADE"), index=True)
    comment: Mapped[str] = mapped_column(Text)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    maintenance: Mapped[DeviceMaintenance] = relationship(back_populates="comments")


class DefectReport(Base):
    __tablename__ = "defect_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    maintenance_id: Mapped[int | None] = mapped_column(
        ForeignKey("device_maintenance.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    severity: Mapped[str] = mapped_column(String(20), default="medium", index=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    device: Mapped[Device] = relationship(back_populates="defect_reports")
    maintenance: Mapped[DeviceMaintenance | None] = relationship(back_populates="defect_reports")
    comments: Mapped[list["DefectComment"]] = relationship(
        "DefectComment",
        back_populates="defect_report",
        cascade="all, delete-orphan",
    )


class DefectComment(Base):
    __tablename__ = "defect_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    defect_report_id: Mapped[int] = mapped_column(ForeignKey("defect_reports.id", ondelete="CASCADE"), index=True)
    comment: Mapped[str] = mapped_column(Text)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    defect_report: Mapped[DefectReport] = relationship(back_populates="comments")


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    zone_type: Mapped[str] = mapped_column(String(50), default="rack")
    barcode: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    qr_code: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    rfid: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("zones.id", ondelete="SET NULL"), nullable=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    pos_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pos_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pos_z: Mapped[int | None] = mapped_column(Integer, nullable=True)
    map_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    map_depth: Mapped[int | None] = mapped_column(Integer, nullable=True)
    map_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rotation: Mapped[int] = mapped_column(Integer, default=0)

    parent: Mapped["Zone | None"] = relationship("Zone", remote_side="Zone.id", back_populates="children")
    children: Mapped[list["Zone"]] = relationship("Zone", back_populates="parent")
    devices: Mapped[list["Device"]] = relationship(back_populates="location_zone")


class InventoryAuditLog(Base):
    __tablename__ = "inventory_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(40), default="scan", index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    message: Mapped[str] = mapped_column(String(500))
    scan_code: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("zones.id", ondelete="SET NULL"), nullable=True, index=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
