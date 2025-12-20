from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Numeric, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
import uuid
from datetime import datetime

from app.db.base import Base

if TYPE_CHECKING:
    from .transaction import Transaction
    from .driver import Driver
    from .station import FuelStation
    from .bank import Bank

class QrCode(Base):
    # Pre-auth Link
    transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("transaction.id"), nullable=True, index=True)
    
    driver_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("driver.id"), index=True)
    station_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("fuelstation.id"), index=True)
    bank_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("bank.id"), index=True)
    
    qr_data: Mapped[str] = mapped_column(String(512)) # Payload (Signed Token)
    qr_image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    # Security & Verification
    signature: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # HMAC signature
    
    # Simplified Content fields (No sensitive bank data)
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    
    authorized_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    transaction: Mapped[Optional["Transaction"]] = relationship("Transaction")
    driver: Mapped["Driver"] = relationship("Driver")
    station: Mapped["FuelStation"] = relationship("FuelStation")
    bank: Mapped["Bank"] = relationship("Bank")
