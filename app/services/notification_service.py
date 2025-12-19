"""
Notification Service: Handles SMS, email, push, and in-app notifications.
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.entities import (
    Notification,
    NotificationType,
    NotificationStatus,
    Driver,
)


class NotificationService:
    """
    Notification service for sending various types of notifications.
    """

    def __init__(self, db: Session):
        self.db = db

    def send_sms(
        self,
        phone_number: str,
        message: str,
        recipient_id: Optional[int] = None,
        recipient_type: str = "DRIVER",
    ) -> Notification:
        """
        Send SMS notification (stub - integrate with SMS provider).
        """
        notification = Notification(
            recipient_type=recipient_type,
            recipient_id=recipient_id or 0,
            recipient_phone=phone_number,
            notification_type=NotificationType.SMS.value,
            title="SMS Notification",
            message=message,
            status=NotificationStatus.PENDING.value,
        )
        self.db.add(notification)
        self.db.commit()
        
        # Stub: In production, call SMS provider API here
        # For now, mark as sent
        notification.status = NotificationStatus.SENT.value
        notification.sent_at = datetime.utcnow()
        notification.external_id = f"sms-{notification.id}"
        self.db.commit()
        self.db.refresh(notification)
        
        return notification

    def send_email(
        self,
        email: str,
        subject: str,
        message: str,
        recipient_id: Optional[int] = None,
        recipient_type: str = "DRIVER",
    ) -> Notification:
        """
        Send email notification (stub - integrate with email provider).
        """
        notification = Notification(
            recipient_type=recipient_type,
            recipient_id=recipient_id or 0,
            recipient_email=email,
            notification_type=NotificationType.EMAIL.value,
            title=subject,
            message=message,
            status=NotificationStatus.PENDING.value,
        )
        self.db.add(notification)
        self.db.commit()
        
        # Stub: In production, call email provider API here
        notification.status = NotificationStatus.SENT.value
        notification.sent_at = datetime.utcnow()
        notification.external_id = f"email-{notification.id}"
        self.db.commit()
        self.db.refresh(notification)
        
        return notification

    def send_push_notification(
        self,
        recipient_id: int,
        recipient_type: str,
        title: str,
        message: str,
        device_token: Optional[str] = None,
    ) -> Notification:
        """
        Send push notification (stub - integrate with FCM/APNS).
        """
        notification = Notification(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            notification_type=NotificationType.PUSH.value,
            title=title,
            message=message,
            status=NotificationStatus.PENDING.value,
        )
        self.db.add(notification)
        self.db.commit()
        
        # Stub: In production, call FCM/APNS API here
        notification.status = NotificationStatus.SENT.value
        notification.sent_at = datetime.utcnow()
        notification.external_id = f"push-{notification.id}"
        self.db.commit()
        self.db.refresh(notification)
        
        return notification

    def send_in_app_notification(
        self,
        recipient_id: int,
        recipient_type: str,
        title: str,
        message: str,
    ) -> Notification:
        """
        Create in-app notification.
        """
        notification = Notification(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            notification_type=NotificationType.IN_APP.value,
            title=title,
            message=message,
            status=NotificationStatus.SENT.value,  # In-app is immediately "sent"
            sent_at=datetime.utcnow(),
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def get_notifications(
        self,
        recipient_id: int,
        recipient_type: str,
        *,
        notification_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Notification]:
        """
        Get notifications for a recipient.
        """
        query = (
            self.db.query(Notification)
            .filter(
                Notification.recipient_id == recipient_id,
                Notification.recipient_type == recipient_type,
            )
        )
        
        if notification_type:
            query = query.filter(Notification.notification_type == notification_type)
        
        return query.order_by(Notification.created_at.desc()).limit(limit).all()

    def mark_as_delivered(
        self,
        notification_id: int,
    ) -> Notification:
        """
        Mark notification as delivered.
        """
        notification = self.db.get(Notification, notification_id)
        if not notification:
            raise ValueError("Notification not found")
        
        notification.status = NotificationStatus.DELIVERED.value
        notification.delivered_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def send_transaction_notification(
        self,
        driver_id: int,
        transaction_id: int,
        transaction_type: str,  # "AUTHORIZED", "SETTLED", etc.
    ) -> List[Notification]:
        """
        Send notifications related to a transaction (SMS + in-app).
        """
        driver = self.db.get(Driver, driver_id)
        if not driver:
            raise ValueError("Driver not found")
        
        notifications = []
        
        if transaction_type == "AUTHORIZED":
            message = f"Fuel authorization successful. Amount: {transaction_id}"
            title = "Transaction Authorized"
        elif transaction_type == "SETTLED":
            message = f"Fuel transaction settled. Transaction ID: {transaction_id}"
            title = "Transaction Settled"
        else:
            message = f"Transaction update: {transaction_type}"
            title = "Transaction Update"
        
        # Send SMS
        if driver.phone_number:
            sms = self.send_sms(
                phone_number=driver.phone_number,
                message=message,
                recipient_id=driver_id,
                recipient_type="DRIVER",
            )
            notifications.append(sms)
        
        # Send in-app
        in_app = self.send_in_app_notification(
            recipient_id=driver_id,
            recipient_type="DRIVER",
            title=title,
            message=message,
        )
        notifications.append(in_app)
        
        return notifications

