from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Numeric, DateTime, UniqueConstraint, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
import uuid
from datetime import datetime

from app.db.base import Base

if TYPE_CHECKING:
    from .bank import Bank
    from .station import FuelStation
    from .driver import Driver

class Transaction(Base):
    """
    Double entry-like representation for a fuel transaction.
    """
    idempotency_key: Mapped[str] = mapped_column(String(64), index=True)

    funding_source_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("bank.id"), index=True)
    station_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("fuelstation.id"), index=True)
    debtor_driver_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("driver.id"), index=True, nullable=False)

    authorized_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    settled_amount: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)

    status: Mapped[str] = mapped_column(String(32), index=True, default="AUTHORIZED")
    authorized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    bank: Mapped["Bank"] = relationship("Bank")
    station: Mapped["FuelStation"] = relationship("FuelStation")
    driver: Mapped["Driver"] = relationship("Driver")

    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_transaction_idempotency"),
        Index("ix_transaction_debtor", "debtor_driver_id"),
    )

class IdempotencyKey(Base):
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    endpoint: Mapped[str] = mapped_column(String(255))
    response_body: Mapped[str] = mapped_column(String)  # JSON string
    status_code: Mapped[int] = mapped_column(Integer)
