"""
Auth Service: Handles OTP generation/verification, JWT tokens, and role-based access control.
"""

from datetime import datetime, timedelta
from typing import Optional
import secrets
import hashlib

from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.models.entities import User, OtpCode, UserRole, Driver, Agency, Bank, Merchant
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings from config
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


class AuthService:
    """
    Authentication service handling OTP and JWT token management.
    """

    def __init__(self, db: Session):
        self.db = db

    def generate_otp(self, phone_number: str, expiry_minutes: int = 10) -> str:
        """
        Generate a 6-digit OTP and store it with expiration.
        Returns the OTP code (in production, this would be sent via SMS).
        """
        # Generate 6-digit OTP
        otp_code = f"{secrets.randbelow(1000000):06d}"
        
        # Hash the OTP before storing (optional, for extra security)
        otp_hash = hashlib.sha256(otp_code.encode()).hexdigest()
        
        expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        # Invalidate any existing unused OTPs for this phone
        self.db.query(OtpCode).filter(
            OtpCode.phone_number == phone_number,
            OtpCode.is_used == False,
        ).update({"is_used": True})
        
        # Store new OTP
        otp_record = OtpCode(
            phone_number=phone_number,
            code=otp_hash,  # Store hash, but return plain OTP for now
            expires_at=expires_at,
        )
        self.db.add(otp_record)
        self.db.commit()
        
        # In production, send OTP via SMS provider here
        # For now, return plain OTP (in production, don't return it)
        return otp_code

    def verify_otp(self, phone_number: str, otp_code: str) -> bool:
        """
        Verify OTP code. Returns True if valid, False otherwise.
        """
        otp_hash = hashlib.sha256(otp_code.encode()).hexdigest()
        
        otp_record = (
            self.db.query(OtpCode)
            .filter(
                OtpCode.phone_number == phone_number,
                OtpCode.code == otp_hash,
                OtpCode.is_used == False,
                OtpCode.expires_at > datetime.utcnow(),
            )
            .order_by(OtpCode.created_at.desc())
            .first()
        )
        
        if not otp_record:
            # Increment attempts for tracking
            latest = (
                self.db.query(OtpCode)
                .filter(OtpCode.phone_number == phone_number)
                .order_by(OtpCode.created_at.desc())
                .first()
            )
            if latest:
                latest.attempts += 1
                self.db.commit()
            return False
        
        # Mark as used
        otp_record.is_used = True
        self.db.commit()
        return True

    def create_access_token(self, user_id: int, role: str, phone_number: str) -> str:
        """
        Create JWT access token for authenticated user.
        """
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode = {
            "sub": str(user_id),
            "role": role,
            "phone": phone_number,
            "exp": expire,
        }
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[dict]:
        """
        Verify and decode JWT token. Returns payload if valid, None otherwise.
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None

    def get_or_create_user(
        self,
        phone_number: str,
        role: UserRole,
        driver_id: Optional[int] = None,
        agency_id: Optional[int] = None,
        bank_id: Optional[int] = None,
        merchant_id: Optional[int] = None,
    ) -> User:
        """
        Get existing user or create new one with specified role and entity link.
        """
        user = (
            self.db.query(User)
            .filter(User.phone_number == phone_number)
            .first()
        )
        
        if user:
            # Update last login
            user.last_login_at = datetime.utcnow()
            self.db.commit()
            return user
        
        # Create new user
        user = User(
            phone_number=phone_number,
            role=role.value,
            driver_id=driver_id,
            agency_id=agency_id,
            bank_id=bank_id,
            merchant_id=merchant_id,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def login_with_otp(self, phone_number: str, otp_code: str, role: UserRole) -> Optional[dict]:
        """
        Complete login flow: verify OTP and return JWT token.
        Returns dict with access_token and user info, or None if OTP invalid.
        """
        if not self.verify_otp(phone_number, otp_code):
            return None
        
        # Find or create user based on role
        user = None
        driver_id = None
        agency_id = None
        bank_id = None
        merchant_id = None
        
        if role == UserRole.DRIVER:
            driver = self.db.query(Driver).filter(Driver.phone_number == phone_number).first()
            if driver:
                driver_id = driver.id
        elif role == UserRole.AGENCY_ADMIN:
            # Would need to query Agency for phone_number match (extend Agency model if needed)
            pass
        elif role == UserRole.BANK_ADMIN:
            # Would need to query Bank for phone_number match (extend Bank model if needed)
            pass
        elif role == UserRole.MERCHANT_ADMIN:
            # Would need to query Merchant for phone_number match (extend Merchant model if needed)
            pass
        
        user = self.get_or_create_user(
            phone_number=phone_number,
            role=role,
            driver_id=driver_id,
            agency_id=agency_id,
            bank_id=bank_id,
            merchant_id=merchant_id,
        )
        
        access_token = self.create_access_token(user.id, user.role, user.phone_number)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "role": user.role,
        }

