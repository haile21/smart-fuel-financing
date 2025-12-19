"""
Payment service schemas.
"""

from pydantic import BaseModel
from typing import Optional
import uuid


class InitiatePaymentRequest(BaseModel):
    loan_id: Optional[uuid.UUID] = None
    transaction_id: Optional[uuid.UUID] = None
    payer_id: uuid.UUID
    payer_type: str
    amount: float
    payment_method: str
    payment_reference: Optional[str] = None


class PaymentResponse(BaseModel):
    id: uuid.UUID
    amount: float
    currency: str
    payment_method: str
    status: str
    external_payment_id: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True

