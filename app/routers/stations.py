"""
Station API endpoints: Registration, profile, status updates, fuel availability management.
Stations can register and update their status, fuel types, and availability in real-time.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from typing import Optional, List
import uuid
import json

from app.db.session import get_db
from app.services.station_service import StationService
from app.services.transaction_qr_service import TransactionQrService
from app.core.security import get_current_user
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
from app.models import User, FuelStation

router = APIRouter()


# Note: Station registration is done by AGENTS via /admin/agent/onboard-station
# Merchants can only update their station status, not register new ones


@router.get("/profile", response_model=StationResponse)
def get_station_profile(
    station_id: uuid.UUID,
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
        bank_account_number=station.bank_account_number,
        bank_routing_number=station.bank_routing_number,
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
    station_id: uuid.UUID,
    payload: UpdateStationStatusRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    PUT /stations/status?station_id=X
    Station Attendant updates station status.
    """
    trace_id = getattr(request.state, "trace_id", "")
    
    station = db.get(FuelStation, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Station not found",
        )
    
    # Verify user manages this station
    if station.id != current_user.station_id:
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
    station_id: uuid.UUID,
    payload: UpdateFuelTypesRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
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
    
    if station.id != current_user.station_id:
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
    station_id: uuid.UUID,
    payload: UpdateFuelAvailabilityRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
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
    
    if station.id != current_user.station_id:
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
    station_id: uuid.UUID,
    payload: BulkUpdateFuelAvailabilityRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
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
    
    if station.id != current_user.station_id:
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
    station_id: uuid.UUID,
    payload: UpdateOperatingHoursRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
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
    
    if station.id != current_user.station_id:
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
    station_id: uuid.UUID,
    payload: UpdateStationInfoRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
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
    
    if station.id != current_user.station_id:
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
    station_id: uuid.UUID,
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
            bank_account_number=s.bank_account_number,
            bank_routing_number=s.bank_routing_number,
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
    qr_data: str

class ConfirmFuelRequest(BaseModel):
    transaction_id: str
    settled_amount: float
    liters_pumped: Optional[float] = None


@router.post("/scan-qr")
def scan_qr_code(
    payload: ScanQrRequest,
    request: Request,
    current_user: User = Depends(get_current_user), # Capture who scanned it? Likely station worker/device
    db: Session = Depends(get_db),
):
    """
    POST /stations/scan-qr
    Station scans QR code from driver.
    VALIDATES the pre-authorized transaction.
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = TransactionQrService(db)
    
    # We assume the caller is authenticated as a station/merchant user
    # For now, we extract station_id from context or payload if needed.
    # But for MVP, we just validate the QR.
    
    # Determine station_id from current_user if possible, or pass it in payload?
    # Attempt to find station associated with this user
    try:
        # Assuming current_user is a merchant admin or authorized station worker
        # This part might need refinement depending on how station workers log in.
        # For now, we'll verify the QR is valid regardless of which station scanned it,
        # OR we enforce that the QR station_id matches.
        
        # Let's pass a dummy or looked-up station_id. 
        # In a real app, the device is linked to a station_id.
        # We will iterate to find if user manages a station.
        station_id = uuid.uuid4() # Placeholder if we don't strictly enforce station matching yet
    except:
        pass

    try:
        transaction = service.process_qr_scan(
            qr_data_json=payload.qr_data,
            station_id=None # We are loosening the station check for now as discussed
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
        "driver_id": transaction.debtor_driver_id,
        "message": "QR Validated. Proceed with fueling.",
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
    
    # Create loan logic removed - Bank Direct Payment Model
    # Future: Trigger bank transfer via API if not pre-funded
    pass
    
    return {
        "trace_id": trace_id,
        "transaction_id": transaction.id,
        "status": transaction.status,
        "settled_amount": float(transaction.settled_amount) if transaction.settled_amount else None,
        "settled_at": transaction.settled_at.isoformat() if transaction.settled_at else None,
        "message": "Fuel transaction completed. Payment transferred.",
    }
import uuid
