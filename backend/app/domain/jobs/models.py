from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    owner: Mapped["User | None"] = relationship(back_populates="jobs")
    requirements: Mapped[list["JobRequirement"]] = relationship(back_populates="job", cascade="all,delete")
    transactions: Mapped[list["FinancialTransaction"]] = relationship(back_populates="job")


class JobRequirement(Base):
    __tablename__ = "job_requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    quantity_required: Mapped[int] = mapped_column(default=1)
    quantity_picked: Mapped[int] = mapped_column(default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped[Job] = relationship(back_populates="requirements")
    product: Mapped["Product"] = relationship(back_populates="requirements", overlaps="requirements")
