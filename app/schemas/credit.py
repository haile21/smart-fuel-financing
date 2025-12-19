from typing import Optional
import uuid

from pydantic import BaseModel, Field


class CreditLineRead(BaseModel):
    id: uuid.UUID
    bank_id: uuid.UUID
    driver_id: uuid.UUID
    credit_limit: float
    utilized_amount: float
    version: int

    class Config:
        from_attributes = True


class CreditLineCreate(BaseModel):
    bank_id: uuid.UUID
    driver_id: uuid.UUID
    credit_limit: float = Field(..., gt=0)


