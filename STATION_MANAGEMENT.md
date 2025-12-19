# Station Management Guide

## Overview

Fuel stations can register themselves and update their status, fuel availability, and operating information in real-time. This enables drivers to see accurate, up-to-date information about fuel availability.

## Station Registration

### Register a New Station

**Endpoint:** `POST /stations/register`  
**Authentication:** Required (MERCHANT role)

**Request:**
```json
{
  "merchant_id": 1,
  "name": "Shell Station - Addis Ababa",
  "address": "Bole Road, Addis Ababa",
  "latitude": 9.1450,
  "longitude": 38.7617,
  "fuel_types": ["PETROL", "DIESEL", "PREMIUM_PETROL"],
  "current_price_per_liter": 45.50,
  "operating_hours": {
    "monday": "06:00-22:00",
    "tuesday": "06:00-22:00",
    "wednesday": "06:00-22:00",
    "thursday": "06:00-22:00",
    "friday": "06:00-22:00",
    "saturday": "06:00-22:00",
    "sunday": "07:00-21:00"
  },
  "phone_number": "+251911234567",
  "email": "station@shell.com"
}
```

**Response:**
```json
{
  "id": 1,
  "name": "Shell Station - Addis Ababa",
  "merchant_id": 1,
  "is_open": true,
  "fuel_types_available": ["PETROL", "DIESEL", "PREMIUM_PETROL"],
  "current_price_per_liter": 45.50,
  "operating_hours": {...},
  "created_at": "2024-01-01T10:00:00Z"
}
```

## Real-Time Status Updates

### Update Station Status (Open/Closed)

**Endpoint:** `PUT /stations/status?station_id=X`  
**Authentication:** Required (MERCHANT role, must own station)

**Request:**
```json
{
  "is_open": false,  // Close station
  "current_price_per_liter": 46.00  // Update price
}
```

**Use Cases:**
- Station closes for the day: `{"is_open": false}`
- Station opens: `{"is_open": true}`
- Update general fuel price: `{"current_price_per_liter": 46.00}`

### Update Available Fuel Types

**Endpoint:** `PUT /stations/fuel-types?station_id=X`  
**Authentication:** Required (MERCHANT role)

**Request:**
```json
{
  "fuel_types": ["PETROL", "DIESEL", "PREMIUM_PETROL", "SUPER"]
}
```

**What Happens:**
- Updates the list of fuel types the station offers
- Creates availability records for new fuel types
- Existing availability records are preserved

### Update Fuel Availability (Per Type)

**Endpoint:** `PUT /stations/fuel-availability?station_id=X`  
**Authentication:** Required (MERCHANT role)

**Request:**
```json
{
  "fuel_type": "PETROL",
  "is_available": false,  // Mark as unavailable
  "estimated_liters_remaining": 5000.0,  // Update stock
  "price_per_liter": 45.50  // Update price for this type
}
```

**Use Cases:**
- Run out of fuel: `{"fuel_type": "DIESEL", "is_available": false}`
- Restock fuel: `{"fuel_type": "DIESEL", "is_available": true, "estimated_liters_remaining": 10000.0}`
- Update price: `{"fuel_type": "PETROL", "price_per_liter": 46.00}`

### Bulk Update Fuel Availability

**Endpoint:** `PUT /stations/fuel-availability/bulk?station_id=X`  
**Authentication:** Required (MERCHANT role)

**Request:**
```json
{
  "fuel_availabilities": [
    {
      "fuel_type": "PETROL",
      "is_available": true,
      "estimated_liters_remaining": 8000.0,
      "price_per_liter": 45.50
    },
    {
      "fuel_type": "DIESEL",
      "is_available": false,
      "estimated_liters_remaining": 0.0
    },
    {
      "fuel_type": "PREMIUM_PETROL",
      "is_available": true,
      "estimated_liters_remaining": 3000.0,
      "price_per_liter": 48.00
    }
  ]
}
```

**Use Cases:**
- End-of-day stock update
- Morning opening stock check
- Price change for multiple fuel types

### Update Operating Hours

**Endpoint:** `PUT /stations/operating-hours?station_id=X`  
**Authentication:** Required (MERCHANT role)

**Request:**
```json
{
  "operating_hours": {
    "monday": "06:00-22:00",
    "tuesday": "06:00-22:00",
    "wednesday": "06:00-22:00",
    "thursday": "06:00-22:00",
    "friday": "06:00-22:00",
    "saturday": "06:00-22:00",
    "sunday": "07:00-21:00"
  }
}
```

### Update Station Information

**Endpoint:** `PUT /stations/info?station_id=X`  
**Authentication:** Required (MERCHANT role)

**Request:**
```json
{
  "name": "Shell Station - Updated Name",
  "address": "New Address",
  "latitude": 9.1500,
  "longitude": 38.7700,
  "phone_number": "+251911234568",
  "email": "newemail@shell.com"
}
```

## Public Endpoints (No Authentication)

### Get Station Profile

**Endpoint:** `GET /stations/profile?station_id=X`

Returns complete station information including:
- Basic info (name, address, location)
- Current status (open/closed)
- Available fuel types
- Operating hours
- Contact information

### Get Station Availability

**Endpoint:** `GET /stations/availability?station_id=X`

Returns real-time availability:
- Station open/closed status
- Fuel types available
- Estimated liters remaining per type
- Last update timestamp

### Find Nearby Stations

**Endpoint:** `GET /stations/nearby?latitude=X&longitude=Y&radius_km=Z&fuel_type=PETROL&is_open_only=true`

**Query Parameters:**
- `latitude`, `longitude` - Your location
- `radius_km` - Search radius (default: 10km)
- `fuel_type` - Filter by fuel type (optional)
- `is_open_only` - Only show open stations (default: true)

## Real-Time Update Workflow

### Morning Opening Routine

1. **Open Station**
   ```
   PUT /stations/status?station_id=X
   {"is_open": true}
   ```

2. **Update Stock Levels**
   ```
   PUT /stations/fuel-availability/bulk?station_id=X
   {
     "fuel_availabilities": [
       {"fuel_type": "PETROL", "is_available": true, "estimated_liters_remaining": 10000.0},
       {"fuel_type": "DIESEL", "is_available": true, "estimated_liters_remaining": 8000.0}
     ]
   }
   ```

3. **Update Prices**
   ```
   PUT /stations/fuel-availability?station_id=X
   {"fuel_type": "PETROL", "price_per_liter": 45.50}
   ```

### During the Day

**Run Out of Fuel:**
```
PUT /stations/fuel-availability?station_id=X
{"fuel_type": "DIESEL", "is_available": false}
```

**Restock:**
```
PUT /stations/fuel-availability?station_id=X
{"fuel_type": "DIESEL", "is_available": true, "estimated_liters_remaining": 5000.0}
```

**Price Change:**
```
PUT /stations/fuel-availability?station_id=X
{"fuel_type": "PETROL", "price_per_liter": 46.00}
```

### End of Day

**Close Station:**
```
PUT /stations/status?station_id=X
{"is_open": false}
```

## Features

### ✅ Real-Time Updates
- Stations can update status instantly
- Changes reflect immediately for drivers
- Last update timestamp tracked

### ✅ Per-Fuel-Type Management
- Track availability per fuel type
- Set prices per fuel type
- Monitor stock levels per type

### ✅ Bulk Operations
- Update multiple fuel types at once
- Efficient for daily stock updates

### ✅ Operating Hours
- Set weekly operating schedule
- Helps drivers know when station is open

### ✅ Location Tracking
- GPS coordinates for accurate mapping
- Nearby station search

### ✅ Contact Information
- Phone and email for customer service
- Publicly accessible

## Security

- **Authentication Required**: All update endpoints require MERCHANT role
- **Ownership Verification**: Merchants can only update their own stations
- **Idempotency**: Updates are safe to retry
- **Audit Trail**: All updates timestamped (`updated_at`, `last_status_update`)

## Best Practices

1. **Update Frequently**: Keep fuel availability current
2. **Bulk Updates**: Use bulk endpoint for efficiency
3. **Price Consistency**: Update prices when they change
4. **Status Accuracy**: Keep `is_open` status accurate
5. **Stock Monitoring**: Update `estimated_liters_remaining` regularly

## Integration with Mobile App

Stations can integrate these endpoints into their POS systems or mobile apps to:
- Automatically update status when opening/closing
- Update fuel availability from pump readings
- Sync prices from pricing systems
- Provide real-time data to drivers

