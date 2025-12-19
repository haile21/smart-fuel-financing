# Role Management System

## Overview

The system implements role-based access control (RBAC) with three main roles:

1. **SUPER_ADMIN** - System owner with full access
2. **BANK_ADMIN** - Bank administrator with bank-specific access
3. **DRIVER** - End user/driver with limited access

Additional roles (for future use):
- **AGENCY_ADMIN** - Agency administrator
- **MERCHANT_ADMIN** - Merchant/station administrator

## User Model

The `User` entity supports:
- Multiple authentication methods (phone/OTP, email/password, username/password)
- Role-based access control
- Links to specific entities (driver, bank, agency, merchant)
- Account status management (active/inactive, verified/unverified)
- Audit trail (created_by, created_at, updated_at, last_login_at)

## Authentication Methods

### 1. OTP Authentication (Drivers)
- `POST /auth/otp/send` - Send OTP to phone number
- `POST /auth/otp/verify` - Verify OTP and get JWT token
- Used primarily by drivers

### 2. Password Authentication (Admins)
- `POST /users/login` - Login with email/username/phone and password
- Used by super admins and bank admins
- Requires password hash stored in database

## Role Permissions

### SUPER_ADMIN
- ✅ Create/update/delete users
- ✅ Change user roles
- ✅ Activate/deactivate users
- ✅ Access all system data
- ✅ Onboard drivers and stations
- ✅ View system overview
- ✅ Full access to all endpoints

### BANK_ADMIN
- ✅ View loans for their bank
- ✅ Approve/reject credit line requests
- ✅ Verify eKYC documents
- ✅ Initiate payments to stations
- ✅ Auto-repay loans
- ❌ Cannot create users
- ❌ Cannot change roles
- ❌ Cannot access other banks' data

### DRIVER
- ✅ Register and update profile
- ✅ View own credit limit
- ✅ Create fuel loan requests
- ✅ Generate QR codes
- ✅ View own loans
- ❌ Cannot access admin endpoints
- ❌ Cannot access other drivers' data

## User Management Endpoints

### Create User (Super Admin Only)
```
POST /users
Authorization: Bearer <super_admin_token>
Body: {
  "role": "BANK_ADMIN",
  "email": "admin@bank.com",
  "username": "bankadmin",
  "password": "secure_password",
  "full_name": "Bank Admin",
  "bank_id": 1
}
```

### Login (Password-based)
```
POST /users/login
Body: {
  "email": "admin@bank.com",
  "password": "secure_password"
}
```

### Get Current User
```
GET /users/me
Authorization: Bearer <token>
```

### List Users (Super Admin Only)
```
GET /users?role=BANK_ADMIN&bank_id=1
Authorization: Bearer <super_admin_token>
```

### Update User Role (Super Admin Only)
```
PUT /users/{user_id}/role
Authorization: Bearer <super_admin_token>
Body: {
  "new_role": "BANK_ADMIN"
}
```

### Activate/Deactivate User (Super Admin Only)
```
PUT /users/{user_id}/activate
PUT /users/{user_id}/deactivate
Authorization: Bearer <super_admin_token>
```

## Using Role-Based Access Control

### In Endpoints

```python
from app.core.security import require_super_admin, require_bank_admin, require_driver, get_current_user

# Require super admin
@router.get("/admin/endpoint")
def admin_endpoint(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    # Only super admin can access
    pass

# Require bank admin or super admin
@router.get("/bank/loans")
def bank_loans(
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db),
):
    # Bank admin or super admin can access
    pass

# Require any authenticated user
@router.get("/profile")
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Any authenticated user can access
    pass
```

### Custom Role Requirements

```python
from app.core.security import require_role
from app.models.entities import UserRole

# Require specific roles
@router.get("/endpoint")
def custom_endpoint(
    current_user: User = Depends(require_role(UserRole.BANK_ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    pass
```

## Security Features

1. **JWT Tokens**: All authenticated endpoints require JWT token in Authorization header
2. **Password Hashing**: Passwords are hashed using bcrypt
3. **Role Validation**: Roles are validated on every request
4. **Account Status**: Inactive users cannot authenticate
5. **Audit Trail**: All user actions are tracked (created_by, timestamps)

## Initial Setup

### Create First Super Admin

You'll need to create the first super admin user directly in the database or via a migration script:

```python
from app.services.user_service import UserService
from app.models.entities import UserRole

# In a setup script or migration
service = UserService(db)
super_admin = service.create_user(
    role=UserRole.SUPER_ADMIN,
    email="admin@system.com",
    username="superadmin",
    password="secure_password",
    full_name="System Administrator",
    created_by_user_id=None,  # First user
)
```

## Best Practices

1. **Never expose passwords**: Always hash passwords before storing
2. **Use HTTPS**: Always use HTTPS in production
3. **Token expiration**: Tokens expire after configured time (default: 7 days)
4. **Role hierarchy**: SUPER_ADMIN > BANK_ADMIN > DRIVER
5. **Principle of least privilege**: Assign minimum required role
6. **Regular audits**: Review user roles and permissions regularly

## Example Flow

### Creating a Bank Admin

1. Super admin logs in: `POST /users/login`
2. Super admin creates bank admin: `POST /users` with role=BANK_ADMIN
3. Bank admin receives credentials (email/password)
4. Bank admin logs in: `POST /users/login`
5. Bank admin can now access bank-specific endpoints

### Driver Registration

1. Driver registers: `POST /drivers/register`
2. System creates User with role=DRIVER automatically
3. Driver uses OTP login: `POST /auth/otp/send` → `POST /auth/otp/verify`
4. Driver receives JWT token
5. Driver can access driver-specific endpoints

