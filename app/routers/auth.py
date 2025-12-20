"""
Auth router: OTP and JWT token endpoints.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import (
    RequestOtpRequest,
    RequestOtpResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from app.models import UserRole

router = APIRouter()


@router.post("/otp/send", response_model=RequestOtpResponse)
def send_otp(
    payload: RequestOtpRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = AuthService(db)
    
    try:
        role = UserRole(payload.role.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}",
        )
    
    otp_code = service.generate_otp(payload.phone_number)
    
    # In production, OTP is sent via SMS and not returned
    return RequestOtpResponse(
        trace_id=trace_id,
        message=f"OTP sent to {payload.phone_number}. Use {otp_code} for testing.",
    )


@router.post("/otp/verify", response_model=VerifyOtpResponse)
def verify_otp(
    payload: VerifyOtpRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = AuthService(db)
    
    try:
        role = UserRole(payload.role.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role",
        )
    
    result = service.login_with_otp(payload.phone_number, payload.otp_code, role)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OTP code",
        )
    
    return VerifyOtpResponse(
        trace_id=trace_id,
        access_token=result["access_token"],
        token_type=result["token_type"],
        user_id=result["user_id"],
        role=result["role"],
    )

