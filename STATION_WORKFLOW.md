# Station Workflow: Agent Onboarding vs Merchant Updates

## Overview

The station management workflow has two distinct roles:

1. **AGENTS** - Onboard new fuel stations (employees of the platform)
2. **MERCHANTS** - Update station status, fuel availability, and operating hours (station owners/operators)

## Workflow

### Step 1: Agent Onboards Station

**Agent** (platform employee) creates a new fuel station:

**Endpoint:** `POST /admin/agent/onboard-station`  
**Authentication:** AGENT or SUPER_ADMIN role required

**Request:**
```json
{
  "merchant_id": 1,
  "name": "Shell Station - Addis Ababa",
  "address": "Bole Road, Addis Ababa",
  "latitude": 9.1450,
  "longitude": 38.7617,
  "fuel_types": ["PETROL", "DIESEL"],
  "current_price_per_liter": 45.50
}
```

**What Happens:**
- Station is created and linked to merchant
- Initial fuel types are set
- Station is marked as open by default
- Merchant can now manage this station

### Step 2: Merchant Updates Station Status

**Merchant** (station owner/operator) updates their station status in real-time:

#### Update Open/Closed Status

**Endpoint:** `PUT /merchants/stations/{station_id}/status`  
**Authentication:** MERCHANT role required (must own the station)

**Request:**
```json
{
  "is_open": false,  // Close station
  "current_price_per_liter": 46.00  // Update general price
}
```

#### Update Available Fuel Types

**Endpoint:** `PUT /merchants/stations/{station_id}/fuel-types`  
**Authentication:** MERCHANT role required

**Request:**
```json
{
  "fuel_types": ["PETROL", "DIESEL", "PREMIUM_PETROL"]
}
```

#### Update Fuel Availability (Per Type)

**Endpoint:** `PUT /merchants/stations/{station_id}/fuel-availability`  
**Authentication:** MERCHANT role required

**Request:**
```json
{
  "fuel_type": "DIESEL",
  "is_available": false,  // Mark as unavailable
  "estimated_liters_remaining": 0.0,
  "price_per_liter": 44.00
}
```

**Common Scenarios:**
- **Run out of fuel:** `{"fuel_type": "DIESEL", "is_available": false}`
- **Restock:** `{"fuel_type": "DIESEL", "is_available": true, "estimated_liters_remaining": 5000.0}`
- **Update price:** `{"fuel_type": "PETROL", "price_per_liter": 46.00}`

#### Bulk Update Fuel Availability

**Endpoint:** `PUT /merchants/stations/{station_id}/fuel-availability/bulk`  
**Authentication:** MERCHANT role required

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
    }
  ]
}
```

## Complete Merchant Endpoints

### Station Management
- `GET /merchants/stations` - Get all stations for merchant
- `PUT /merchants/stations/{id}/status` - Update open/closed status
- `PUT /merchants/stations/{id}/fuel-types` - Update available fuel types
- `PUT /merchants/stations/{id}/fuel-availability` - Update single fuel type
- `PUT /merchants/stations/{id}/fuel-availability/bulk` - Bulk update fuel types

### Transaction Processing
- `POST /merchants/scan-qr` - Scan QR code from driver
- `POST /merchants/confirm-fuel` - Confirm fuel pumped and settle transaction

## Complete Agent Endpoints

### Station Onboarding
- `POST /admin/agent/onboard-station` - Create new fuel station
- `POST /admin/agent/onboard-driver` - Onboard new driver

## Daily Workflow Example

### Morning (Merchant)
```bash
# 1. Open station
PUT /merchants/stations/1/status
{"is_open": true}

# 2. Update morning stock levels
PUT /merchants/stations/1/fuel-availability/bulk
{
  "fuel_availabilities": [
    {"fuel_type": "PETROL", "is_available": true, "estimated_liters_remaining": 10000.0, "price_per_liter": 45.50},
    {"fuel_type": "DIESEL", "is_available": true, "estimated_liters_remaining": 8000.0, "price_per_liter": 44.00}
  ]
}
```

### During Day (Merchant)
```bash
# Run out of DIESEL
PUT /merchants/stations/1/fuel-availability
{"fuel_type": "DIESEL", "is_available": false}

# Restock DIESEL
PUT /merchants/stations/1/fuel-availability
{"fuel_type": "DIESEL", "is_available": true, "estimated_liters_remaining": 5000.0}
```

### End of Day (Merchant)
```bash
# Close station
PUT /merchants/stations/1/status
{"is_open": false}
```

## Key Points

✅ **Agents onboard** - Only agents can create new stations  
✅ **Merchants update** - Merchants update status, fuel types, availability  
✅ **Real-time updates** - Changes reflect immediately for drivers  
✅ **Ownership verification** - Merchants can only update their own stations  
✅ **Bulk operations** - Efficient updates for multiple fuel types  

## Security

- **Agent endpoints**: Require AGENT or SUPER_ADMIN role
- **Merchant endpoints**: Require MERCHANT role + ownership verification
- **Public endpoints**: Station profile and availability (read-only)

