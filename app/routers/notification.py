"""
Notification router: SMS, email, push, and in-app notification endpoints.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.notification_service import NotificationService
from app.schemas.notification import (
    SendSmsRequest,
    SendEmailRequest,
    NotificationResponse,
)

router = APIRouter()


@router.post("/sms", response_model=NotificationResponse)
def send_sms(
    payload: SendSmsRequest,
    request: Request,
    recipient_id: int = None,
    recipient_type: str = "DRIVER",
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = NotificationService(db)
    
    notification = service.send_sms(
        phone_number=payload.phone_number,
        message=payload.message,
        recipient_id=recipient_id,
        recipient_type=recipient_type,
    )
    
    return NotificationResponse(
        id=notification.id,
        notification_type=notification.notification_type,
        title=notification.title,
        message=notification.message,
        status=notification.status,
        created_at=notification.created_at.isoformat(),
    )


@router.post("/email", response_model=NotificationResponse)
def send_email(
    payload: SendEmailRequest,
    request: Request,
    recipient_id: int = None,
    recipient_type: str = "DRIVER",
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = NotificationService(db)
    
    notification = service.send_email(
        email=payload.email,
        subject=payload.subject,
        message=payload.message,
        recipient_id=recipient_id,
        recipient_type=recipient_type,
    )
    
    return NotificationResponse(
        id=notification.id,
        notification_type=notification.notification_type,
        title=notification.title,
        message=notification.message,
        status=notification.status,
        created_at=notification.created_at.isoformat(),
    )


@router.get("/notifications", response_model=list[NotificationResponse])
def get_notifications(
    recipient_id: int,
    recipient_type: str,
    notification_type: str = None,
    limit: int = 50,
    request: Request = None,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = NotificationService(db)
    
    notifications = service.get_notifications(
        recipient_id=recipient_id,
        recipient_type=recipient_type,
        notification_type=notification_type,
        limit=limit,
    )
    
    return [
        NotificationResponse(
            id=n.id,
            notification_type=n.notification_type,
            title=n.title,
            message=n.message,
            status=n.status,
            created_at=n.created_at.isoformat(),
        )
        for n in notifications
    ]

