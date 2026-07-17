from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TwentyConfig(Base):
    __tablename__ = "twenty_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    api_key: Mapped[str] = mapped_column(Text)
    base_url: Mapped[str] = mapped_column(String(500), default="https://api.twenty.com")
    workspace_id: Mapped[str] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class TwentySyncLog(Base):
    __tablename__ = "twenty_sync_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    direction: Mapped[str] = mapped_column(String(20), index=True)  # "outbound" or "inbound"
    entity_type: Mapped[str] = mapped_column(String(50), index=True)  # "customer", "job", "company", "person", "opportunity"
    entity_id: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    twenty_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    operation: Mapped[str] = mapped_column(String(20))  # "create", "update", "delete"
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # "pending", "success", "failed"
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    payload: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
