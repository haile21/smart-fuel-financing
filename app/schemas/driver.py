from typing import Optional
import uuid

from pydantic import BaseModel, Field


class DriverOnboardRequest(BaseModel):
    phone_number: str
    national_id: str
    name: str

    car_model: Optional[str] = None
    car_year: Optional[int] = None
    fuel_tank_capacity_liters: Optional[float] = Field(default=None, gt=0)
    fuel_consumption_l_per_km: Optional[float] = Field(default=None, gt=0)

    driver_license_number: Optional[str] = None
    plate_number: Optional[str] = None

    bank_id: uuid.UUID = Field(..., description="Selected bank id (Coop / CBE / others)")
    consent_data_sharing: bool = Field(..., description="eKYC consent flag")


class DriverProfile(BaseModel):
    id: uuid.UUID
    name: str
    phone_number: str
    national_id: str
    risk_category: str
    credit_limit: float
    bank_id: uuid.UUID

    class Config:
        from_attributes = True


class DriverOnboardResponse(BaseModel):
    trace_id: str
    driver: DriverProfile


class RequestOtpRequest(BaseModel):
    phone_number: str


class RequestOtpResponse(BaseModel):
    trace_id: str
    message: str


class VerifyOtpRequest(BaseModel):
    phone_number: str
    otp_code: str


class VerifyOtpResponse(BaseModel):
    trace_id: str
    access_token: str
    token_type: str = "bearer"


