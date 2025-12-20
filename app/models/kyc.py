from __future__ import annotations
import enum
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
import uuid
from datetime import datetime

from app.db.base import Base

if TYPE_CHECKING:
    from .driver import Driver
    from .user import User

class KycStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class KycDocument(Base):
    driver_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("driver.id"), nullable=False)
    
    document_type: Mapped[str] = mapped_column(String(64))
    document_url: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    
    verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    driver: Mapped["Driver"] = relationship("Driver")
    verifier: Mapped[Optional["User"]] = relationship("User")
