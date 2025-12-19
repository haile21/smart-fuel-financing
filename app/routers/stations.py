"""
Station API endpoints: Registration, profile, status, nearby stations, QR scanning, fuel confirmation.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.db.session import get_db
from app.services.station_service import StationService
from app.services.transaction_qr_service import TransactionQrService
from app.schemas.station import CreateStationRequest, StationResponse

router = APIRouter()


class RegisterStationRequest(BaseModel):
    merchant_id: int
    name: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    fuel_types: Optional[List[str]] = None
    current_price_per_liter: Optional[float] = None


class UpdateStationStatusRequest(BaseModel):
    is_open: Optional[bool] = None
    current_price_per_liter: Optional[float] = None


class ScanQrRequest(BaseModel):
    qr_id: str
    idempotency_key: str


class ConfirmFuelRequest(BaseModel):
    transaction_id: int
    settled_amount: float
    liters_pumped: Optional[float] = None


@router.post("/register", response_model=StationResponse)
def register_station(
    payload: RegisterStationRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    POST /stations/register
    Register a new fuel station.
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


@router.get("/profile", response_model=StationResponse)
def get_station_profile(
    station_id: int,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    GET /stations/profile?station_id=X
    Get station profile information.
    """
    trace_id = getattr(request.state, "trace_id", "")
    from app.models.entities import FuelStation
    
    station = db.get(FuelStation, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Station not found",
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


@router.put("/status")
def update_station_status(
    station_id: int,
    payload: UpdateStationStatusRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    PUT /stations/status?station_id=X
    Update station status (open/closed, price).
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = StationService(db)
    
    try:
        station = service.update_station(
            station_id=station_id,
            is_open=payload.is_open,
            current_price_per_liter=payload.current_price_per_liter,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return {
        "trace_id": trace_id,
        "station_id": station.id,
        "is_open": station.is_open,
        "current_price_per_liter": float(station.current_fuel_price_per_liter) if station.current_fuel_price_per_liter else None,
    }


@router.get("/nearby", response_model=List[StationResponse])
def get_nearby_stations(
    latitude: float,
    longitude: float,
    radius_km: float = 10.0,
    fuel_type: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    GET /stations/nearby?latitude=X&longitude=Y&radius_km=Z&fuel_type=PETROL
    Find nearby fuel stations.
    """
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

