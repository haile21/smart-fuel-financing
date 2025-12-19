from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    Integer,
    ForeignKey,
    Numeric,
    Boolean,
    DateTime,
    UniqueConstraint,
    Index,
    Text,
    Enum as SQLEnum,
    UUID as SQLUUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
import uuid

from app.db.base import Base


class Bank(Base):
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    account_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # Bank account for transfers
    routing_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # Bank routing/SWIFT code

    credit_lines: Mapped[list["CreditLine"]] = relationship(back_populates="bank")
    credit_line_requests: Mapped[list["CreditLineRequest"]] = relationship(back_populates="bank")
    credit_line_requests: Mapped[list["CreditLineRequest"]] = relationship(back_populates="bank")


class Driver(Base):
    """
    End customer / driver profile used by the customer app.
    """

    name: Mapped[str] = mapped_column(String(255), index=True)
    phone_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    national_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Simple vehicle profile (can later be normalized into its own table)
    car_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    car_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fuel_tank_capacity_liters: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    fuel_consumption_l_per_km: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)

    driver_license_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    plate_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Relationships
    preferred_bank_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("bank.id"), index=True, nullable=True)

    preferred_bank: Mapped[Optional[Bank]] = relationship()
    credit_lines: Mapped[list["CreditLine"]] = relationship(back_populates="driver")

    # eKYC & risk
    consent_data_sharing: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_category: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)


class Merchant(Base):
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    bank_account_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # Account to receive payments
    bank_routing_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # Routing/SWIFT code
    
    stations: Mapped[list["FuelStation"]] = relationship(back_populates="merchant")
    users: Mapped[list[User]] = relationship(back_populates="merchant")


class CreditLine(Base):
    """
    Represents credit line for a specific Driver.
    Optimistic locking via version column.
    """

    bank_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("bank.id"), index=True)
    driver_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("driver.id"), index=True, nullable=False)

    credit_limit: Mapped[float] = mapped_column(Numeric(18, 2))
    utilized_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # for optimistic locking
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    bank: Mapped[Bank] = relationship(back_populates="credit_lines")
    driver: Mapped[Driver] = relationship(back_populates="credit_lines")

    __table_args__ = (
        UniqueConstraint(
            "bank_id",
            "driver_id",
            name="uq_creditline_bank_driver",
        ),
    )


class Transaction(Base):
    """
    Double entry-like representation for a fuel transaction.
    """

    # Two-phase: AUTH then CAPTURE
    idempotency_key: Mapped[str] = mapped_column(String(64), index=True)

    funding_source_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("bank.id"), index=True)
    destination_merchant_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("merchant.id"), index=True)
    debtor_driver_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("driver.id"), index=True, nullable=False)

    authorized_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    settled_amount: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)

    status: Mapped[str] = mapped_column(String(32), index=True, default="AUTHORIZED")
    authorized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    bank: Mapped[Bank] = relationship()
    merchant: Mapped[Merchant] = relationship()
    driver: Mapped[Driver] = relationship()

    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_transaction_idempotency"),
        Index(
            "ix_transaction_debtor",
            "debtor_driver_id",
        ),
    )


class IdempotencyKey(Base):
    """
    Stores results of idempotent operations, primarily for /authorize.
    """

    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    endpoint: Mapped[str] = mapped_column(String(255))
    response_body: Mapped[str] = mapped_column(String)  # JSON string
    status_code: Mapped[int] = mapped_column(Integer)


# ========== Auth Service Models ==========

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"  # System owner
    BANK_ADMIN = "BANK_ADMIN"  # Bank administrator
    DRIVER = "DRIVER"  # Driver/end user
    AGENT = "AGENT"  # Agent (onboards fuel stations)
    MERCHANT = "MERCHANT"  # Merchant (provides fuel services)
    MERCHANT_ADMIN = "MERCHANT_ADMIN"  # Merchant/station administrator (legacy)


class User(Base):
    """
    Unified user model with role-based access control.
    Supports: SUPER_ADMIN (system owner), BANK_ADMIN, DRIVER, AGENT, MERCHANT, MERCHANT_ADMIN
    """

    # Authentication
    phone_number: Mapped[Optional[str]] = mapped_column(String(32), unique=True, index=True, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True, nullable=True)  # For admin users
    
    # Password hash (for non-OTP authentication, e.g., admin login)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Profile
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Role management
    role: Mapped[str] = mapped_column(String(32), index=True, default="DRIVER")  # UserRole enum as string
    
    # Foreign keys to specific entity types (for role-based data access)
    driver_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("driver.id"), nullable=True)
    bank_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("bank.id"), nullable=True)
    merchant_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("merchant.id"), nullable=True)
    
    # Status and metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)  # Email/phone verified
    
    # Audit fields
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=datetime.utcnow)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    driver: Mapped[Optional[Driver]] = relationship()
    bank: Mapped[Optional[Bank]] = relationship()
    merchant: Mapped[Optional["Merchant"]] = relationship(back_populates="users")
    created_by: Mapped[Optional["User"]] = relationship(remote_side="User.id")
    
    __table_args__ = (
        Index("ix_user_phone_email", "phone_number", "email"),
    )


class OtpCode(Base):
    """
    OTP codes for phone-based authentication.
    """

    phone_number: Mapped[str] = mapped_column(String(32), index=True)
    code: Mapped[str] = mapped_column(String(6))  # 6-digit OTP
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("ix_otp_phone_expires", "phone_number", "expires_at", "is_used"),
    )


# ========== KYC Service Models ==========

class KycStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class KycDocument(Base):
    """
    KYC documents uploaded by drivers.
    """

    driver_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("driver.id"), nullable=False)
    
    document_type: Mapped[str] = mapped_column(String(64))  # "NATIONAL_ID", "DRIVER_LICENSE", "VEHICLE_REGISTRATION", etc.
    document_url: Mapped[str] = mapped_column(String(512))  # S3/storage URL
    status: Mapped[str] = mapped_column(String(32), default="PENDING")  # KycStatus enum as string
    
    verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    driver: Mapped[Driver] = relationship()
    verifier: Mapped[Optional[User]] = relationship()


# ========== Station/Fuel Availability Service Models ==========

class FuelStation(Base):
    """
    Fuel stations (merchants) with location and availability info.
    Stations can register and update their status, fuel types, and availability.
    """

    merchant_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("merchant.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    
    # Location
    address: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 7), nullable=True)
    
    # Contact information
    phone_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Availability status
    is_open: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    fuel_types_available: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # JSON array: ["PETROL", "DIESEL"]
    current_fuel_price_per_liter: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    
    # Operating hours (stored as JSON: {"monday": "06:00-22:00", "tuesday": "06:00-22:00", ...})
    operating_hours: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    last_status_update: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # Last time status was updated
    
    merchant: Mapped["Merchant"] = relationship()
    fuel_availabilities: Mapped[list["FuelAvailability"]] = relationship(back_populates="station")


class FuelAvailability(Base):
    """
    Real-time fuel availability tracking per station.
    Tracks availability, stock levels, and prices per fuel type.
    """

    station_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("fuelstation.id"), index=True)
    fuel_type: Mapped[str] = mapped_column(String(32), index=True)  # "PETROL", "DIESEL", "PREMIUM_PETROL", etc.
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    estimated_liters_remaining: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    price_per_liter: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)  # Price for this specific fuel type
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    station: Mapped[FuelStation] = relationship(back_populates="fuel_availabilities")

    __table_args__ = (
        UniqueConstraint("station_id", "fuel_type", name="uq_fuel_availability_station_type"),
    )


# ========== Loan Management Service Models ==========

class LoanStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAID_OFF = "PAID_OFF"
    OVERDUE = "OVERDUE"
    DEFAULTED = "DEFAULTED"


class Loan(Base):
    """
    Represents a loan/debt created from fuel transactions.
    """

    credit_line_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("creditline.id"), index=True)
    driver_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("driver.id"), nullable=False)
    
    principal_amount: Mapped[float] = mapped_column(Numeric(18, 2))  # Total debt
    outstanding_balance: Mapped[float] = mapped_column(Numeric(18, 2))  # Remaining to pay
    interest_rate: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0)  # Annual interest rate
    
    status: Mapped[str] = mapped_column(String(32), index=True, default="ACTIVE")  # LoanStatus enum as string
    
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    paid_off_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    credit_line: Mapped[CreditLine] = relationship()
    driver: Mapped[Driver] = relationship()
    repayments: Mapped[list["LoanRepayment"]] = relationship(back_populates="loan")


class LoanRepayment(Base):
    """
    Repayment transactions against a loan.
    """

    loan_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("loan.id"), index=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    payment_method: Mapped[str] = mapped_column(String(32))  # "BANK_TRANSFER", "MOBILE_MONEY", etc.
    payment_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    repaid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    loan: Mapped[Loan] = relationship(back_populates="repayments")


# ========== Transaction & QR Service Models ==========

class QrCode(Base):
    """
    QR codes generated for fuel transactions.
    Contains bank account, amount, driver phone, and bank name for station scanning.
    """

    transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("transaction.id"), nullable=True)
    driver_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("driver.id"), index=True)
    station_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("fuelstation.id"), index=True)
    bank_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("bank.id"), index=True)
    
    qr_data: Mapped[str] = mapped_column(String(512))  # Encoded QR data (JSON with bank account, amount, phone, bank name)
    qr_image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # Generated QR image URL
    
    # QR code content fields for station scanning
    bank_account_number: Mapped[str] = mapped_column(String(64))  # Bank account for transfer
    amount: Mapped[float] = mapped_column(Numeric(18, 2))  # Amount to transfer
    driver_phone_number: Mapped[str] = mapped_column(String(32))  # Driver phone number
    bank_name: Mapped[str] = mapped_column(String(255))  # Bank name
    
    authorized_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    transaction: Mapped[Optional[Transaction]] = relationship()
    driver: Mapped[Driver] = relationship()
    station: Mapped[FuelStation] = relationship()
    bank: Mapped[Bank] = relationship()


# ========== Notification Service Models ==========

class NotificationType(str, enum.Enum):
    SMS = "SMS"
    EMAIL = "EMAIL"
    PUSH = "PUSH"
    IN_APP = "IN_APP"


class NotificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    DELIVERED = "DELIVERED"


class Notification(Base):
    """
    Notification records for SMS, email, push, in-app notifications.
    """

    recipient_type: Mapped[str] = mapped_column(String(32))  # "DRIVER", "BANK", etc.
    recipient_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), index=True)  # ID of driver/bank/etc.
    recipient_phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    recipient_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    notification_type: Mapped[str] = mapped_column(String(32), index=True)  # NotificationType enum as string
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    
    status: Mapped[str] = mapped_column(String(32), default="PENDING")  # NotificationStatus enum as string
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Provider's message ID
    
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


# ========== Payment Service Models ==========

class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class Payment(Base):
    """
    Payment records for loan repayments and other transactions.
    """

    loan_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("loan.id"), nullable=True)
    transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("transaction.id"), nullable=True)
    
    payer_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), index=True)  # Driver ID
    payer_type: Mapped[str] = mapped_column(String(32), default="DRIVER")  # "DRIVER"
    
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="ETB")
    payment_method: Mapped[str] = mapped_column(String(32))  # "BANK_TRANSFER", "MOBILE_MONEY", "CARD", etc.
    
    status: Mapped[str] = mapped_column(String(32), index=True, default="PENDING")  # PaymentStatus enum as string
    
    external_payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Payment gateway reference
    payment_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    loan: Mapped[Optional[Loan]] = relationship()
    transaction: Mapped[Optional[Transaction]] = relationship()


# ========== Credit Line Request Models ==========

class CreditLineRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class CreditLineRequest(Base):
    """
    Credit line requests from drivers that banks can approve/reject via portal.
    """

    driver_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("driver.id"), index=True)
    bank_id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("bank.id"), index=True)
    
    requested_amount: Mapped[float] = mapped_column(Numeric(18, 2))  # Amount driver wants to use now
    requested_limit: Mapped[float] = mapped_column(Numeric(18, 2))  # Credit limit requested
    
    status: Mapped[str] = mapped_column(String(32), index=True, default="PENDING")  # CreditLineRequestStatus enum
    
    # Location where request was made (near fuel station)
    station_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("fuelstation.id"), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 7), nullable=True)
    
    # Approval details
    reviewed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # If approved, link to created credit line
    credit_line_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), ForeignKey("creditline.id"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    driver: Mapped[Driver] = relationship()
    bank: Mapped[Bank] = relationship(back_populates="credit_line_requests")
    station: Mapped[Optional["FuelStation"]] = relationship()
    reviewer: Mapped[Optional[User]] = relationship()
    credit_line: Mapped[Optional["CreditLine"]] = relationship()

