"""
Credit request schemas.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CreateCreditRequestRequest(BaseModel):
    bank_id: int
    requested_amount: float
    requested_limit: float
    station_id: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class CreditRequestResponse(BaseModel):
    id: int
    driver_id: int
    bank_id: int
    requested_amount: float
    requested_limit: float
    status: str
    station_id: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    reviewed_by_user_id: Optional[int] = None
    reviewed_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    credit_line_id: Optional[int] = None
    created_at: str
    
    # Driver info
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    
    # Bank info
    bank_name: Optional[str] = None
    
    # Station info
    station_name: Optional[str] = None

    class Config:
        from_attributes = True


class ApproveRequestRequest(BaseModel):
    approved_limit: Optional[float] = None  # If not provided, uses requested_limit


class RejectRequestRequest(BaseModel):
    rejection_reason: str

