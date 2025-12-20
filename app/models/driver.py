from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
import uuid

from app.db.base import Base

if TYPE_CHECKING:
    from .bank import Bank

import enum

class KycLevel(str, enum.Enum):
    TIER_1 = "TIER_1"  # Basic (Self-declared)
    TIER_2 = "TIER_2"  # Verified (Fayda/National ID)
    TIER_3 = "TIER_3"  # Advanced (Biometric/Face Match)

class Driver(Base):
    """
    End customer / driver profile used by the customer app.
    """
    name: Mapped[str] = mapped_column(String(255), index=True)
    phone_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    national_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Fayda / KYC Integration
    fayda_ref_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True, nullable=True)
    is_fayda_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    kyc_level: Mapped[str] = mapped_column(String(16), default=KycLevel.TIER_1.value)

    # Vehicle profile
    car_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    car_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fuel_tank_capacity_liters: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    fuel_consumption_l_per_km: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)

    driver_license_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    plate_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Relationships
    preferred_bank_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("bank.id"), index=True, nullable=True)

    preferred_bank: Mapped[Optional["Bank"]] = relationship("Bank")

    # eKYC & risk
    consent_data_sharing: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_category: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
