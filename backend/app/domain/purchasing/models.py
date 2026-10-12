"""Persistence models for the Best-purchase / supplier-comparison feature.

A :class:`PurchaseDraft` captures the recommended purchase basket produced by
the best-purchase engine so it can be reused as a purchase-order draft later.
"""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PurchaseDraft(Base):
    __tablename__ = "purchase_drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="draft")
    report_currency: Mapped[str] = mapped_column(String(10), default="EUR")
    total_base: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    supplier_count: Mapped[int] = mapped_column(default=0)
    meta_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    lines: Mapped[list["PurchaseDraftLine"]] = relationship(
        back_populates="draft", cascade="all, delete-orphan"
    )


class PurchaseDraftLine(Base):
    __tablename__ = "purchase_draft_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_drafts.id", ondelete="CASCADE"), index=True
    )
    vendor_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    vendor_product_id: Mapped[int | None] = mapped_column(
        ForeignKey("vendor_products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    requirement_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_requirements.id", ondelete="CASCADE"), nullable=True, index=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    vendor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    qty: Mapped[int] = mapped_column(default=1)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    converted_unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    line_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    is_selected_cheapest: Mapped[bool] = mapped_column(Boolean, default=True)

    draft: Mapped["PurchaseDraft"] = relationship(back_populates="lines")


class PurchaseOrder(Base):
    """A purchase order sent to a single supplier.

    A draft or a set of jobs can produce several POs (one per distinct supplier).
    Receiving a PO increments product stock and creates device records.
    """

    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    po_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    supplier_company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    supplier_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    order_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expected_delivery_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    report_currency: Mapped[str] = mapped_column(String(10), default="EUR")
    total_base: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    freight_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    freight_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    freight_base: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    meta_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    lines: Mapped[list["PurchaseOrderLine"]] = relationship(
        back_populates="po", cascade="all, delete-orphan"
    )

    @property
    def grand_total_base(self) -> Decimal | None:
        """Goods subtotal plus freight, in the report currency."""
        if self.total_base is None and self.freight_base is None:
            return None
        return (self.total_base or Decimal(0)) + (self.freight_base or Decimal(0))


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    po_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="CASCADE"), index=True
    )
    vendor_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    vendor_product_id: Mapped[int | None] = mapped_column(
        ForeignKey("vendor_products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    requirement_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_requirements.id", ondelete="SET NULL"), nullable=True, index=True
    )
    job_id: Mapped[int | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sku: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    qty: Mapped[int] = mapped_column(default=1)
    received_qty: Mapped[int] = mapped_column(default=0)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    converted_unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    line_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)
    is_restock: Mapped[bool] = mapped_column(Boolean, default=False)
    serials: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True
    )

    po: Mapped["PurchaseOrder"] = relationship(back_populates="lines")
