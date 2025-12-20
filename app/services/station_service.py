"""
Station/Fuel Availability Service: Manages fuel stations and real-time availability.
"""

from datetime import datetime
from typing import Optional, List
import json
import uuid

from sqlalchemy.orm import Session

from app.models import (
    FuelStation,
    FuelAvailability,

)


class StationService:
    """
    Service for managing fuel stations and availability.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_station(
        self,
        name: str,
        *,
        bank_account_number: Optional[str] = None,
        bank_routing_number: Optional[str] = None,
        address: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        fuel_configs: Optional[List[dict]] = None, # List of dicts or objects with fuel_type and price
        operating_hours: Optional[dict] = None,
    ) -> FuelStation:
        """
        Create a new fuel station.
        fuel_configs: List of objects/dicts like [{"fuel_type": "Benzene", "price": 75.0}, ...]
        """
        
        # Extract fuel types string list
        fuel_type_names = [f["fuel_type"] for f in fuel_configs] if fuel_configs else None
        
        # Determine base price (legacy support - take the first one or None)
        base_price = None
        if fuel_configs and len(fuel_configs) > 0:
            base_price = fuel_configs[0]["price"]
            
        station = FuelStation(
            name=name,
            bank_account_number=bank_account_number,
            bank_routing_number=bank_routing_number,
            address=address,
            latitude=latitude,
            longitude=longitude,
            fuel_types_available=json.dumps(fuel_type_names) if fuel_type_names else None,
            current_fuel_price_per_liter=base_price,
            operating_hours=json.dumps(operating_hours) if operating_hours else None,
            is_open=True,
        )
        self.db.add(station)
        self.db.commit()
        self.db.refresh(station)
        
        # Create availability records for each fuel type with specific price
        if fuel_configs:
            for config in fuel_configs:
                # Handle both dict and object access if Pydantic model passed
                f_type = config.get("fuel_type") if isinstance(config, dict) else config.fuel_type
                f_price = config.get("price") if isinstance(config, dict) else config.price
                
                availability = FuelAvailability(
                    station_id=station.id,
                    fuel_type=f_type,
                    is_available=True,
                    price_per_liter=f_price
                )
                self.db.add(availability)
            self.db.commit()
        
        return station

    def update_station(
        self,
        station_id: uuid.UUID,
        *,
        name: Optional[str] = None,
        is_open: Optional[bool] = None,
        current_price_per_liter: Optional[float] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        phone_number: Optional[str] = None,
        email: Optional[str] = None,
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
        if phone_number is not None:
            station.phone_number = phone_number
        if email is not None:
            station.email = email
        
        station.updated_at = datetime.utcnow()
        station.last_status_update = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(station)
        return station

    def update_fuel_availability(
        self,
        station_id: uuid.UUID,
        fuel_type: str,
        *,
        is_available: Optional[bool] = None,
        estimated_liters_remaining: Optional[float] = None,
        price_per_liter: Optional[float] = None,
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
                price_per_liter=price_per_liter,
            )
            self.db.add(availability)
        else:
            if is_available is not None:
                availability.is_available = is_available
            if estimated_liters_remaining is not None:
                availability.estimated_liters_remaining = estimated_liters_remaining
            if price_per_liter is not None:
                availability.price_per_liter = price_per_liter
        
        availability.last_updated = datetime.utcnow()
        
        # Update station's last_status_update
        station.last_status_update = datetime.utcnow()
        
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
        station_id: uuid.UUID,
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
                    "price_per_liter": float(a.price_per_liter) if a.price_per_liter else None,
                    "last_updated": a.last_updated.isoformat(),
                }
                for a in availabilities
            ],
            "last_updated": station.last_status_update.isoformat() if station.last_status_update else station.updated_at.isoformat(),
        }

