from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.driver import (
    DriverOnboardRequest,
    DriverOnboardResponse,
    DriverProfile,
    RequestOtpRequest,
    RequestOtpResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from app.services.driver_service import DriverService

router = APIRouter()


@router.post("/onboard", response_model=DriverOnboardResponse)
def onboard_driver(
    payload: DriverOnboardRequest,
    request: Request,
    db: Session = Depends(get_db),
):
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

    # Very basic limit based on risk category; mirror logic from service
    if driver.risk_category == "LOW":
        limit = 5000.0
    elif driver.risk_category == "HIGH":
        limit = 20000.0
    else:
        limit = 10000.0

    profile = DriverProfile(
        id=driver.id,
        name=driver.name,
        phone_number=driver.phone_number,
        national_id=driver.national_id or "",
        risk_category=driver.risk_category or "MEDIUM",
        credit_limit=limit,
        bank_id=driver.preferred_bank_id or payload.bank_id,
    )

    return DriverOnboardResponse(trace_id=trace_id, driver=profile)


@router.post("/login/request-otp", response_model=RequestOtpResponse)
def request_otp(
    payload: RequestOtpRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    from app.services.auth_service import AuthService
    from app.models.entities import UserRole
    
    service = AuthService(db)
    try:
        role = UserRole.DRIVER  # Customer app is for drivers
        otp_code = service.generate_otp(payload.phone_number)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    
    # In production, OTP is sent via SMS and not returned
    return RequestOtpResponse(
        trace_id=trace_id,
        message=f"OTP sent to {payload.phone_number}. Use {otp_code} for testing.",
    )


@router.post("/login/verify-otp", response_model=VerifyOtpResponse)
def verify_otp(
    payload: VerifyOtpRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    from app.services.auth_service import AuthService
    from app.models.entities import UserRole
    
    service = AuthService(db)
    result = service.login_with_otp(payload.phone_number, payload.otp_code, UserRole.DRIVER)
    
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


