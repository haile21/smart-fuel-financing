from __future__ import annotations
import enum
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from .driver import Driver
    from .bank import Bank
    from .station import FuelStation
from sqlalchemy import String, Boolean, ForeignKey, Integer, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
import uuid
from datetime import datetime

from app.db.base import Base

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    DRIVER = "DRIVER"
    STATION_ATTENDANT = "STATION_ATTENDANT"
    BANKER = "BANKER"

class User(Base):
    """
    Unified user model with role-based access control.
    """
    # Authentication
    phone_number: Mapped[Optional[str]] = mapped_column(String(32), unique=True, index=True, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True, nullable=True)
    
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Profile
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Role management
    role: Mapped[str] = mapped_column(String(32), index=True, default="DRIVER")
    
    # Foreign keys
    driver_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("driver.id"), nullable=True)
    bank_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("bank.id"), nullable=True)
    station_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("fuelstation.id"), nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Audit
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships - using string forward references
    driver: Mapped[Optional["Driver"]] = relationship("Driver")
    bank: Mapped[Optional["Bank"]] = relationship("Bank")
    station: Mapped[Optional["FuelStation"]] = relationship("FuelStation")
    created_by: Mapped[Optional["User"]] = relationship("User", remote_side="User.id")
    
    __table_args__ = (
        Index("ix_user_phone_email", "phone_number", "email"),
    )

class OtpCode(Base):
    """
    OTP codes for phone-based authentication.
    """
    phone_number: Mapped[str] = mapped_column(String(32), index=True)
    code: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    # created_at is inherited from Base but explicit in entities.py. Base has it, so we can omit or keep.
    # Base implementation: created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # entities.py had default=datetime.utcnow (python side). server_default is better. I'll stick to Base.

    __table_args__ = (
        Index("ix_otp_phone_expires", "phone_number", "expires_at", "is_used"),
    )
