from typing import Optional

from pydantic import BaseModel, Field


class CreditLineRead(BaseModel):
    id: int
    bank_id: int
    agency_id: Optional[int]
    driver_id: Optional[int]
    credit_limit: float
    utilized_amount: float
    version: int

    class Config:
        from_attributes = True


class CreditLineCreate(BaseModel):
    bank_id: int
    agency_id: Optional[int] = None
    driver_id: Optional[int] = None
    credit_limit: float = Field(..., gt=0)


class AgencyRiskScoreRequest(BaseModel):
    agency_id: int
    fleet_size: int
    average_repayment_days: float
    monthly_fuel_volume: float


class AgencyRiskScoreResponse(BaseModel):
    trace_id: str
    agency_id: int
    risk_score: float


