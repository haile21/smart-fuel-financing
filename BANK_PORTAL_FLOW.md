# Bank Portal & Credit Request Flow

## Overview

This document describes the complete flow for drivers requesting credit lines from banks, bank approval/rejection via portal, and QR code generation for fuel transactions.

## Flow Diagram

```
Driver App (Near Fuel Station)
    ↓
1. Create Credit Request
    POST /customer/credit-request
    ↓
Bank Portal
    ↓
2. View Pending Requests
    GET /bank-portal/requests?bank_id=X
    ↓
3. Approve/Reject Request
    POST /bank-portal/requests/{id}/approve
    POST /bank-portal/requests/{id}/reject
    ↓
Driver App (After Approval)
    ↓
4. Generate QR Code
    POST /transactions/qr/generate
    ↓
QR Code Contains:
    - Bank Account Number
    - Amount
    - Driver Phone Number
    - Bank Name
    ↓
Fuel Station App
    ↓
5. Scan QR Code
    POST /transactions/authorize
    ↓
6. Payment Transfer
    (Bank Account → Merchant Account)
    ↓
7. Settle Transaction
    POST /transactions/{id}/settle
```

## Detailed Steps

### Step 1: Driver Creates Credit Request

**Endpoint:** `POST /customer/credit-request`

**Request:**
```json
{
  "driver_id": 1,
  "bank_id": 1,
  "requested_amount": 500.0,
  "requested_limit": 10000.0,
  "station_id": 1,
  "latitude": 9.1450,
  "longitude": 38.7617
}
```

**Response:**
```json
{
  "id": 1,
  "driver_id": 1,
  "bank_id": 1,
  "requested_amount": 500.0,
  "requested_limit": 10000.0,
  "status": "PENDING",
  "created_at": "2024-01-01T10:00:00Z"
}
```

### Step 2: Bank Views Pending Requests

**Endpoint:** `GET /bank-portal/requests?bank_id=1`

**Response:**
```json
[
  {
    "id": 1,
    "driver_id": 1,
    "driver_name": "John Doe",
    "driver_phone": "+251911234567",
    "bank_id": 1,
    "bank_name": "Coop Bank",
    "requested_amount": 500.0,
    "requested_limit": 10000.0,
    "status": "PENDING",
    "station_id": 1,
    "station_name": "Shell Station",
    "latitude": 9.1450,
    "longitude": 38.7617,
    "created_at": "2024-01-01T10:00:00Z"
  }
]
```

### Step 3: Bank Approves Request

**Endpoint:** `POST /bank-portal/requests/1/approve`

**Request:**
```json
{
  "approved_limit": 10000.0  // Optional, defaults to requested_limit
}
```

**What Happens:**
1. Credit line is automatically created for the driver
2. Request status changes to "APPROVED"
3. Driver can now generate QR codes

### Step 4: Driver Generates QR Code (After Approval)

**Endpoint:** `POST /transactions/qr/generate?driver_id=1`

**Request:**
```json
{
  "station_id": 1,
  "authorized_amount": 500.0,
  "expiry_minutes": 30
}
```

**Response:**
```json
{
  "id": 1,
  "qr_data": "{\"bank_account\":\"1234567890\",\"amount\":500.0,\"driver_phone\":\"+251911234567\",\"bank_name\":\"Coop Bank\",\"qr_id\":\"uuid\",...}",
  "qr_image_url": "data:image/png;base64,...",
  "bank_account_number": "1234567890",
  "amount": 500.0,
  "driver_phone_number": "+251911234567",
  "bank_name": "Coop Bank",
  "authorized_amount": 500.0,
  "expires_at": "2024-01-01T10:30:00Z"
}
```

**QR Code Content:**
The QR code contains JSON with:
- `bank_account`: Bank account number for transfer
- `amount`: Amount to transfer
- `driver_phone`: Driver's phone number
- `bank_name`: Bank name
- `qr_id`: Unique QR identifier
- `driver_id`: Driver ID
- `station_id`: Station ID
- `expires_at`: Expiration timestamp

### Step 5: Fuel Station Scans QR Code

**Endpoint:** `POST /transactions/authorize`

**Request:**
```json
{
  "qr_id": "uuid-from-qr-code",
  "idempotency_key": "unique-key-from-station-pos"
}
```

**What Happens:**
1. QR code is validated (not expired, not used)
2. Credit availability is checked
3. Authorization transaction is created (Hold phase)
4. Credit line utilized amount is updated
5. QR code is marked as used

### Step 6: Payment Transfer

When the station scans the QR code, the payment transfer should be initiated:
- **From:** Bank account (from QR code: `bank_account`)
- **To:** Merchant bank account (`merchant.bank_account_number`)
- **Amount:** Amount from QR code

**Note:** In production, this would integrate with a payment gateway or bank API.

### Step 7: Settle Transaction

**Endpoint:** `POST /transactions/{transaction_id}/settle`

**Request:**
```json
{
  "settled_amount": 450.0  // Actual amount pumped (may be less than authorized)
}
```

**What Happens:**
1. Transaction status changes to "SETTLED"
2. Difference between authorized and settled is released back to credit limit
3. Loan is created from settled transaction
4. Payment is recorded

## Database Models

### CreditLineRequest
- `driver_id`: Driver making request
- `bank_id`: Bank being requested
- `requested_amount`: Amount driver wants to use now
- `requested_limit`: Credit limit requested
- `status`: PENDING, APPROVED, REJECTED
- `station_id`: Station where request was made
- `latitude`, `longitude`: Location coordinates
- `reviewed_by_user_id`: Bank admin who reviewed
- `credit_line_id`: Link to created credit line (if approved)

### QrCode (Updated)
- `bank_account_number`: Bank account for transfer
- `amount`: Amount to transfer
- `driver_phone_number`: Driver phone
- `bank_name`: Bank name
- `qr_data`: JSON string with all QR info

### Bank (Updated)
- `account_number`: Bank account for transfers
- `routing_number`: Bank routing/SWIFT code

### Merchant (Updated)
- `bank_account_number`: Account to receive payments
- `bank_routing_number`: Routing/SWIFT code

## Key Features

1. **Credit Line Auto-Creation**: When driver is onboarded, a credit line is automatically created (but may need bank approval for activation)

2. **Request-Based Approval**: Drivers must request credit lines, banks approve/reject via portal

3. **QR Code Contains Payment Info**: QR code includes all necessary info for station to initiate payment transfer

4. **Two-Phase Commit**: Authorization (Hold) → Settlement (Capture) with credit release

5. **Location Tracking**: Requests include location data (near fuel station)

## API Endpoints Summary

### Customer Endpoints
- `POST /customer/credit-request` - Create credit request
- `GET /customer/credit-requests?driver_id=X` - Get my requests
- `POST /transactions/qr/generate?driver_id=X` - Generate QR code (after approval)

### Bank Portal Endpoints
- `GET /bank-portal/requests?bank_id=X` - View pending requests
- `GET /bank-portal/requests/{id}` - Get request details
- `POST /bank-portal/requests/{id}/approve` - Approve request
- `POST /bank-portal/requests/{id}/reject` - Reject request

### Station Endpoints
- `POST /transactions/authorize` - Scan QR and authorize
- `POST /transactions/{id}/settle` - Settle transaction

## Security Considerations

1. **JWT Authentication**: Bank portal endpoints should require JWT tokens with BANK_ADMIN role
2. **Idempotency**: All transaction endpoints use idempotency keys
3. **QR Expiration**: QR codes expire after specified minutes
4. **Credit Checks**: Credit availability is checked before authorization
5. **Optimistic Locking**: Credit line updates use version column to prevent race conditions

