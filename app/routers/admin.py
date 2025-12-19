"""
Admin API endpoints: Bank loans overview, Kifiya overview, agent onboarding.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.services.driver_service import DriverService
from app.services.station_service import StationService
from app.services.loan_service import LoanService
from app.schemas.driver import DriverOnboardRequest
from app.schemas.station import CreateStationRequest

router = APIRouter()


@router.get("/admin/bank/loans")
def get_bank_loans(
    bank_id: int,
    status: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    GET /admin/bank/loans?bank_id=X&status=ACTIVE
    Get all loans for a bank.
    """
    trace_id = getattr(request.state, "trace_id", "")
    from app.models.entities import Loan, CreditLine
    
    # Get all credit lines for this bank
    credit_lines = db.query(CreditLine).filter(CreditLine.bank_id == bank_id).all()
    credit_line_ids = [cl.id for cl in credit_lines]
    
    # Get loans for these credit lines
    query = db.query(Loan).filter(Loan.credit_line_id.in_(credit_line_ids))
    
    if status:
        query = query.filter(Loan.status == status)
    
    loans = query.all()
    
    return {
        "trace_id": trace_id,
        "bank_id": bank_id,
        "total_loans": len(loans),
        "loans": [
            {
                "id": loan.id,
                "driver_id": loan.driver_id,
                "principal_amount": float(loan.principal_amount),
                "outstanding_balance": float(loan.outstanding_balance),
                "status": loan.status,
                "created_at": loan.created_at.isoformat(),
                "due_date": loan.due_date.isoformat() if loan.due_date else None,
            }
            for loan in loans
        ],
    }


@router.get("/admin/kifiya/overview")
def get_kifiya_overview(
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    GET /admin/kifiya/overview
    Get system overview (Kifiya = platform name).
    """
    trace_id = getattr(request.state, "trace_id", "")
    from app.models.entities import Driver, Loan, Transaction, CreditLine, CreditLineRequest
    
    total_drivers = db.query(Driver).count()
    total_loans = db.query(Loan).count()
    active_loans = db.query(Loan).filter(Loan.status == "ACTIVE").count()
    total_transactions = db.query(Transaction).count()
    pending_requests = db.query(CreditLineRequest).filter(CreditLineRequest.status == "PENDING").count()
    
    # Calculate total credit extended
    credit_lines = db.query(CreditLine).all()
    total_credit_limit = sum(float(cl.credit_limit) for cl in credit_lines)
    total_utilized = sum(float(cl.utilized_amount) for cl in credit_lines)
    
    return {
        "trace_id": trace_id,
        "overview": {
            "total_drivers": total_drivers,
            "total_loans": total_loans,
            "active_loans": active_loans,
            "total_transactions": total_transactions,
            "pending_credit_requests": pending_requests,
            "total_credit_extended": total_credit_limit,
            "total_credit_utilized": total_utilized,
            "total_credit_available": total_credit_limit - total_utilized,
        },
    }


@router.post("/admin/agent/onboard-driver")
def onboard_driver_agent(
    payload: DriverOnboardRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    POST /admin/agent/onboard-driver
    Agent (admin) onboards a driver.
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
    
    return {
        "trace_id": trace_id,
        "driver_id": driver.id,
        "status": "onboarded",
        "message": "Driver onboarded successfully",
    }


@router.post("/admin/agent/onboard-station")
def onboard_station_agent(
    payload: CreateStationRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    POST /admin/agent/onboard-station
    Agent (admin) onboards a fuel station.
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = StationService(db)
    
    try:
        station = service.create_station(
            merchant_id=payload.merchant_id,
            name=payload.name,
            address=payload.address,
            latitude=payload.latitude,
            longitude=payload.longitude,
            fuel_types=payload.fuel_types,
            current_price_per_liter=payload.current_price_per_liter,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return {
        "trace_id": trace_id,
        "station_id": station.id,
        "status": "onboarded",
        "message": "Station onboarded successfully",
    }

