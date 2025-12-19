"""
User Management API endpoints: Create users, manage roles, authentication.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.core.security import create_access_token, require_super_admin, require_bank_admin, get_current_user
from app.schemas.user import (
    CreateUserRequest,
    UserResponse,
    LoginRequest,
    LoginResponse,
    UpdateUserRoleRequest,
    UpdateUserRequest,
)
from app.models.entities import User, UserRole

router = APIRouter()


@router.post("/users", response_model=UserResponse)
def create_user(
    payload: CreateUserRequest,
    request: Request,
    current_user: User = Depends(require_super_admin),  # Only super admin can create users
    db: Session = Depends(get_db),
):
    """
    POST /users
    Create a new user (Super Admin only).
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = UserService(db)
    
    try:
        role = UserRole(payload.role.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}",
        )
    
    try:
        user = service.create_user(
            role=role,
            phone_number=payload.phone_number,
            email=payload.email,
            username=payload.username,
            password=payload.password,
            full_name=payload.full_name,
            driver_id=payload.driver_id,
            bank_id=payload.bank_id,
            merchant_id=payload.merchant_id,
            created_by_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return UserResponse(
        id=user.id,
        phone_number=user.phone_number,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        driver_id=user.driver_id,
        bank_id=user.bank_id,
        merchant_id=user.merchant_id,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat(),
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


@router.post("/users/login", response_model=LoginResponse)
def login_user(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    POST /users/login
    Login with email/username/phone and password (for admin users).
    Drivers use OTP login instead.
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = UserService(db)
    
    user = service.authenticate_user(
        phone_number=payload.phone_number,
        email=payload.email,
        username=payload.username,
        password=payload.password,
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    # Create JWT token
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role,
            "phone": user.phone_number or "",
            "email": user.email or "",
        }
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            phone_number=user.phone_number,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
        driver_id=user.driver_id,
        bank_id=user.bank_id,
        merchant_id=user.merchant_id,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at.isoformat(),
            last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        ),
    )


@router.get("/users/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    GET /users/me
    Get current authenticated user's information.
    """
    return UserResponse(
        id=current_user.id,
        phone_number=current_user.phone_number,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        role=current_user.role,
        driver_id=current_user.driver_id,
        bank_id=current_user.bank_id,
        agency_id=current_user.agency_id,
        merchant_id=current_user.merchant_id,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at.isoformat(),
        last_login_at=current_user.last_login_at.isoformat() if current_user.last_login_at else None,
    )


@router.get("/users", response_model=list[UserResponse])
def list_users(
    role: str = None,
    bank_id: int = None,
    request: Request = None,
    current_user: User = Depends(require_super_admin),  # Only super admin can list all users
    db: Session = Depends(get_db),
):
    """
    GET /users?role=BANK_ADMIN&bank_id=1
    List users (Super Admin only).
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = UserService(db)
    
    if role:
        try:
            role_enum = UserRole(role.upper())
            users = service.get_users_by_role(role_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role",
            )
    elif bank_id:
        users = service.get_bank_users(bank_id)
    else:
        # Get all users (super admin only)
        from app.models.entities import User as UserModel
        users = db.query(UserModel).all()
    
    return [
        UserResponse(
            id=user.id,
            phone_number=user.phone_number,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
        driver_id=user.driver_id,
        bank_id=user.bank_id,
        merchant_id=user.merchant_id,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at.isoformat(),
            last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        )
        for user in users
    ]


@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    payload: UpdateUserRoleRequest,
    request: Request,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    PUT /users/{user_id}/role
    Update user role (Super Admin only).
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = UserService(db)
    
    try:
        new_role = UserRole(payload.new_role.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role",
        )
    
    try:
        user = service.update_user_role(
            user_id=user_id,
            new_role=new_role,
            updated_by_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return {"trace_id": trace_id, "status": "success", "user_id": user.id, "new_role": user.role}


@router.put("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    PUT /users/{user_id}/deactivate
    Deactivate user account (Super Admin only).
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = UserService(db)
    
    try:
        user = service.deactivate_user(user_id, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return {"trace_id": trace_id, "status": "deactivated", "user_id": user.id}


@router.put("/users/{user_id}/activate")
def activate_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    PUT /users/{user_id}/activate
    Activate user account (Super Admin only).
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = UserService(db)
    
    try:
        user = service.activate_user(user_id, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return {"trace_id": trace_id, "status": "activated", "user_id": user.id}

