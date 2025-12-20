from __future__ import annotations
import enum
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Numeric, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
import uuid
from datetime import datetime

from app.db.base import Base

if TYPE_CHECKING:
    from .loan import Loan
    from .transaction import Transaction

class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"

class Payment(Base):
    loan_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("loan.id"), nullable=True)
    transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("transaction.id"), nullable=True)
    
    payer_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), index=True)
    payer_type: Mapped[str] = mapped_column(String(32), default="DRIVER")
    
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="ETB")
    payment_method: Mapped[str] = mapped_column(String(32))
    
    status: Mapped[str] = mapped_column(String(32), index=True, default="PENDING")
    
    external_payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    payment_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    loan: Mapped[Optional["Loan"]] = relationship("Loan")
    transaction: Mapped[Optional["Transaction"]] = relationship("Transaction")
