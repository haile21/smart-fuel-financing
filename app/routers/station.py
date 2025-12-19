"""
Station router: Fuel station and availability management endpoints.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.station_service import StationService
from app.schemas.station import (
    CreateStationRequest,
    StationResponse,
    UpdateFuelAvailabilityRequest,
    FuelAvailabilityResponse,
)

router = APIRouter()


@router.post("/stations", response_model=StationResponse)
def create_station(
    payload: CreateStationRequest,
    request: Request,
    db: Session = Depends(get_db),
):
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
    
    return StationResponse(
        id=station.id,
        name=station.name,
        merchant_id=station.merchant_id,
        address=station.address,
        latitude=float(station.latitude) if station.latitude else None,
        longitude=float(station.longitude) if station.longitude else None,
        is_open=station.is_open,
        current_price_per_liter=float(station.current_fuel_price_per_liter) if station.current_fuel_price_per_liter else None,
    )


@router.get("/stations/{station_id}/availability", response_model=FuelAvailabilityResponse)
def get_station_availability(
    station_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = StationService(db)
    
    try:
        availability = service.get_station_availability(station_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return FuelAvailabilityResponse(**availability)


@router.put("/stations/{station_id}/fuel-availability")
def update_fuel_availability(
    station_id: int,
    payload: UpdateFuelAvailabilityRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = StationService(db)
    
    try:
        availability = service.update_fuel_availability(
            station_id=station_id,
            fuel_type=payload.fuel_type,
            is_available=payload.is_available,
            estimated_liters_remaining=payload.estimated_liters_remaining,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return {"trace_id": trace_id, "status": "success", "fuel_type": availability.fuel_type}


@router.get("/stations/nearby", response_model=list[StationResponse])
def get_nearby_stations(
    latitude: float,
    longitude: float,
    radius_km: float = 10.0,
    fuel_type: str = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = StationService(db)
    
    stations = service.get_nearby_stations(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        fuel_type=fuel_type,
    )
    
    return [
        StationResponse(
            id=s.id,
            name=s.name,
            merchant_id=s.merchant_id,
            address=s.address,
            latitude=float(s.latitude) if s.latitude else None,
            longitude=float(s.longitude) if s.longitude else None,
            is_open=s.is_open,
            current_price_per_liter=float(s.current_fuel_price_per_liter) if s.current_fuel_price_per_liter else None,
        )
        for s in stations
    ]

