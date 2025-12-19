"""
Station/Fuel Availability Service: Manages fuel stations and real-time availability.
"""

from datetime import datetime
from typing import Optional, List
import json

from sqlalchemy.orm import Session

from app.models.entities import (
    FuelStation,
    FuelAvailability,
    Merchant,
)


class StationService:
    """
    Service for managing fuel stations and availability.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_station(
        self,
        merchant_id: int,
        name: str,
        *,
        address: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        fuel_types: Optional[List[str]] = None,
        current_price_per_liter: Optional[float] = None,
        operating_hours: Optional[dict] = None,
    ) -> FuelStation:
        """
        Create a new fuel station.
        """
        merchant = self.db.get(Merchant, merchant_id)
        if not merchant:
            raise ValueError("Merchant not found")
        
        station = FuelStation(
            merchant_id=merchant_id,
            name=name,
            address=address,
            latitude=latitude,
            longitude=longitude,
            fuel_types_available=json.dumps(fuel_types) if fuel_types else None,
            current_fuel_price_per_liter=current_price_per_liter,
            operating_hours=json.dumps(operating_hours) if operating_hours else None,
            is_open=True,
        )
        self.db.add(station)
        self.db.commit()
        self.db.refresh(station)
        
        # Create availability records for each fuel type
        if fuel_types:
            for fuel_type in fuel_types:
                availability = FuelAvailability(
                    station_id=station.id,
                    fuel_type=fuel_type,
                    is_available=True,
                )
                self.db.add(availability)
            self.db.commit()
        
        return station

    def update_station(
        self,
        station_id: int,
        *,
        name: Optional[str] = None,
        is_open: Optional[bool] = None,
        current_price_per_liter: Optional[float] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> FuelStation:
        """
        Update station information.
        """
        station = self.db.get(FuelStation, station_id)
        if not station:
            raise ValueError("Station not found")
        
        if name is not None:
            station.name = name
        if is_open is not None:
            station.is_open = is_open
        if current_price_per_liter is not None:
            station.current_fuel_price_per_liter = current_price_per_liter
        if latitude is not None:
            station.latitude = latitude
        if longitude is not None:
            station.longitude = longitude
        
        station.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(station)
        return station

    def update_fuel_availability(
        self,
        station_id: int,
        fuel_type: str,
        *,
        is_available: Optional[bool] = None,
        estimated_liters_remaining: Optional[float] = None,
    ) -> FuelAvailability:
        """
        Update fuel availability for a station.
        """
        station = self.db.get(FuelStation, station_id)
        if not station:
            raise ValueError("Station not found")
        
        availability = (
            self.db.query(FuelAvailability)
            .filter(
                FuelAvailability.station_id == station_id,
                FuelAvailability.fuel_type == fuel_type,
            )
            .first()
        )
        
        if not availability:
            availability = FuelAvailability(
                station_id=station_id,
                fuel_type=fuel_type,
                is_available=is_available if is_available is not None else True,
                estimated_liters_remaining=estimated_liters_remaining,
            )
            self.db.add(availability)
        else:
            if is_available is not None:
                availability.is_available = is_available
            if estimated_liters_remaining is not None:
                availability.estimated_liters_remaining = estimated_liters_remaining
        
        availability.last_updated = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(availability)
        return availability

    def get_nearby_stations(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 10.0,
        fuel_type: Optional[str] = None,
    ) -> List[FuelStation]:
        """
        Find nearby stations (simplified - in production use PostGIS for proper geospatial queries).
        """
        # Simple distance calculation (Haversine would be better, but requires PostGIS)
        # For now, return all stations (in production, implement proper geospatial query)
        query = (
            self.db.query(FuelStation)
            .filter(FuelStation.is_open == True)
        )
        
        if fuel_type:
            # Filter by fuel type availability
            stations_with_fuel = (
                self.db.query(FuelStation.id)
                .join(FuelAvailability)
                .filter(
                    FuelAvailability.fuel_type == fuel_type,
                    FuelAvailability.is_available == True,
                )
            )
            query = query.filter(FuelStation.id.in_(stations_with_fuel))
        
        return query.all()

    def get_station_availability(
        self,
        station_id: int,
    ) -> dict:
        """
        Get full availability information for a station.
        """
        station = self.db.get(FuelStation, station_id)
        if not station:
            raise ValueError("Station not found")
        
        availabilities = (
            self.db.query(FuelAvailability)
            .filter(FuelAvailability.station_id == station_id)
            .all()
        )
        
        return {
            "station_id": station.id,
            "name": station.name,
            "is_open": station.is_open,
            "current_price_per_liter": float(station.current_fuel_price_per_liter) if station.current_fuel_price_per_liter else None,
            "fuel_availability": [
                {
                    "fuel_type": a.fuel_type,
                    "is_available": a.is_available,
                    "estimated_liters_remaining": float(a.estimated_liters_remaining) if a.estimated_liters_remaining else None,
                    "last_updated": a.last_updated.isoformat(),
                }
                for a in availabilities
            ],
        }

