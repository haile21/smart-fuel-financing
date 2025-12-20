"""
User Service: User management, role assignment, user creation.
"""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.models import User, UserRole, Driver, Bank
from app.core.security import get_password_hash, verify_password

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """
    Service for managing users and roles.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_user(
        self,
        *,
        role: UserRole,
        phone_number: Optional[str] = None,
        email: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        full_name: Optional[str] = None,
        driver_id: Optional[int] = None,
        bank_id: Optional[int] = None,
        station_id: Optional[int] = None,
        created_by_user_id: Optional[int] = None,
    ) -> User:
        """
        Create a new user with specified role.
        """
        # Validate required fields based on role
        if role == UserRole.DRIVER:
            if not phone_number and not email:
                raise ValueError("Driver must have phone_number or email")
            if driver_id:
                driver = self.db.get(Driver, driver_id)
                if not driver:
                    raise ValueError("Driver not found")
        elif role == UserRole.BANKER:
            if not email and not username:
                raise ValueError("Bank admin must have email or username")
            if bank_id:
                bank = self.db.get(Bank, bank_id)
                if not bank:
                    raise ValueError("Bank not found")
        elif role == UserRole.SUPER_ADMIN:
            if not email and not username:
                raise ValueError("Super admin must have email or username")
        
        # Check uniqueness
        if phone_number:
            existing = self.db.query(User).filter(User.phone_number == phone_number).first()
            if existing:
                raise ValueError("Phone number already registered")
        
        if email:
            existing = self.db.query(User).filter(User.email == email).first()
            if existing:
                raise ValueError("Email already registered")
        
        if username:
            existing = self.db.query(User).filter(User.username == username).first()
            if existing:
                raise ValueError("Username already taken")
        
        # Hash password if provided
        password_hash = None
        if password:
            password_hash = get_password_hash(password)
        
        user = User(
            phone_number=phone_number,
            email=email,
            username=username,
            password_hash=password_hash,
            full_name=full_name,
            role=role.value,
            driver_id=driver_id,
            bank_id=bank_id,
            station_id=station_id,
            created_by_user_id=created_by_user_id,
            is_active=True,
            is_verified=False,  # Requires verification
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate_user(
        self,
        *,
        phone_number: Optional[str] = None,
        email: Optional[str] = None,
        username: Optional[str] = None,
        password: str,
    ) -> Optional[User]:
        """
        Authenticate user with password (for admin users).
        """
        user = None
        
        if phone_number:
            user = self.db.query(User).filter(User.phone_number == phone_number).first()
        elif email:
            user = self.db.query(User).filter(User.email == email).first()
        elif username:
            user = self.db.query(User).filter(User.username == username).first()
        
        if not user:
            return None
        
        if not user.is_active:
            return None
        
        if not user.password_hash:
            return None  # User doesn't have password set
        
        if not verify_password(password, user.password_hash):
            return None
        
        user.last_login_at = datetime.utcnow()
        self.db.commit()
        
        return user

    def update_user_role(
        self,
        user_id: uuid.UUID,
        new_role: UserRole,
        updated_by_user_id: uuid.UUID,
    ) -> User:
        """
        Update user role (only super admin can do this).
        """
        user = self.db.get(User, user_id)
        if not user:
            raise ValueError("User not found")
        
        # Only super admin can change roles
        updater = self.db.get(User, updated_by_user_id)
        if not updater or UserRole(updater.role) != UserRole.SUPER_ADMIN:
            raise ValueError("Only super admin can change user roles")
        
        user.role = new_role.value
        user.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(user)
        return user

    def deactivate_user(
        self,
        user_id: uuid.UUID,
        deactivated_by_user_id: uuid.UUID,
    ) -> User:
        """
        Deactivate a user account.
        """
        user = self.db.get(User, user_id)
        if not user:
            raise ValueError("User not found")
        
        user.is_active = False
        user.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(user)
        return user

    def activate_user(
        self,
        user_id: uuid.UUID,
        activated_by_user_id: uuid.UUID,
    ) -> User:
        """
        Activate a user account.
        """
        user = self.db.get(User, user_id)
        if not user:
            raise ValueError("User not found")
        
        user.is_active = True
        user.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID."""
        return self.db.get(User, user_id)

    def get_users_by_role(self, role: UserRole) -> list[User]:
        """Get all users with a specific role."""
        return self.db.query(User).filter(User.role == role.value).all()

    def get_bank_users(self, bank_id: uuid.UUID) -> list[User]:
        """Get all users for a specific bank."""
        return (
            self.db.query(User)
            .filter(User.bank_id == bank_id)
            .filter(User.role == UserRole.BANK_ADMIN.value)
            .all()
        )

