"""
User & KYC Service: Handles KYC workflow, document management, and user profile operations.
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session

from app.models import (
    Driver,
    KycDocument,
    KycStatus,
    User,
)


class KycService:
    """
    KYC service for managing document verification and user profiles.
    """

    def __init__(self, db: Session):
        self.db = db

    def upload_document(
        self,
        *,
        driver_id: int,
        document_type: str,
        document_url: str,
    ) -> KycDocument:
        """
        Upload a KYC document for driver.
        """
        doc = KycDocument(
            driver_id=driver_id,
            document_type=document_type,
            document_url=document_url,
            status=KycStatus.PENDING.value,
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get_documents(
        self,
        *,
        driver_id: int,
    ) -> List[KycDocument]:
        """
        Get all KYC documents for a driver.
        """
        return (
            self.db.query(KycDocument)
            .filter(KycDocument.driver_id == driver_id)
            .all()
        )

    def verify_document(
        self,
        document_id: int,
        verifier_user_id: int,
        approved: bool,
        rejection_reason: Optional[str] = None,
    ) -> KycDocument:
        """
        Approve or reject a KYC document.
        """
        doc = self.db.get(KycDocument, document_id)
        if not doc:
            raise ValueError("Document not found")
        
        if approved:
            doc.status = KycStatus.APPROVED.value
        else:
            doc.status = KycStatus.REJECTED.value
            doc.rejection_reason = rejection_reason
        
        doc.verified_by = verifier_user_id
        doc.verified_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get_kyc_status(
        self,
        *,
        driver_id: int,
    ) -> dict:
        """
        Get overall KYC status for a driver.
        Returns status summary with document counts.
        """
        docs = self.get_documents(driver_id=driver_id)
        
        if not docs:
            return {
                "status": "PENDING",
                "documents_uploaded": 0,
                "documents_approved": 0,
                "documents_rejected": 0,
                "documents_pending": 0,
            }
        
        approved = sum(1 for d in docs if d.status == KycStatus.APPROVED.value)
        rejected = sum(1 for d in docs if d.status == KycStatus.REJECTED.value)
        pending = sum(1 for d in docs if d.status == KycStatus.PENDING.value)
        
        # Overall status: APPROVED if all required docs approved, else PENDING/REJECTED
        if approved > 0 and rejected == 0 and pending == 0:
            overall_status = "APPROVED"
        elif rejected > 0:
            overall_status = "REJECTED"
        else:
            overall_status = "PENDING"
        
        return {
            "status": overall_status,
            "documents_uploaded": len(docs),
            "documents_approved": approved,
            "documents_rejected": rejected,
            "documents_pending": pending,
        }

    def update_driver_profile(
        self,
        driver_id: int,
        **kwargs,
    ) -> Driver:
        """
        Update driver profile fields.
        """
        driver = self.db.get(Driver, driver_id)
        if not driver:
            raise ValueError("Driver not found")
        
        allowed_fields = [
            "name", "national_id", "car_model", "car_year",
            "fuel_tank_capacity_liters", "fuel_consumption_l_per_km",
            "driver_license_number", "plate_number",
        ]
        
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(driver, field, value)
        
        self.db.commit()
        self.db.refresh(driver)
        return driver

