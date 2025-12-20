from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    pass # No circular deps for now, kept for structure

class Bank(Base):
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    account_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    bank_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
