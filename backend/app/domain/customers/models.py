from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Company(Base):
    """Company entity for B2B customers and suppliers."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Twenty CRM sync fields
    external_source: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    external_reference: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    external_origin: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)

    # Business classification
    is_customer: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_product_supplier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_rental_supplier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_crew_supplier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Notification preferences
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    preferred_language: Mapped[str | None] = mapped_column(String(10), nullable=True, default="en")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    persons: Mapped[list["Person"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="company")
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="company")
    supplied_products: Mapped[list["ProductSupplier"]] = relationship(
        "ProductSupplier", back_populates="supplier_company"
    )


class Person(Base):
    """Person entity for contacts and individual customers."""

    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(150), index=True)
    last_name: Mapped[str] = mapped_column(String(150), index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Foreign key to Company (nullable for B2C standalone persons)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Twenty CRM sync fields
    external_source: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    external_reference: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    external_origin: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)

    # Notification preferences
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    preferred_language: Mapped[str | None] = mapped_column(String(10), nullable=True, default="en")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    company: Mapped[Company | None] = relationship(back_populates="persons")
    crew_member: Mapped["CrewMember | None"] = relationship("CrewMember", back_populates="person", uselist=False)

    @property
    def full_name(self) -> str:
        """Return the person's full name."""
        return f"{self.first_name} {self.last_name}".strip()


class Customer(Base):
    """Legacy Customer model - kept for backward compatibility during migration.

    This model will be deprecated after the Company/Person migration is complete.
    """

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
    external_origin: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    twenty_person_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    is_customer: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_product_supplier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_rental_supplier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_crew_supplier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    preferred_language: Mapped[str | None] = mapped_column(String(10), nullable=True, default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="customer_legacy")
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="customer_legacy")
    supplied_products: Mapped[list["ProductSupplier"]] = relationship(
        "ProductSupplier", back_populates="supplier_legacy"
    )