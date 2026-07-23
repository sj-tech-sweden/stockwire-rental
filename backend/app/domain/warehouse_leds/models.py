from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LEDController(Base):
    __tablename__ = "led_controllers"

    id: Mapped[int] = mapped_column(primary_key=True)
    controller_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=True)
    mac_address: Mapped[str] = mapped_column(String(17), nullable=True, index=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    hostname: Mapped[str] = mapped_column(String(255), nullable=True)
    firmware_version: Mapped[str] = mapped_column(String(50), nullable=True)
    led_count: Mapped[int] = mapped_column(Integer, default=300)
    topic_suffix: Mapped[str] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="offline", index=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    wifi_rssi: Mapped[int] = mapped_column(Integer, nullable=True)
    uptime_seconds: Mapped[int] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    zone_assignments: Mapped[list["LEDControllerZone"]] = relationship(
        back_populates="controller", cascade="all, delete-orphan"
    )
    bin_mappings: Mapped[list["LEDBinMapping"]] = relationship(
        back_populates="controller", cascade="all, delete-orphan"
    )


class LEDControllerZone(Base):
    __tablename__ = "led_controller_zones"
    __table_args__ = (
        UniqueConstraint("controller_id", "zone_id", name="uq_led_controller_zone"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    controller_id: Mapped[int] = mapped_column(
        ForeignKey("led_controllers.id", ondelete="CASCADE"), index=True
    )
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    controller: Mapped[LEDController] = relationship(back_populates="zone_assignments")


class LEDBinMapping(Base):
    __tablename__ = "led_bin_mappings"
    __table_args__ = (
        UniqueConstraint("controller_id", "bin_label", name="uq_led_bin_mapping"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    controller_id: Mapped[int] = mapped_column(
        ForeignKey("led_controllers.id", ondelete="CASCADE"), index=True
    )
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id", ondelete="CASCADE"), index=True)
    shelf_label: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    bin_label: Mapped[str] = mapped_column(String(50), index=True)
    pixel_start: Mapped[int] = mapped_column(Integer, default=0)
    pixel_end: Mapped[int] = mapped_column(Integer, default=0)
    default_color: Mapped[str] = mapped_column(String(20), default="#FF6600")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    controller: Mapped[LEDController] = relationship(back_populates="bin_mappings")
