"""
Loan service schemas.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid


class LoanResponse(BaseModel):
    id: uuid.UUID
    principal_amount: float
    outstanding_balance: float
    interest_rate: float
    status: str
    due_date: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class RepaymentRequest(BaseModel):
    amount: float
    payment_method: str
    payment_reference: Optional[str] = None


class RepaymentResponse(BaseModel):
    id: uuid.UUID
    amount: float
    payment_method: str
    repaid_at: str

    class Config:
        from_attributes = True


class LoanStatementResponse(BaseModel):
    loan_id: uuid.UUID
    principal_amount: float
    outstanding_balance: float
    interest_rate: float
    status: str
    due_date: Optional[str] = None
    created_at: str
    paid_off_at: Optional[str] = None
    total_repaid: float
    repayments: List[RepaymentResponse]

