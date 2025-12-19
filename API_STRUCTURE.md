# API Structure - Complete Endpoint List

This document lists all API endpoints organized by domain as per your specification.

## AUTH
- `POST /auth/otp/send` - Send OTP to phone number
- `POST /auth/otp/verify` - Verify OTP and get JWT token

## DRIVER
- `POST /drivers/register` - Register new driver with KYC info
- `GET /drivers/profile?driver_id=X` - Get driver profile
- `PUT /drivers/profile?driver_id=X` - Update driver profile
- `GET /drivers/credit-limit?driver_id=X` - Get credit limit and available credit
- `POST /drivers/fuel-loans?driver_id=X` - Create fuel loan request
- `GET /drivers/fuel-loans?driver_id=X` - Get all fuel loan requests
- `POST /drivers/fuel-loans/{loan_request_id}/qr?driver_id=X` - Generate QR code for approved loan
- `POST /drivers/fuel-loans/{loan_request_id}/otp/confirm?driver_id=X` - Confirm OTP for loan

## STATION (Public & Merchant)
- `GET /stations/profile?station_id=X` - Get station profile (public)
- `GET /stations/availability?station_id=X` - Get station availability (public)
- `GET /stations/nearby?latitude=X&longitude=Y&radius_km=Z&fuel_type=PETROL&is_open_only=true` - Find nearby stations (public)
- `POST /stations/scan-qr` - Station scans QR code and authorizes transaction
- `POST /stations/confirm-fuel` - Station confirms fuel pumped and settles transaction

## MERCHANT (Station Service Providers)
- `GET /merchants/stations` - Get all stations for merchant (MERCHANT auth)
- `PUT /merchants/stations/{station_id}/status` - Update station status (open/closed, price) (MERCHANT auth)
- `PUT /merchants/stations/{station_id}/fuel-types` - Update available fuel types (MERCHANT auth)
- `PUT /merchants/stations/{station_id}/fuel-availability` - Update fuel availability per type (MERCHANT auth)
- `PUT /merchants/stations/{station_id}/fuel-availability/bulk` - Bulk update fuel availability (MERCHANT auth)
- `POST /merchants/scan-qr` - Merchant scans QR code (MERCHANT auth)
- `POST /merchants/confirm-fuel` - Merchant confirms fuel pumped (MERCHANT auth)

## AGENT (Platform Employees)
- `POST /admin/agent/onboard-station` - Agent onboards a new fuel station (AGENT auth)
- `POST /admin/agent/onboard-driver` - Agent onboards a new driver (AGENT auth)

## LOANS & TRANSACTIONS
- `GET /loans/{loan_id}` - Get loan details and statement
- `POST /transactions/initiate` - Initiate transaction (alternative to QR flow)
- `POST /transactions/complete` - Complete/settle transaction

## CREDIT SCORING (AI)
- `POST /credit/score` - Calculate credit score for driver or agency
- `GET /credit/explain/{driver_id}` - Explain credit score calculation

## BANK INTEGRATION
- `POST /bank/ekyc/verify` - Bank verifies eKYC documents
- `POST /bank/pay-station` - Bank initiates payment to fuel station
- `POST /bank/auto-repay` - Bank automatically repays loan

## ADMIN
- `GET /admin/bank/loans?bank_id=X&status=ACTIVE` - Get all loans for a bank
- `GET /admin/kifiya/overview` - Get system overview (Kifiya platform)
- `POST /admin/agent/onboard-driver` - Agent onboards a driver
- `POST /admin/agent/onboard-station` - Agent onboards a fuel station

## REPORTS
- `GET /reports/summary?start_date=2024-01-01&end_date=2024-01-31&bank_id=1` - Get summary report

## Implementation Notes

### Request/Response Format
- All endpoints return JSON
- All responses include `trace_id` in header and body
- Error responses follow FastAPI standard format

### Authentication
- Most endpoints require JWT token (to be implemented)
- OTP endpoints are public
- Admin endpoints require ADMIN role

### Query Parameters
- Use query parameters for filtering (e.g., `?driver_id=X`)
- Use path parameters for resource IDs (e.g., `/loans/{loan_id}`)
- Use request body for complex data

### Status Codes
- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

## Backward Compatibility

Legacy endpoints are still available:
- `/customer/*` - Customer endpoints (legacy)
- `/bank-portal/*` - Bank portal endpoints (legacy)
- `/transactions/*` - Transaction endpoints (legacy)
- `/stations/*` - Station endpoints (legacy)

New RESTful structure is recommended for all new integrations.

