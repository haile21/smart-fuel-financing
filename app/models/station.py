from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, ForeignKey, Numeric, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
import uuid
from datetime import datetime

from app.db.base import Base



class FuelStation(Base):
    # Financials (Moved from Merchant)
    bank_account_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    bank_routing_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    name: Mapped[str] = mapped_column(String(255))
    
    # Location
    address: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 7), nullable=True)
    
    # Contact
    phone_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Status
    is_open: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    fuel_types_available: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    current_fuel_price_per_liter: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    
    operating_hours: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    last_status_update: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    fuel_availabilities: Mapped[list["FuelAvailability"]] = relationship("FuelAvailability", back_populates="station")

class FuelAvailability(Base):
    station_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("fuelstation.id"), index=True)
    fuel_type: Mapped[str] = mapped_column(String(32), index=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    estimated_liters_remaining: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    price_per_liter: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    station: Mapped["FuelStation"] = relationship("FuelStation", back_populates="fuel_availabilities")

    __table_args__ = (
        UniqueConstraint("station_id", "fuel_type", name="uq_fuel_availability_station_type"),
    )
