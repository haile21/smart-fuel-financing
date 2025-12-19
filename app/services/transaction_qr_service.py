"""
Transaction & QR Service: Handles QR code generation, scanning, and transaction processing.
Updated to include bank account, amount, driver phone, and bank name in QR code.
"""

from datetime import datetime, timedelta
from typing import Optional
import uuid
import qrcode
import io
import base64
import json

from sqlalchemy.orm import Session

from app.models.entities import (
    Transaction,
    QrCode,
    Driver,
    FuelStation,
    CreditLine,
    Bank,
    Merchant,
)
from app.services.credit_engine_service import CreditEngineService


class TransactionQrService:
    """
    Service for QR code generation and transaction processing.
    QR codes contain: bank account, amount, driver phone number, bank name.
    """

    def __init__(self, db: Session):
        self.db = db
        self.credit_engine = CreditEngineService(db)

    def generate_qr_code(
        self,
        driver_id: int,
        station_id: int,
        authorized_amount: float,
        expiry_minutes: int = 30,
    ) -> QrCode:
        """
        Generate a QR code for a fuel transaction authorization.
        QR contains: bank account, amount, driver phone, bank name.
        """
        driver = self.db.get(Driver, driver_id)
        if not driver:
            raise ValueError("Driver not found")
        
        if not driver.preferred_bank_id:
            raise ValueError("Driver has no preferred bank")
        
        station = self.db.get(FuelStation, station_id)
        if not station:
            raise ValueError("Station not found")
        
        bank = self.db.get(Bank, driver.preferred_bank_id)
        if not bank:
            raise ValueError("Bank not found")
        
        if not bank.account_number:
            raise ValueError("Bank account number not configured")
        
        # Check credit availability
        is_available, available = self.credit_engine.check_credit_availability(
            driver_id=driver_id,
            requested_amount=authorized_amount,
        )
        
        if not is_available:
            raise ValueError(f"Insufficient credit. Available: {available}")
        
        # Get credit line
        credit_line = (
            self.db.query(CreditLine)
            .filter(
                CreditLine.driver_id == driver.id,
                CreditLine.bank_id == bank.id,
            )
            .first()
        )
        
        if not credit_line:
            raise ValueError("Credit line not found")
        
        # Prepare QR data with bank account, amount, phone, bank name
        qr_payload = {
            "bank_account": bank.account_number,
            "amount": authorized_amount,
            "driver_phone": driver.phone_number,
            "bank_name": bank.name,
            "qr_id": str(uuid.uuid4()),
            "driver_id": driver_id,
            "station_id": station_id,
            "expires_at": (datetime.utcnow() + timedelta(minutes=expiry_minutes)).isoformat(),
        }
        
        qr_data_str = json.dumps(qr_payload)
        
        # Create QR code image
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data_str)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        
        # Encode as base64 (in production, upload to S3 and store URL)
        qr_image_base64 = base64.b64encode(img_buffer.read()).decode()
        qr_image_url = f"data:image/png;base64,{qr_image_base64}"
        
        expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        qr_record = QrCode(
            driver_id=driver_id,
            station_id=station_id,
            bank_id=bank.id,
            qr_data=qr_data_str,
            qr_image_url=qr_image_url,
            bank_account_number=bank.account_number,
            amount=authorized_amount,
            driver_phone_number=driver.phone_number,
            bank_name=bank.name,
            authorized_amount=authorized_amount,
            expires_at=expires_at,
        )
        self.db.add(qr_record)
        self.db.commit()
        self.db.refresh(qr_record)
        
        return qr_record

    def scan_and_authorize(
        self,
        qr_id: str,
        idempotency_key: str,
    ) -> Transaction:
        """
        Scan QR code and create authorization transaction.
        This is the "Hold" phase of two-phase commit.
        Station scans QR code and initiates payment transfer.
        """
        # Find QR code by parsing qr_data or by qr_id
        qr_records = (
            self.db.query(QrCode)
            .filter(QrCode.qr_data.contains(qr_id))
            .filter(QrCode.is_used == False)
            .filter(QrCode.expires_at > datetime.utcnow())
            .all()
        )
        
        qr_record = None
        for qr in qr_records:
            try:
                qr_data = json.loads(qr.qr_data)
                if qr_data.get("qr_id") == qr_id:
                    qr_record = qr
                    break
            except:
                continue
        
        if not qr_record:
            raise ValueError("Invalid or expired QR code")
        
        # Check idempotency
        existing = (
            self.db.query(Transaction)
            .filter(Transaction.idempotency_key == idempotency_key)
            .first()
        )
        if existing:
            return existing
        
        driver = self.db.get(Driver, qr_record.driver_id)
        station = self.db.get(FuelStation, qr_record.station_id)
        bank = self.db.get(Bank, qr_record.bank_id)
        
        if not driver or not station or not bank:
            raise ValueError("Driver, station, or bank not found")
        
        # Get credit line
        credit_line = (
            self.db.query(CreditLine)
            .filter(
                CreditLine.driver_id == driver.id,
                CreditLine.bank_id == bank.id,
            )
            .first()
        )
        
        if not credit_line:
            raise ValueError("Credit line not found")
        
        # Check credit with optimistic locking
        if credit_line.utilized_amount + qr_record.authorized_amount > credit_line.credit_limit:
            raise ValueError("Insufficient credit limit")
        
        # Get merchant for station
        merchant = self.db.get(Merchant, station.merchant_id)
        if not merchant:
            raise ValueError("Merchant not found")
        
        # Create authorization transaction
        transaction = Transaction(
            idempotency_key=idempotency_key,
            funding_source_id=bank.id,
            destination_merchant_id=merchant.id,
            debtor_driver_id=driver.id,
            debtor_agency_id=driver.agency_id,
            authorized_amount=qr_record.authorized_amount,
            settled_amount=None,
            status="AUTHORIZED",
        )
        self.db.add(transaction)
        
        # Update credit line (with optimistic locking)
        credit_line.utilized_amount += qr_record.authorized_amount
        credit_line.version += 1
        
        # Mark QR as used
        qr_record.is_used = True
        qr_record.used_at = datetime.utcnow()
        qr_record.transaction_id = transaction.id
        
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def settle_transaction(
        self,
        transaction_id: int,
        settled_amount: float,
    ) -> Transaction:
        """
        Settle a transaction (Capture phase).
        Releases the difference between authorized and settled amounts.
        Payment is transferred from bank account to merchant account.
        """
        transaction = self.db.get(Transaction, transaction_id)
        if not transaction:
            raise ValueError("Transaction not found")
        
        if transaction.status != "AUTHORIZED":
            raise ValueError(f"Transaction already {transaction.status}")
        
        if settled_amount > transaction.authorized_amount:
            raise ValueError("Settled amount cannot exceed authorized amount")
        
        # Get credit line
        driver = self.db.get(Driver, transaction.debtor_driver_id)
        if not driver:
            raise ValueError("Driver not found")
        
        credit_line = (
            self.db.query(CreditLine)
            .filter(
                CreditLine.driver_id == driver.id,
                CreditLine.bank_id == transaction.funding_source_id,
            )
            .first()
        )
        
        if not credit_line:
            raise ValueError("Credit line not found")
        
        # Release difference back to credit limit
        difference = transaction.authorized_amount - settled_amount
        credit_line.utilized_amount = max(0.0, credit_line.utilized_amount - difference)
        
        # Update transaction
        transaction.settled_amount = settled_amount
        transaction.status = "SETTLED"
        transaction.settled_at = datetime.utcnow()
        
        # In production, initiate bank transfer here:
        # Transfer settled_amount from bank.account_number to merchant.bank_account
        
        self.db.commit()
        self.db.refresh(transaction)
        return transaction
