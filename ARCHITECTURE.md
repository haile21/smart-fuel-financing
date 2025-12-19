# Fuel Financing Backend - System Architecture

## Overview

This is a comprehensive FastAPI backend for a fuel financing system that acts as a clearinghouse between Banks, Drivers/Agencies, and Fuel Stations (Merchants).

## Core Services

### 1. Auth Service (`app/services/auth_service.py`)
- **OTP Management**: Generate and verify 6-digit OTPs for phone-based authentication
- **JWT Tokens**: Issue and verify JWT access tokens with role-based claims
- **User Management**: Create and manage users with roles (DRIVER, AGENCY_ADMIN, BANK_ADMIN, MERCHANT_ADMIN, SYSTEM_ADMIN)
- **Endpoints**: `/auth/request-otp`, `/auth/verify-otp`

### 2. User & KYC Service (`app/services/kyc_service.py`)
- **Document Upload**: Upload KYC documents (National ID, Driver License, Vehicle Registration)
- **Document Verification**: Approve/reject documents with reviewer tracking
- **KYC Status**: Track overall KYC status with document counts
- **Profile Management**: Update driver/agency profiles
- **Endpoints**: `/kyc/documents/upload`, `/kyc/documents`, `/kyc/status`, `/kyc/documents/{id}/verify`

### 3. Credit Engine Service (`app/services/credit_engine_service.py`)
- **Risk Scoring**: Calculate risk scores for drivers and agencies
- **Credit Limit Calculation**: Determine credit limits based on risk categories
- **Credit Line Management**: Create and manage credit lines for drivers/agencies
- **Credit Availability**: Check available credit with agency hierarchy support
- **Endpoints**: `/credit/credit-lines`, `/credit/available-credit`, `/credit/check-availability`

### 4. Loan Management Service (`app/services/loan_service.py`)
- **Loan Creation**: Create loans from settled transactions
- **Repayment Tracking**: Record repayments and update balances
- **Loan Statements**: Generate detailed loan statements with repayment history
- **Status Management**: Track loan status (ACTIVE, PAID_OFF, OVERDUE, DEFAULTED)
- **Endpoints**: `/loans/loans`, `/loans/{id}/statement`, `/loans/{id}/repay`

### 5. Transaction & QR Service (`app/services/transaction_qr_service.py`)
- **QR Code Generation**: Generate QR codes for fuel transactions with expiration
- **Authorization (Hold)**: Two-phase commit - Hold amount against credit line
- **Settlement (Capture)**: Settle transaction and release unused credit
- **Idempotency**: Ensure no duplicate transactions via idempotency keys
- **Endpoints**: `/transactions/qr/generate`, `/transactions/authorize`, `/transactions/{id}/settle`

### 6. Station/Fuel Availability Service (`app/services/station_service.py`)
- **Station Management**: Create and manage fuel stations with location data
- **Fuel Availability**: Track real-time fuel availability by type
- **Nearby Stations**: Find nearby stations (geospatial queries)
- **Price Management**: Track and update fuel prices per station
- **Endpoints**: `/stations/stations`, `/stations/{id}/availability`, `/stations/nearby`

### 7. Notification Service (`app/services/notification_service.py`)
- **SMS Notifications**: Send SMS via provider integration (stub)
- **Email Notifications**: Send emails via provider integration (stub)
- **Push Notifications**: Send push notifications via FCM/APNS (stub)
- **In-App Notifications**: Create in-app notification records
- **Notification History**: Retrieve notification history for users
- **Endpoints**: `/notifications/sms`, `/notifications/email`, `/notifications/notifications`

### 8. Payment Service (`app/services/payment_service.py`)
- **Payment Initiation**: Initiate payments for loan repayments
- **Payment Processing**: Process payments via payment gateway (stub)
- **Payment Reconciliation**: Reconcile payments from webhook callbacks
- **Payment History**: Retrieve payment history with filters
- **Endpoints**: `/payments/initiate`, `/payments/history`, `/payments/webhook/reconcile`

## Database Models

### Core Entities
- **Bank**: Financial institutions providing credit
- **Agency**: Transportation agencies with fleet management
- **Driver**: Individual drivers with vehicle information
- **Merchant**: Fuel station operators
- **FuelStation**: Physical fuel stations with location and availability
- **User**: Unified user model with role-based access
- **CreditLine**: Credit lines with optimistic locking
- **Transaction**: Double-entry transaction records
- **Loan**: Loan records created from transactions
- **LoanRepayment**: Repayment records
- **QrCode**: QR codes for fuel transactions
- **Notification**: Notification records
- **Payment**: Payment records
- **KycDocument**: KYC document records
- **OtpCode**: OTP code storage

## Key Features

### Two-Phase Commit (Hold & Capture)
1. **Authorization (Hold)**: Reserve maximum amount against credit line
2. **Settlement (Capture)**: Settle actual amount and release difference

### Agency Hierarchy
- Agencies have parent credit lines
- Drivers can be sub-accounts drawing from agency credit
- Credit checks aggregate agency-level balances

### Optimistic Locking
- CreditLine uses version column to prevent race conditions
- Concurrent fuel transactions are handled safely

### Idempotency
- All critical endpoints require idempotency keys
- Prevents duplicate transactions from retries

### Trace IDs
- Every API response includes `trace_id` in header and body
- Enables request tracing and debugging

## API Endpoints Summary

### Customer App (Driver)
- `POST /customer/onboard` - Driver registration
- `POST /customer/login/request-otp` - Request OTP
- `POST /customer/login/verify-otp` - Verify OTP and login

### Auth
- `POST /auth/request-otp` - Request OTP for any role
- `POST /auth/verify-otp` - Verify OTP and get JWT token

### KYC
- `POST /kyc/documents/upload` - Upload KYC document
- `GET /kyc/documents` - Get documents
- `GET /kyc/status` - Get KYC status
- `POST /kyc/documents/{id}/verify` - Verify document

### Credit
- `POST /credit/credit-lines` - Create credit line
- `GET /credit/available-credit` - Get available credit
- `GET /credit/check-availability` - Check credit availability

### Loans
- `GET /loans/loans` - Get loans
- `GET /loans/{id}/statement` - Get loan statement
- `POST /loans/{id}/repay` - Record repayment

### Transactions
- `POST /transactions/qr/generate` - Generate QR code
- `POST /transactions/authorize` - Authorize transaction (Hold)
- `POST /transactions/{id}/settle` - Settle transaction (Capture)

### Stations
- `POST /stations/stations` - Create station
- `GET /stations/{id}/availability` - Get station availability
- `PUT /stations/{id}/fuel-availability` - Update fuel availability
- `GET /stations/nearby` - Find nearby stations

### Notifications
- `POST /notifications/sms` - Send SMS
- `POST /notifications/email` - Send email
- `GET /notifications/notifications` - Get notifications

### Payments
- `POST /payments/initiate` - Initiate payment
- `GET /payments/history` - Get payment history
- `POST /payments/webhook/reconcile` - Reconcile payment webhook

## Setup & Configuration

### Environment Variables
Create a `.env` file:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/fuel_finance
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

### Database Migration
```bash
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### Run Server
```bash
uvicorn app.main:app --reload
```

## Production Considerations

1. **SMS Provider**: Integrate real SMS provider (Twilio, AWS SNS, etc.)
2. **Email Provider**: Integrate email service (SendGrid, AWS SES, etc.)
3. **Push Notifications**: Integrate FCM/APNS for mobile push
4. **Payment Gateway**: Integrate real payment gateway (Stripe, PayPal, etc.)
5. **File Storage**: Use S3 or similar for document storage
6. **Geospatial**: Use PostGIS for proper geospatial queries
7. **Caching**: Add Redis for OTP caching and rate limiting
8. **Monitoring**: Add logging, metrics, and APM
9. **Security**: Add rate limiting, CORS, and security headers
10. **Testing**: Add comprehensive unit and integration tests

