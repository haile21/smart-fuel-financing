from typing import Optional

from pydantic import BaseModel, Field


class CreditLineRead(BaseModel):
    id: int
    bank_id: int
    driver_id: int
    credit_limit: float
    utilized_amount: float
    version: int

    class Config:
        from_attributes = True


class CreditLineCreate(BaseModel):
    bank_id: int
    driver_id: int
    credit_limit: float = Field(..., gt=0)


