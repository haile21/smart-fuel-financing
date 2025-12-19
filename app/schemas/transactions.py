from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AuthorizeRequest(BaseModel):
    idempotency_key: str = Field(..., description="Unique key from POS/frontend")
    bank_id: int
    merchant_id: int
    driver_id: int
    max_amount: float = Field(..., gt=0)


class AuthorizeResponse(BaseModel):
    trace_id: str
    transaction_id: int
    authorized_amount: float
    status: str


class CaptureRequest(BaseModel):
    transaction_id: int
    final_amount: float = Field(..., gt=0)


class CaptureResponse(BaseModel):
    trace_id: str
    transaction_id: int
    settled_amount: float
    status: str


class TransactionRead(BaseModel):
    id: int
    bank_id: int
    merchant_id: int
    driver_id: int
    authorized_amount: float
    settled_amount: Optional[float]
    status: str
    authorized_at: datetime
    settled_at: Optional[datetime]

    class Config:
        from_attributes = True


