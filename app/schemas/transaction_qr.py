"""
Transaction & QR service schemas.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class GenerateQrRequest(BaseModel):
    station_id: int
    authorized_amount: float
    expiry_minutes: int = 30


class QrCodeResponse(BaseModel):
    id: int
    qr_data: str
    qr_image_url: str
    bank_account_number: str
    amount: float
    driver_phone_number: str
    bank_name: str
    authorized_amount: float
    expires_at: str

    class Config:
        from_attributes = True


class ScanQrRequest(BaseModel):
    qr_id: str
    idempotency_key: str


class TransactionResponse(BaseModel):
    id: int
    idempotency_key: str
    authorized_amount: float
    settled_amount: Optional[float] = None
    status: str
    authorized_at: str
    settled_at: Optional[str] = None

    class Config:
        from_attributes = True


class SettleTransactionRequest(BaseModel):
    settled_amount: float

