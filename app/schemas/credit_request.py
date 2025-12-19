"""
Credit request schemas.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid


class CreateCreditRequestRequest(BaseModel):
    bank_id: uuid.UUID
    requested_amount: float
    requested_limit: float
    station_id: Optional[uuid.UUID] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class CreditRequestResponse(BaseModel):
    id: uuid.UUID
    driver_id: uuid.UUID
    bank_id: uuid.UUID
    requested_amount: float
    requested_limit: float
    status: str
    station_id: Optional[uuid.UUID] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    reviewed_by_user_id: Optional[uuid.UUID] = None
    reviewed_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    credit_line_id: Optional[uuid.UUID] = None
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

