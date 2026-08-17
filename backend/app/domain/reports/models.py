from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Letterhead(Base):
    __tablename__ = "letterheads"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    asset_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset_files.id", ondelete="SET NULL"), nullable=True, index=True
    )
    page_count: Mapped[int] = mapped_column(Integer, default=1)
    margin_top_mm: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("20.0"))
    margin_bottom_mm: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("20.0"))
    margin_left_mm: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("20.0"))
    margin_right_mm: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("20.0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    asset_file: Mapped["AssetFile | None"] = relationship()
    templates: Mapped[list["ReportTemplate"]] = relationship(back_populates="letterhead")


class ReportTemplate(Base):
    __tablename__ = "report_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    category: Mapped[str] = mapped_column(String(50), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    letterhead_id: Mapped[int | None] = mapped_column(
        ForeignKey("letterheads.id", ondelete="SET NULL"), nullable=True, index=True
    )
    body_json: Mapped[str] = mapped_column(Text, default="{}")
    translations_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_source_type: Mapped[str] = mapped_column(String(50), default="job")
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    letterhead: Mapped[Letterhead | None] = relationship(back_populates="templates")
    generation_logs: Mapped[list["GeneratedReportLog"]] = relationship(back_populates="template")


class GeneratedReportLog(Base):
    __tablename__ = "generated_report_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("report_templates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    asset_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset_files.id", ondelete="SET NULL"), nullable=True, index=True
    )
    generated_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    format: Mapped[str] = mapped_column(String(10), default="pdf")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    template: Mapped[ReportTemplate | None] = relationship(back_populates="generation_logs")
    asset_file: Mapped["AssetFile | None"] = relationship()
