"""
Merchant API endpoints: For merchants who provide fuel services.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.db.session import get_db
from app.services.station_service import StationService
from app.services.transaction_qr_service import TransactionQrService
from app.core.security import require_merchant, get_current_user
from app.schemas.station import UpdateFuelAvailabilityRequest, BulkUpdateFuelAvailabilityRequest
from app.models.entities import User

router = APIRouter()


class ScanQrRequest(BaseModel):
    qr_id: str
    idempotency_key: str


class ConfirmFuelRequest(BaseModel):
    transaction_id: int
    settled_amount: float
    liters_pumped: Optional[float] = None


class UpdateFuelTypesRequest(BaseModel):
    fuel_types: List[str]


class UpdateFuelTypesRequest(BaseModel):
    fuel_types: List[str]


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
    import json
    
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
                "fuel_types_available": json.loads(s.fuel_types_available) if s.fuel_types_available else [],
                "operating_hours": json.loads(s.operating_hours) if s.operating_hours else None,
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
    Merchant updates station status (open/closed, general price).
    Stations are onboarded by agents, but merchants update their status.
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
        "last_status_update": station.last_status_update.isoformat() if station.last_status_update else None,
    }


@router.put("/merchants/stations/{station_id}/fuel-types")
def update_fuel_types(
    station_id: int,
    payload: UpdateFuelTypesRequest,
    request: Request = None,
    current_user: User = Depends(require_merchant),
    db: Session = Depends(get_db),
):
    """
    PUT /merchants/stations/{station_id}/fuel-types
    Merchant updates available fuel types for their station.
    """
    trace_id = getattr(request.state, "trace_id", "")
    from app.models.entities import FuelStation
    import json
    
    station = db.get(FuelStation, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Station not found",
        )
    
    if station.merchant_id != current_user.merchant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    
    # Update fuel types
    station.fuel_types_available = json.dumps(payload.fuel_types)
    
    # Create/update fuel availability records
    service = StationService(db)
    for fuel_type in payload.fuel_types:
        service.update_fuel_availability(
            station_id=station_id,
            fuel_type=fuel_type,
            is_available=True,  # Default to available when adding
        )
    
    from datetime import datetime
    station.updated_at = datetime.utcnow()
    station.last_status_update = datetime.utcnow()
    db.commit()
    db.refresh(station)
    
    return {
        "trace_id": trace_id,
        "station_id": station.id,
        "fuel_types": payload.fuel_types,
        "updated_at": station.updated_at.isoformat(),
    }


@router.put("/merchants/stations/{station_id}/fuel-availability")
def update_fuel_availability(
    station_id: int,
    payload: UpdateFuelAvailabilityRequest,
    request: Request = None,
    current_user: User = Depends(require_merchant),
    db: Session = Depends(get_db),
):
    """
    PUT /merchants/stations/{station_id}/fuel-availability
    Merchant updates fuel availability for a specific fuel type.
    Use this to mark fuel as unavailable, update stock levels, or update prices.
    """
    trace_id = getattr(request.state, "trace_id", "")
    from app.models.entities import FuelStation
    
    station = db.get(FuelStation, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Station not found",
        )
    
    if station.merchant_id != current_user.merchant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    
    service = StationService(db)
    
    try:
        availability = service.update_fuel_availability(
            station_id=station_id,
            fuel_type=payload.fuel_type,
            is_available=payload.is_available,
            estimated_liters_remaining=payload.estimated_liters_remaining,
            price_per_liter=payload.price_per_liter,
        )
        
        # Update general price if provided
        if payload.price_per_liter:
            station.current_fuel_price_per_liter = payload.price_per_liter
            from datetime import datetime
            station.last_status_update = datetime.utcnow()
            db.commit()
            db.refresh(availability)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return {
        "trace_id": trace_id,
        "station_id": station_id,
        "fuel_type": availability.fuel_type,
        "is_available": availability.is_available,
        "estimated_liters_remaining": float(availability.estimated_liters_remaining) if availability.estimated_liters_remaining else None,
        "price_per_liter": float(availability.price_per_liter) if availability.price_per_liter else None,
        "last_updated": availability.last_updated.isoformat(),
    }


@router.put("/merchants/stations/{station_id}/fuel-availability/bulk")
def bulk_update_fuel_availability(
    station_id: int,
    payload: BulkUpdateFuelAvailabilityRequest,
    request: Request = None,
    current_user: User = Depends(require_merchant),
    db: Session = Depends(get_db),
):
    """
    PUT /merchants/stations/{station_id}/fuel-availability/bulk
    Merchant updates multiple fuel types at once (bulk update).
    Useful for end-of-day or morning stock updates.
    """
    trace_id = getattr(request.state, "trace_id", "")
    from app.models.entities import FuelStation
    
    station = db.get(FuelStation, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Station not found",
        )
    
    if station.merchant_id != current_user.merchant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    
    service = StationService(db)
    results = []
    
    for fuel_update in payload.fuel_availabilities:
        try:
            availability = service.update_fuel_availability(
                station_id=station_id,
                fuel_type=fuel_update.fuel_type,
                is_available=fuel_update.is_available,
                estimated_liters_remaining=fuel_update.estimated_liters_remaining,
                price_per_liter=fuel_update.price_per_liter,
            )
            results.append({
                "fuel_type": availability.fuel_type,
                "is_available": availability.is_available,
                "estimated_liters_remaining": float(availability.estimated_liters_remaining) if availability.estimated_liters_remaining else None,
                "price_per_liter": float(availability.price_per_liter) if availability.price_per_liter else None,
            })
        except Exception as e:
            results.append({
                "fuel_type": fuel_update.fuel_type,
                "error": str(e),
            })
    
    from datetime import datetime
    station.last_status_update = datetime.utcnow()
    db.commit()
    
    return {
        "trace_id": trace_id,
        "station_id": station_id,
        "updated": len([r for r in results if "error" not in r]),
        "results": results,
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

