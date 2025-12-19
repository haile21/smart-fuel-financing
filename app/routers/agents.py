"""
Agent API endpoints: For agents who onboard fuel stations.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.station_service import StationService
from app.core.security import require_agent, get_current_user
from app.schemas.station import CreateStationRequest, StationResponse
from app.models.entities import User

router = APIRouter()


@router.post("/agents/stations/onboard", response_model=StationResponse)
def onboard_station(
    payload: CreateStationRequest,
    request: Request,
    current_user: User = Depends(require_agent),  # Agent or Super admin
    db: Session = Depends(get_db),
):
    """
    POST /agents/stations/onboard
    Agent onboards a new fuel station.
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


@router.get("/agents/stations")
def list_onboarded_stations(
    request: Request = None,
    current_user: User = Depends(require_agent),
    db: Session = Depends(get_db),
):
    """
    GET /agents/stations
    List stations onboarded by the agent.
    """
    trace_id = getattr(request.state, "trace_id", "")
    from app.models.entities import FuelStation
    
    # In a full implementation, you'd track which agent onboarded which station
    # For now, return all stations
    stations = db.query(FuelStation).all()
    
    return {
        "trace_id": trace_id,
        "agent_id": current_user.id,
        "stations": [
            {
                "id": s.id,
                "name": s.name,
                "merchant_id": s.merchant_id,
                "address": s.address,
                "is_open": s.is_open,
            }
            for s in stations
        ],
    }

