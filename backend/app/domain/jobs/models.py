from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    location_in_venue: Mapped[str] = mapped_column(String(255), nullable=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    venue_name: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)
    sales_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    invoice_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    invoice_paid_at: Mapped[date] = mapped_column(Date, nullable=True)
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    productionplanner_project_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    external_source: Mapped[str] = mapped_column(String(80), nullable=True, index=True)
    external_reference: Mapped[str] = mapped_column(String(120), nullable=True, index=True)
    eventory_job_ids: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner: Mapped["User"] = relationship(back_populates="jobs")
    project: Mapped["Project"] = relationship(back_populates="jobs")
    customer: Mapped["Customer"] = relationship(back_populates="jobs")
    venue: Mapped["Venue"] = relationship(back_populates="jobs")
    requirements: Mapped[list["JobRequirement"]] = relationship(back_populates="job", cascade="all,delete")
    crew_requirements: Mapped[list["JobCrewRequirement"]] = relationship(
        back_populates="job", cascade="all,delete"
    )
    transactions: Mapped[list["FinancialTransaction"]] = relationship(back_populates="job")


class JobRequirement(Base):
    __tablename__ = "job_requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    quantity_required: Mapped[int] = mapped_column(default=1)
    quantity_picked: Mapped[int] = mapped_column(default=0)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    job: Mapped[Job] = relationship(back_populates="requirements")
    product: Mapped["Product"] = relationship(back_populates="requirements", overlaps="requirements")
