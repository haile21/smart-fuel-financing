"""
Credit Request Service: Handles credit line requests from drivers and bank approvals.
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.entities import (
    CreditLineRequest,
    CreditLineRequestStatus,
    CreditLine,
    Driver,
    Bank,
    FuelStation,
    User,
)
from app.services.credit_engine_service import CreditEngineService


class CreditRequestService:
    """
    Service for managing credit line requests and bank approvals.
    """

    def __init__(self, db: Session):
        self.db = db
        self.credit_engine = CreditEngineService(db)

    def create_request(
        self,
        *,
        driver_id: int,
        bank_id: int,
        requested_amount: float,
        requested_limit: float,
        station_id: Optional[int] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> CreditLineRequest:
        """
        Create a credit line request from driver (near fuel station).
        """
        driver = self.db.get(Driver, driver_id)
        if not driver:
            raise ValueError("Driver not found")
        
        bank = self.db.get(Bank, bank_id)
        if not bank:
            raise ValueError("Bank not found")
        
        if station_id:
            station = self.db.get(FuelStation, station_id)
            if not station:
                raise ValueError("Station not found")
        
        request = CreditLineRequest(
            driver_id=driver_id,
            bank_id=bank_id,
            requested_amount=requested_amount,
            requested_limit=requested_limit,
            station_id=station_id,
            latitude=latitude,
            longitude=longitude,
            status=CreditLineRequestStatus.PENDING.value,
        )
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        return request

    def get_pending_requests(
        self,
        bank_id: Optional[int] = None,
    ) -> List[CreditLineRequest]:
        """
        Get pending credit line requests, optionally filtered by bank.
        """
        query = self.db.query(CreditLineRequest).filter(
            CreditLineRequest.status == CreditLineRequestStatus.PENDING.value
        )
        
        if bank_id:
            query = query.filter(CreditLineRequest.bank_id == bank_id)
        
        return query.order_by(CreditLineRequest.created_at.desc()).all()

    def approve_request(
        self,
        request_id: int,
        reviewer_user_id: int,
        approved_limit: Optional[float] = None,
    ) -> CreditLineRequest:
        """
        Approve a credit line request and create the credit line.
        """
        request = self.db.get(CreditLineRequest, request_id)
        if not request:
            raise ValueError("Request not found")
        
        if request.status != CreditLineRequestStatus.PENDING.value:
            raise ValueError(f"Request already {request.status}")
        
        # Use approved_limit if provided, otherwise use requested_limit
        final_limit = approved_limit if approved_limit is not None else request.requested_limit
        
        # Create credit line
        credit_line = self.credit_engine.create_credit_line(
            bank_id=request.bank_id,
            credit_limit=final_limit,
            driver_id=request.driver_id,
        )
        
        # Update request
        request.status = CreditLineRequestStatus.APPROVED.value
        request.reviewed_by_user_id = reviewer_user_id
        request.reviewed_at = datetime.utcnow()
        request.credit_line_id = credit_line.id
        
        self.db.commit()
        self.db.refresh(request)
        return request

    def reject_request(
        self,
        request_id: int,
        reviewer_user_id: int,
        rejection_reason: str,
    ) -> CreditLineRequest:
        """
        Reject a credit line request.
        """
        request = self.db.get(CreditLineRequest, request_id)
        if not request:
            raise ValueError("Request not found")
        
        if request.status != CreditLineRequestStatus.PENDING.value:
            raise ValueError(f"Request already {request.status}")
        
        request.status = CreditLineRequestStatus.REJECTED.value
        request.reviewed_by_user_id = reviewer_user_id
        request.reviewed_at = datetime.utcnow()
        request.rejection_reason = rejection_reason
        
        self.db.commit()
        self.db.refresh(request)
        return request

    def get_request(
        self,
        request_id: int,
    ) -> Optional[CreditLineRequest]:
        """
        Get a specific credit line request.
        """
        return self.db.get(CreditLineRequest, request_id)

    def get_driver_requests(
        self,
        driver_id: int,
    ) -> List[CreditLineRequest]:
        """
        Get all credit line requests for a driver.
        """
        return (
            self.db.query(CreditLineRequest)
            .filter(CreditLineRequest.driver_id == driver_id)
            .order_by(CreditLineRequest.created_at.desc())
            .all()
        )

