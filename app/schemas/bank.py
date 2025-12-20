from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class BankBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    bank_code: str = Field(..., min_length=1, max_length=32)
    account_number: Optional[str] = Field(None, max_length=64)

class BankCreate(BankBase):
    pass

class BankUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    bank_code: Optional[str] = Field(None, min_length=1, max_length=32)
    account_number: Optional[str] = Field(None, max_length=64)

class BankResponse(BankBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
