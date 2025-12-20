"""
Station service schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import time
import uuid


class StationFuelConfig(BaseModel):
    fuel_type: str = Field(..., description="Fuel type: PETROL, DIESEL, etc.")
    price: float = Field(..., description="Price per liter")


class CreateStationRequest(BaseModel):

    name: str
    bank_account_number: Optional[str] = None
    bank_routing_number: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    fuel_types: Optional[List[StationFuelConfig]] = Field(default=None, description="List of fuel types with prices")
    # current_price_per_liter removed in favor of per-type pricing
    operating_hours: Optional[Dict[str, str]] = Field(default=None, description="Operating hours: {'monday': '06:00-22:00', ...}")
    phone_number: Optional[str] = None
    email: Optional[str] = None


class StationResponse(BaseModel):
    id: uuid.UUID
    name: str

    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_open: bool
    bank_account_number: Optional[str] = None
    bank_routing_number: Optional[str] = None
    current_price_per_liter: Optional[float] = None
    fuel_types_available: Optional[List[str]] = None
    operating_hours: Optional[Dict[str, str]] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class UpdateStationStatusRequest(BaseModel):
    is_open: Optional[bool] = Field(None, description="Whether station is open or closed")
    current_price_per_liter: Optional[float] = Field(None, description="General fuel price per liter")


class UpdateFuelTypesRequest(BaseModel):
    fuel_types: List[str] = Field(..., description="List of available fuel types: ['PETROL', 'DIESEL', 'PREMIUM_PETROL']")


class UpdateFuelAvailabilityRequest(BaseModel):
    fuel_type: str = Field(..., description="Fuel type: PETROL, DIESEL, etc.")
    is_available: Optional[bool] = Field(None, description="Whether this fuel type is available")
    estimated_liters_remaining: Optional[float] = Field(None, description="Estimated liters remaining")
    price_per_liter: Optional[float] = Field(None, description="Price per liter for this fuel type")


class BulkUpdateFuelAvailabilityRequest(BaseModel):
    """Update multiple fuel types at once"""
    fuel_availabilities: List[UpdateFuelAvailabilityRequest] = Field(..., description="List of fuel availability updates")


class UpdateOperatingHoursRequest(BaseModel):
    operating_hours: Dict[str, str] = Field(..., description="Operating hours: {'monday': '06:00-22:00', 'tuesday': '06:00-22:00', ...}")


class UpdateStationInfoRequest(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None


class FuelAvailabilityResponse(BaseModel):
    station_id: uuid.UUID
    name: str
    is_open: bool
    current_price_per_liter: Optional[float] = None
    fuel_availability: List[dict]
    operating_hours: Optional[Dict[str, str]] = None
    last_updated: str
