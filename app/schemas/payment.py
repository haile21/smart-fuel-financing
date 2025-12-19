"""
Payment service schemas.
"""

from pydantic import BaseModel
from typing import Optional


class InitiatePaymentRequest(BaseModel):
    loan_id: Optional[int] = None
    transaction_id: Optional[int] = None
    payer_id: int
    payer_type: str
    amount: float
    payment_method: str
    payment_reference: Optional[str] = None


class PaymentResponse(BaseModel):
    id: int
    amount: float
    currency: str
    payment_method: str
    status: str
    external_payment_id: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True

