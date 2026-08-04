from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_source: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    external_reference: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    is_customer: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_product_supplier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_rental_supplier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_crew_supplier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    jobs: Mapped[list["Job"]] = relationship(back_populates="customer")
    projects: Mapped[list["Project"]] = relationship(back_populates="customer")
    supplied_products: Mapped[list["ProductSupplier"]] = relationship(
        "ProductSupplier", back_populates="supplier"
    )