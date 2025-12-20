"""
Driver API endpoints: Registration, profile, credit limit, fuel loans, QR generation.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid
from app.db.session import get_db
from app.services.driver_service import DriverService
from app.services.transaction_qr_service import TransactionQrService
from app.services.loan_service import LoanService
from app.schemas.driver import DriverOnboardRequest, DriverProfile

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
    driver_id: uuid.UUID,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    GET /drivers/profile?driver_id=X
    Get driver profile information.
    """
    trace_id = getattr(request.state, "trace_id", "")
    from app.models import Driver
    
    driver = db.get(Driver, driver_id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found",
        )
    
    
    # Default limit placeholder if needed by frontend, or remove field from schema if possible
    # For now, we set it to 0 or remove calculation
    total_limit = 0.0
    
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



# End of driver endpoints


