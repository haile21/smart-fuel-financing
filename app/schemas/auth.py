"""
Auth service schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional


class RequestOtpRequest(BaseModel):
    phone_number: str
    role: str = Field(..., description="User role: DRIVER, BANK_ADMIN, AGENT, MERCHANT, etc.")


class RequestOtpResponse(BaseModel):
    trace_id: str
    message: str


class VerifyOtpRequest(BaseModel):
    phone_number: str
    otp_code: str
    role: str


class VerifyOtpResponse(BaseModel):
    trace_id: str
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: str

