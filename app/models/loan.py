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
    from .bank import Bank
    from .driver import Driver

class LoanStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAID_OFF = "PAID_OFF"
    OVERDUE = "OVERDUE"
    DEFAULTED = "DEFAULTED"

class Loan(Base):
    bank_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("bank.id"), index=True)
    driver_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("driver.id"), nullable=False)
    
    principal_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    outstanding_balance: Mapped[float] = mapped_column(Numeric(18, 2))
    interest_rate: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0)
    
    status: Mapped[str] = mapped_column(String(32), index=True, default="ACTIVE")
    
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_off_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    bank: Mapped["Bank"] = relationship("Bank")
    driver: Mapped["Driver"] = relationship("Driver")
    repayments: Mapped[list["LoanRepayment"]] = relationship("LoanRepayment", back_populates="loan")

class LoanRepayment(Base):
    loan_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("loan.id"), index=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    payment_method: Mapped[str] = mapped_column(String(32))
    payment_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    repaid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    loan: Mapped["Loan"] = relationship("Loan", back_populates="repayments")
