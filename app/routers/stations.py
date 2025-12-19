"""
Station API endpoints: Registration, profile, status updates, fuel availability management.
Stations can register and update their status, fuel types, and availability in real-time.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
import json

from app.db.session import get_db
from app.services.station_service import StationService
from app.services.transaction_qr_service import TransactionQrService
from app.core.security import require_merchant, get_current_user
from app.schemas.station import (
    CreateStationRequest,
    StationResponse,
    UpdateStationStatusRequest,
    UpdateFuelTypesRequest,
    UpdateFuelAvailabilityRequest,
    BulkUpdateFuelAvailabilityRequest,
    UpdateOperatingHoursRequest,
    UpdateStationInfoRequest,
    FuelAvailabilityResponse,
)
from app.models.entities import User, FuelStation

router = APIRouter()


# Note: Station registration is done by AGENTS via /admin/agent/onboard-station
# Merchants can only update their station status, not register new ones


@router.get("/profile", response_model=StationResponse)
def get_station_profile(
    station_id: int,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    GET /stations/profile?station_id=X
    Get station profile information (public).
    """
    trace_id = getattr(request.state, "trace_id", "")
    
    station = db.get(FuelStation, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Station not found",
        )
    
    fuel_types = json.loads(station.fuel_types_available) if station.fuel_types_available else None
    operating_hours = json.loads(station.operating_hours) if station.operating_hours else None
    
    return StationResponse(
        id=station.id,
        name=station.name,
        merchant_id=station.merchant_id,
        address=station.address,
        latitude=float(station.latitude) if station.latitude else None,
        longitude=float(station.longitude) if station.longitude else None,
        is_open=station.is_open,
        current_price_per_liter=float(station.current_fuel_price_per_liter) if station.current_fuel_price_per_liter else None,
        fuel_types_available=fuel_types,
        operating_hours=operating_hours,
        phone_number=station.phone_number,
        email=station.email,
        created_at=station.created_at.isoformat(),
        updated_at=station.updated_at.isoformat(),
    )


@router.put("/status")
def update_station_status(
    station_id: int,
    payload: UpdateStationStatusRequest,
    request: Request,
    current_user: User = Depends(require_merchant),  # Merchant must be authenticated
    db: Session = Depends(get_db),
):
    """
    PUT /stations/status?station_id=X
    Merchant updates station status (open/closed, general price).
    Note: Stations are onboarded by agents, but merchants update their status.
    """
    trace_id = getattr(request.state, "trace_id", "")
    
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
            is_open=payload.is_open,
            current_price_per_liter=payload.current_price_per_liter,
        )
        
        # Update last_status_update timestamp
        from datetime import datetime
        station.last_status_update = datetime.utcnow()
        db.commit()
        db.refresh(station)
        
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


@router.put("/fuel-types")
def update_fuel_types(
    station_id: int,
    payload: UpdateFuelTypesRequest,
    request: Request,
    current_user: User = Depends(require_merchant),
    db: Session = Depends(get_db),
):
    """
    PUT /stations/fuel-types?station_id=X
    Update available fuel types for the station.
    """
    trace_id = getattr(request.state, "trace_id", "")
    
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


@router.put("/fuel-availability")
def update_fuel_availability(
    station_id: int,
    payload: UpdateFuelAvailabilityRequest,
    request: Request,
    current_user: User = Depends(require_merchant),
    db: Session = Depends(get_db),
):
    """
    PUT /stations/fuel-availability?station_id=X
    Update availability for a specific fuel type (available/unavailable, price, liters remaining).
    """
    trace_id = getattr(request.state, "trace_id", "")
    
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
        )
        
        # Price is now stored per fuel type in FuelAvailability
        # Also update general price for backward compatibility
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
        "last_updated": availability.last_updated.isoformat(),
    }


@router.put("/fuel-availability/bulk")
def bulk_update_fuel_availability(
    station_id: int,
    payload: BulkUpdateFuelAvailabilityRequest,
    request: Request,
    current_user: User = Depends(require_merchant),
    db: Session = Depends(get_db),
):
    """
    PUT /stations/fuel-availability/bulk?station_id=X
    Update multiple fuel types at once (bulk update).
    """
    trace_id = getattr(request.state, "trace_id", "")
    
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
            )
            results.append({
                "fuel_type": availability.fuel_type,
                "is_available": availability.is_available,
                "estimated_liters_remaining": float(availability.estimated_liters_remaining) if availability.estimated_liters_remaining else None,
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


@router.put("/operating-hours")
def update_operating_hours(
    station_id: int,
    payload: UpdateOperatingHoursRequest,
    request: Request,
    current_user: User = Depends(require_merchant),
    db: Session = Depends(get_db),
):
    """
    PUT /stations/operating-hours?station_id=X
    Update operating hours for the station.
    """
    trace_id = getattr(request.state, "trace_id", "")
    
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
    
    station.operating_hours = json.dumps(payload.operating_hours)
    from datetime import datetime
    station.updated_at = datetime.utcnow()
    station.last_status_update = datetime.utcnow()
    db.commit()
    db.refresh(station)
    
    return {
        "trace_id": trace_id,
        "station_id": station.id,
        "operating_hours": payload.operating_hours,
        "updated_at": station.updated_at.isoformat(),
    }


@router.put("/info")
def update_station_info(
    station_id: int,
    payload: UpdateStationInfoRequest,
    request: Request,
    current_user: User = Depends(require_merchant),
    db: Session = Depends(get_db),
):
    """
    PUT /stations/info?station_id=X
    Update station information (name, address, location, contact).
    """
    trace_id = getattr(request.state, "trace_id", "")
    
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
    
    if payload.name is not None:
        station.name = payload.name
    if payload.address is not None:
        station.address = payload.address
    if payload.latitude is not None:
        station.latitude = payload.latitude
    if payload.longitude is not None:
        station.longitude = payload.longitude
    if payload.phone_number is not None:
        station.phone_number = payload.phone_number
    if payload.email is not None:
        station.email = payload.email
    
    from datetime import datetime
    station.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(station)
    
    return {
        "trace_id": trace_id,
        "station_id": station.id,
        "message": "Station information updated",
        "updated_at": station.updated_at.isoformat(),
    }


@router.get("/availability", response_model=FuelAvailabilityResponse)
def get_station_availability(
    station_id: int,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    GET /stations/availability?station_id=X
    Get full availability information for a station (public).
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = StationService(db)
    
    try:
        availability = service.get_station_availability(station_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    station = db.get(FuelStation, station_id)
    operating_hours = json.loads(station.operating_hours) if station and station.operating_hours else None
    
    return FuelAvailabilityResponse(
        station_id=availability["station_id"],
        name=availability["name"],
        is_open=availability["is_open"],
        current_price_per_liter=availability["current_price_per_liter"],
        fuel_availability=availability["fuel_availability"],
        operating_hours=operating_hours,
        last_updated=availability.get("last_updated", station.updated_at.isoformat() if station else ""),
    )


@router.get("/nearby", response_model=List[StationResponse])
def get_nearby_stations(
    latitude: float,
    longitude: float,
    radius_km: float = 10.0,
    fuel_type: Optional[str] = None,
    is_open_only: bool = True,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    GET /stations/nearby?latitude=X&longitude=Y&radius_km=Z&fuel_type=PETROL&is_open_only=true
    Find nearby fuel stations with optional filters.
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = StationService(db)
    
    stations = service.get_nearby_stations(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        fuel_type=fuel_type,
    )
    
    # Filter by is_open if requested
    if is_open_only:
        stations = [s for s in stations if s.is_open]
    
    result = []
    for s in stations:
        fuel_types = json.loads(s.fuel_types_available) if s.fuel_types_available else None
        operating_hours = json.loads(s.operating_hours) if s.operating_hours else None
        
        result.append(StationResponse(
            id=s.id,
            name=s.name,
            merchant_id=s.merchant_id,
            address=s.address,
            latitude=float(s.latitude) if s.latitude else None,
            longitude=float(s.longitude) if s.longitude else None,
            is_open=s.is_open,
            current_price_per_liter=float(s.current_fuel_price_per_liter) if s.current_fuel_price_per_liter else None,
            fuel_types_available=fuel_types,
            operating_hours=operating_hours,
            phone_number=s.phone_number,
            email=s.email,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        ))
    
    return result


# QR and transaction endpoints
class ScanQrRequest(BaseModel):
    qr_id: str
    idempotency_key: str


class ConfirmFuelRequest(BaseModel):
    transaction_id: int
    settled_amount: float
    liters_pumped: Optional[float] = None


@router.post("/scan-qr")
def scan_qr_code(
    payload: ScanQrRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    POST /stations/scan-qr
    Station scans QR code from driver and authorizes transaction.
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


@router.post("/confirm-fuel")
def confirm_fuel(
    payload: ConfirmFuelRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    POST /stations/confirm-fuel
    Station confirms fuel pumped and settles transaction.
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
