from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=True, index=True)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"), nullable=True, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    customer: Mapped["Customer"] = relationship(back_populates="projects")
    venue: Mapped["Venue"] = relationship()
    jobs: Mapped[list["Job"]] = relationship(back_populates="project")
