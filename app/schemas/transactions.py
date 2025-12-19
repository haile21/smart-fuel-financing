from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, Field


class AuthorizeRequest(BaseModel):
    idempotency_key: str = Field(..., description="Unique key from POS/frontend")
    bank_id: uuid.UUID
    merchant_id: uuid.UUID
    driver_id: uuid.UUID
    max_amount: float = Field(..., gt=0)


class AuthorizeResponse(BaseModel):
    trace_id: str
    transaction_id: uuid.UUID
    authorized_amount: float
    status: str


class CaptureRequest(BaseModel):
    transaction_id: uuid.UUID
    final_amount: float = Field(..., gt=0)


class CaptureResponse(BaseModel):
    trace_id: str
    transaction_id: uuid.UUID
    settled_amount: float
    status: str


class TransactionRead(BaseModel):
    id: uuid.UUID
    bank_id: uuid.UUID
    merchant_id: uuid.UUID
    driver_id: uuid.UUID
    authorized_amount: float
    settled_amount: Optional[float]
    status: str
    authorized_at: datetime
    settled_at: Optional[datetime]

    class Config:
        from_attributes = True


