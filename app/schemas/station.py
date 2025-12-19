"""
Station service schemas.
"""

from pydantic import BaseModel
from typing import Optional, List


class CreateStationRequest(BaseModel):
    merchant_id: int
    name: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    fuel_types: Optional[List[str]] = None
    current_price_per_liter: Optional[float] = None


class StationResponse(BaseModel):
    id: int
    name: str
    merchant_id: int
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_open: bool
    current_price_per_liter: Optional[float] = None

    class Config:
        from_attributes = True


class UpdateFuelAvailabilityRequest(BaseModel):
    fuel_type: str
    is_available: Optional[bool] = None
    estimated_liters_remaining: Optional[float] = None


class FuelAvailabilityResponse(BaseModel):
    station_id: int
    name: str
    is_open: bool
    current_price_per_liter: Optional[float] = None
    fuel_availability: List[dict]

