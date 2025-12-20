"""
User management schemas.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
import uuid


class CreateUserRequest(BaseModel):
    role: str = Field(..., description="User role: SUPER_ADMIN, BANK_ADMIN, DRIVER, etc.")
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    driver_id: Optional[uuid.UUID] = None
    bank_id: Optional[uuid.UUID] = None
    station_id: Optional[uuid.UUID] = None


class UserResponse(BaseModel):
    id: uuid.UUID
    phone_number: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    driver_id: Optional[uuid.UUID] = None
    bank_id: Optional[uuid.UUID] = None
    station_id: Optional[uuid.UUID] = None
    is_active: bool
    is_verified: bool
    created_at: str
    last_login_at: Optional[str] = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UpdateUserRoleRequest(BaseModel):
    new_role: str


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    is_active: Optional[bool] = None

