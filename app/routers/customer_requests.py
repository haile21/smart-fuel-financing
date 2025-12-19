"""
Customer Requests Router: Endpoints for drivers to create credit line requests.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.credit_request_service import CreditRequestService
from app.schemas.credit_request import (
    CreateCreditRequestRequest,
    CreditRequestResponse,
)

router = APIRouter()


@router.post("/credit-request", response_model=CreditRequestResponse)
def create_credit_request(
    driver_id: int,
    payload: CreateCreditRequestRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Create a credit line request from driver (near fuel station).
    After approval, driver can generate QR codes for fuel transactions.
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = CreditRequestService(db)
    
    try:
        req = service.create_request(
            driver_id=driver_id,
            bank_id=payload.bank_id,
            requested_amount=payload.requested_amount,
            requested_limit=payload.requested_limit,
            station_id=payload.station_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return CreditRequestResponse(
        id=req.id,
        driver_id=req.driver_id,
        bank_id=req.bank_id,
        requested_amount=float(req.requested_amount),
        requested_limit=float(req.requested_limit),
        status=req.status,
        station_id=req.station_id,
        latitude=float(req.latitude) if req.latitude else None,
        longitude=float(req.longitude) if req.longitude else None,
        reviewed_by_user_id=req.reviewed_by_user_id,
        reviewed_at=req.reviewed_at.isoformat() if req.reviewed_at else None,
        rejection_reason=req.rejection_reason,
        credit_line_id=req.credit_line_id,
        created_at=req.created_at.isoformat(),
        driver_name=req.driver.name if req.driver else None,
        driver_phone=req.driver.phone_number if req.driver else None,
        bank_name=req.bank.name if req.bank else None,
        station_name=req.station.name if req.station else None,
    )


@router.get("/credit-requests", response_model=list[CreditRequestResponse])
def get_my_requests(
    driver_id: int,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Get all credit line requests for a driver.
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = CreditRequestService(db)
    
    requests = service.get_driver_requests(driver_id)
    
    return [
        CreditRequestResponse(
            id=req.id,
            driver_id=req.driver_id,
            bank_id=req.bank_id,
            requested_amount=float(req.requested_amount),
            requested_limit=float(req.requested_limit),
            status=req.status,
            station_id=req.station_id,
            latitude=float(req.latitude) if req.latitude else None,
            longitude=float(req.longitude) if req.longitude else None,
            reviewed_by_user_id=req.reviewed_by_user_id,
            reviewed_at=req.reviewed_at.isoformat() if req.reviewed_at else None,
            rejection_reason=req.rejection_reason,
            credit_line_id=req.credit_line_id,
            created_at=req.created_at.isoformat(),
            driver_name=req.driver.name if req.driver else None,
            driver_phone=req.driver.phone_number if req.driver else None,
            bank_name=req.bank.name if req.bank else None,
            station_name=req.station.name if req.station else None,
        )
        for req in requests
    ]

