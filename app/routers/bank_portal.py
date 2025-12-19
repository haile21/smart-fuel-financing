"""
Bank Portal Router: Endpoints for banks to view and approve/reject credit line requests.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.credit_request_service import CreditRequestService
from app.schemas.credit_request import (
    CreditRequestResponse,
    ApproveRequestRequest,
    RejectRequestRequest,
)

router = APIRouter()


@router.get("/requests", response_model=list[CreditRequestResponse])
def get_pending_requests(
    bank_id: int,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Get all pending credit line requests for a bank.
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = CreditRequestService(db)
    
    requests = service.get_pending_requests(bank_id=bank_id)
    
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


@router.get("/requests/{request_id}", response_model=CreditRequestResponse)
def get_request(
    request_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Get a specific credit line request with full details.
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = CreditRequestService(db)
    
    req = service.get_request(request_id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found",
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


@router.post("/requests/{request_id}/approve", response_model=CreditRequestResponse)
def approve_request(
    request_id: int,
    payload: ApproveRequestRequest,
    request: Request,
    reviewer_user_id: int = 1,  # In production, get from JWT token
    db: Session = Depends(get_db),
):
    """
    Approve a credit line request. Creates the credit line automatically.
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = CreditRequestService(db)
    
    try:
        req = service.approve_request(
            request_id=request_id,
            reviewer_user_id=reviewer_user_id,
            approved_limit=payload.approved_limit,
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


@router.post("/requests/{request_id}/reject", response_model=CreditRequestResponse)
def reject_request(
    request_id: int,
    payload: RejectRequestRequest,
    request: Request,
    reviewer_user_id: int = 1,  # In production, get from JWT token
    db: Session = Depends(get_db),
):
    """
    Reject a credit line request.
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = CreditRequestService(db)
    
    try:
        req = service.reject_request(
            request_id=request_id,
            reviewer_user_id=reviewer_user_id,
            rejection_reason=payload.rejection_reason,
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

