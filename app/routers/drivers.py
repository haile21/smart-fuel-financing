"""
Driver API endpoints: Registration, profile, credit limit, fuel loans, QR generation.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.services.driver_service import DriverService
from app.services.credit_engine_service import CreditEngineService
from app.services.credit_request_service import CreditRequestService
from app.services.transaction_qr_service import TransactionQrService
from app.services.loan_service import LoanService
from app.schemas.driver import DriverOnboardRequest, DriverProfile
from app.schemas.credit_request import CreateCreditRequestRequest
from app.models.entities import CreditLine

router = APIRouter()


class UpdateDriverProfileRequest(BaseModel):
    name: Optional[str] = None
    car_model: Optional[str] = None
    car_year: Optional[int] = None
    fuel_tank_capacity_liters: Optional[float] = None
    fuel_consumption_l_per_km: Optional[float] = None
    driver_license_number: Optional[str] = None
    plate_number: Optional[str] = None


class CreateFuelLoanRequest(BaseModel):
    bank_id: int
    requested_amount: float
    requested_limit: float
    station_id: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class GenerateQrRequest(BaseModel):
    expiry_minutes: int = 30


class ConfirmOtpRequest(BaseModel):
    otp_code: str


@router.post("/register", response_model=DriverProfile)
def register_driver(
    payload: DriverOnboardRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    POST /drivers/register
    Register a new driver with KYC information.
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = DriverService(db)
    
    try:
        driver = service.onboard_driver(
            phone_number=payload.phone_number,
            national_id=payload.national_id,
            name=payload.name,
            car_model=payload.car_model,
            car_year=payload.car_year,
            fuel_tank_capacity_liters=payload.fuel_tank_capacity_liters,
            fuel_consumption_l_per_km=payload.fuel_consumption_l_per_km,
            driver_license_number=payload.driver_license_number,
            plate_number=payload.plate_number,
            bank_id=payload.bank_id,
            consent_data_sharing=payload.consent_data_sharing,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    # Calculate limit based on risk category
    if driver.risk_category == "LOW":
        limit = 5000.0
    elif driver.risk_category == "HIGH":
        limit = 20000.0
    else:
        limit = 10000.0
    
    return DriverProfile(
        id=driver.id,
        name=driver.name,
        phone_number=driver.phone_number,
        national_id=driver.national_id or "",
        risk_category=driver.risk_category or "MEDIUM",
        credit_limit=limit,
        bank_id=driver.preferred_bank_id or payload.bank_id,
    )


@router.get("/profile", response_model=DriverProfile)
def get_driver_profile(
    driver_id: int,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    GET /drivers/profile?driver_id=X
    Get driver profile information.
    """
    trace_id = getattr(request.state, "trace_id", "")
    from app.models.entities import Driver
    
    driver = db.get(Driver, driver_id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found",
        )
    
    # Get credit limit
    credit_engine = CreditEngineService(db)
    credit_lines = (
        db.query(CreditLine)
        .filter(CreditLine.driver_id == driver_id)
        .all()
    )
    total_limit = sum(cl.credit_limit for cl in credit_lines) if credit_lines else 0.0
    
    return DriverProfile(
        id=driver.id,
        name=driver.name,
        phone_number=driver.phone_number,
        national_id=driver.national_id or "",
        risk_category=driver.risk_category or "MEDIUM",
        credit_limit=total_limit,
        bank_id=driver.preferred_bank_id or 0,
    )


@router.put("/profile")
def update_driver_profile(
    driver_id: int,
    payload: UpdateDriverProfileRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    PUT /drivers/profile?driver_id=X
    Update driver profile information.
    """
    trace_id = getattr(request.state, "trace_id", "")
    from app.services.kyc_service import KycService
    
    service = KycService(db)
    
    try:
        driver = service.update_driver_profile(
            driver_id=driver_id,
            **payload.dict(exclude_none=True),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return {"trace_id": trace_id, "status": "success", "driver_id": driver.id}


@router.get("/credit-limit")
def get_credit_limit(
    driver_id: int,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    GET /drivers/credit-limit?driver_id=X
    Get driver's credit limit and available credit.
    """
    trace_id = getattr(request.state, "trace_id", "")
    credit_engine = CreditEngineService(db)
    
    from app.models.entities import CreditLine
    
    credit_lines = (
        db.query(CreditLine)
        .filter(CreditLine.driver_id == driver_id)
        .all()
    )
    
    total_limit = sum(cl.credit_limit for cl in credit_lines)
    total_utilized = sum(cl.utilized_amount for cl in credit_lines)
    available = total_limit - total_utilized
    
    return {
        "trace_id": trace_id,
        "driver_id": driver_id,
        "total_credit_limit": total_limit,
        "utilized_amount": total_utilized,
        "available_credit": max(0.0, available),
    }


@router.post("/fuel-loans")
def create_fuel_loan(
    driver_id: int,
    payload: CreateFuelLoanRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    POST /drivers/fuel-loans?driver_id=X
    Create a fuel loan request (credit line request).
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
    
    return {
        "trace_id": trace_id,
        "request_id": req.id,
        "status": req.status,
        "message": "Fuel loan request created. Waiting for bank approval.",
    }


@router.get("/fuel-loans")
def get_fuel_loans(
    driver_id: int,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    GET /drivers/fuel-loans?driver_id=X
    Get all fuel loan requests for a driver.
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = CreditRequestService(db)
    
    requests = service.get_driver_requests(driver_id)
    
    return {
        "trace_id": trace_id,
        "driver_id": driver_id,
        "requests": [
            {
                "id": req.id,
                "bank_id": req.bank_id,
                "bank_name": req.bank.name if req.bank else None,
                "requested_amount": float(req.requested_amount),
                "requested_limit": float(req.requested_limit),
                "status": req.status,
                "created_at": req.created_at.isoformat(),
                "reviewed_at": req.reviewed_at.isoformat() if req.reviewed_at else None,
                "rejection_reason": req.rejection_reason,
                "credit_line_id": req.credit_line_id,
            }
            for req in requests
        ],
    }


@router.post("/fuel-loans/{loan_request_id}/qr")
def generate_qr_for_loan(
    loan_request_id: int,
    driver_id: int,
    payload: GenerateQrRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    POST /drivers/fuel-loans/{loan_request_id}/qr?driver_id=X
    Generate QR code for an approved fuel loan.
    """
    trace_id = getattr(request.state, "trace_id", "")
    
    # Check if request is approved
    service = CreditRequestService(db)
    req = service.get_request(loan_request_id)
    
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan request not found",
        )
    
    if req.driver_id != driver_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    
    if req.status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Loan request is {req.status}. Only approved requests can generate QR codes.",
        )
    
    if not req.credit_line_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credit line not created yet",
        )
    
    # Get station from request or require it
    station_id = req.station_id
    if not station_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Station ID required",
        )
    
    # Generate QR code
    qr_service = TransactionQrService(db)
    
    try:
        qr = qr_service.generate_qr_code(
            driver_id=driver_id,
            station_id=station_id,
            authorized_amount=req.requested_amount,
            expiry_minutes=payload.expiry_minutes,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return {
        "trace_id": trace_id,
        "qr_id": qr.id,
        "qr_image_url": qr.qr_image_url,
        "qr_data": qr.qr_data,
        "bank_account_number": qr.bank_account_number,
        "amount": float(qr.amount),
        "driver_phone_number": qr.driver_phone_number,
        "bank_name": qr.bank_name,
        "expires_at": qr.expires_at.isoformat(),
    }


@router.post("/fuel-loans/{loan_request_id}/otp/confirm")
def confirm_otp_for_loan(
    loan_request_id: int,
    driver_id: int,
    payload: ConfirmOtpRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    POST /drivers/fuel-loans/{loan_request_id}/otp/confirm?driver_id=X
    Confirm OTP for fuel loan (if required for security).
    """
    trace_id = getattr(request.state, "trace_id", "")
    from app.services.auth_service import AuthService
    from app.models.entities import Driver
    
    driver = db.get(Driver, driver_id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found",
        )
    
    auth_service = AuthService(db)
    
    if not auth_service.verify_otp(driver.phone_number, payload.otp_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP code",
        )
    
    return {
        "trace_id": trace_id,
        "status": "confirmed",
        "message": "OTP confirmed successfully",
    }

