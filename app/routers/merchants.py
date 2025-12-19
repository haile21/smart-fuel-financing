"""
Merchant API endpoints: For merchants who provide fuel services.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.services.station_service import StationService
from app.services.transaction_qr_service import TransactionQrService
from app.core.security import require_merchant, get_current_user
from app.models.entities import User

router = APIRouter()


class ScanQrRequest(BaseModel):
    qr_id: str
    idempotency_key: str


class ConfirmFuelRequest(BaseModel):
    transaction_id: int
    settled_amount: float
    liters_pumped: Optional[float] = None


@router.get("/merchants/stations")
def get_merchant_stations(
    request: Request = None,
    current_user: User = Depends(require_merchant),
    db: Session = Depends(get_db),
):
    """
    GET /merchants/stations
    Get all stations for the merchant.
    """
    trace_id = getattr(request.state, "trace_id", "")
    from app.models.entities import FuelStation
    
    stations = (
        db.query(FuelStation)
        .filter(FuelStation.merchant_id == current_user.merchant_id)
        .all()
    )
    
    return {
        "trace_id": trace_id,
        "merchant_id": current_user.merchant_id,
        "stations": [
            {
                "id": s.id,
                "name": s.name,
                "address": s.address,
                "is_open": s.is_open,
                "current_price_per_liter": float(s.current_fuel_price_per_liter) if s.current_fuel_price_per_liter else None,
            }
            for s in stations
        ],
    }


@router.put("/merchants/stations/{station_id}/status")
def update_station_status(
    station_id: int,
    is_open: Optional[bool] = None,
    current_price_per_liter: Optional[float] = None,
    request: Request = None,
    current_user: User = Depends(require_merchant),
    db: Session = Depends(get_db),
):
    """
    PUT /merchants/stations/{station_id}/status
    Update station status (open/closed, price).
    """
    trace_id = getattr(request.state, "trace_id", "")
    from app.models.entities import FuelStation
    
    station = db.get(FuelStation, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Station not found",
        )
    
    # Verify merchant owns this station
    if station.merchant_id != current_user.merchant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this station",
        )
    
    service = StationService(db)
    
    try:
        station = service.update_station(
            station_id=station_id,
            is_open=is_open,
            current_price_per_liter=current_price_per_liter,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return {
        "trace_id": trace_id,
        "station_id": station.id,
        "is_open": station.is_open,
        "current_price_per_liter": float(station.current_fuel_price_per_liter) if station.current_fuel_price_per_liter else None,
    }


@router.post("/merchants/scan-qr")
def scan_qr_code(
    payload: ScanQrRequest,
    request: Request,
    current_user: User = Depends(require_merchant),
    db: Session = Depends(get_db),
):
    """
    POST /merchants/scan-qr
    Merchant scans QR code from driver and authorizes transaction.
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = TransactionQrService(db)
    
    try:
        transaction = service.scan_and_authorize(
            qr_id=payload.qr_id,
            idempotency_key=payload.idempotency_key,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return {
        "trace_id": trace_id,
        "transaction_id": transaction.id,
        "status": transaction.status,
        "authorized_amount": float(transaction.authorized_amount),
        "authorized_at": transaction.authorized_at.isoformat(),
        "message": "Transaction authorized. Proceed with fueling.",
    }


@router.post("/merchants/confirm-fuel")
def confirm_fuel(
    payload: ConfirmFuelRequest,
    request: Request,
    current_user: User = Depends(require_merchant),
    db: Session = Depends(get_db),
):
    """
    POST /merchants/confirm-fuel
    Merchant confirms fuel pumped and settles transaction.
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = TransactionQrService(db)
    
    try:
        transaction = service.settle_transaction(
            transaction_id=payload.transaction_id,
            settled_amount=payload.settled_amount,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    # Create loan from settled transaction
    if transaction.status == "SETTLED" and transaction.settled_amount:
        from app.services.loan_service import LoanService
        from app.models.entities import CreditLine, Driver
        
        loan_service = LoanService(db)
        driver = db.get(Driver, transaction.debtor_driver_id)
        if driver:
            credit_line = (
                db.query(CreditLine)
                .filter(
                    CreditLine.driver_id == driver.id,
                    CreditLine.bank_id == transaction.funding_source_id,
                )
                .first()
            )
            if credit_line:
                try:
                    loan_service.create_loan_from_transaction(transaction.id, credit_line.id)
                except Exception:
                    pass
    
    return {
        "trace_id": trace_id,
        "transaction_id": transaction.id,
        "status": transaction.status,
        "settled_amount": float(transaction.settled_amount) if transaction.settled_amount else None,
        "settled_at": transaction.settled_at.isoformat() if transaction.settled_at else None,
        "message": "Fuel transaction completed. Payment transferred.",
    }

