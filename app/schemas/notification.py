"""
Notification service schemas.
"""

from pydantic import BaseModel
from typing import Optional, List


class SendSmsRequest(BaseModel):
    phone_number: str
    message: str


class SendEmailRequest(BaseModel):
    email: str
    subject: str
    message: str


class NotificationResponse(BaseModel):
    id: int
    notification_type: str
    title: str
    message: str
    status: str
    created_at: str

    class Config:
        from_attributes = True

