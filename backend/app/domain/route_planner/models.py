from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, PrimaryKeyConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    vehicle_type: Mapped[str] = mapped_column(String(50))  # truck, van, trailer, car
    license_plate: Mapped[str] = mapped_column(String(20), nullable=True)
    max_weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=True)
    # Volume: either set directly or auto-calculated from interior dimensions
    max_volume_m3: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=True)
    interior_length_cm: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=True)
    interior_width_cm: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=True)
    interior_height_cm: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=True)
    # Towing: only trucks/vans can pull trailers
    can_pull_trailer: Mapped[bool] = mapped_column(Boolean, default=False)
    max_tow_weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=True)
    # Trailer-specific: curb weight (own weight) and payload capacity
    curb_weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=True)
    max_payload_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    route_assignments: Mapped[list["RouteVehicle"]] = relationship(back_populates="vehicle")


class DeliveryRoute(Base):
    __tablename__ = "delivery_routes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="planned", index=True)
    start_date: Mapped[date] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    stops: Mapped[list["RouteStop"]] = relationship(back_populates="route", cascade="all,delete-orphan", order_by="RouteStop.stop_order")
    vehicle_assignments: Mapped[list["RouteVehicle"]] = relationship(back_populates="route", cascade="all,delete-orphan", order_by="RouteVehicle.load_order")


class RouteVehicle(Base):
    """Junction table: which vehicles are assigned to a route, and in what load order."""
    __tablename__ = "route_vehicles"
    __table_args__ = (PrimaryKeyConstraint("route_id", "vehicle_id"),)

    route_id: Mapped[int] = mapped_column(ForeignKey("delivery_routes.id", ondelete="CASCADE"))
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    load_order: Mapped[int] = mapped_column(Integer, default=0)  # lower = loaded first
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    route: Mapped["DeliveryRoute"] = relationship(back_populates="vehicle_assignments")
    vehicle: Mapped["Vehicle"] = relationship(back_populates="route_assignments")


class RouteStop(Base):
    __tablename__ = "route_stops"

    id: Mapped[int] = mapped_column(primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("delivery_routes.id", ondelete="CASCADE"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    stop_order: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    route: Mapped["DeliveryRoute"] = relationship(back_populates="stops")
    job: Mapped["Job"] = relationship()
    vehicle: Mapped["Vehicle"] = relationship()
