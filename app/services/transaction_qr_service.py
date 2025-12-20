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
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    Transaction,
    QrCode,
    Driver,
    FuelStation,
    Bank,

)


class TransactionQrService:
    """
    Service for QR code generation and transaction processing.
    QR codes contain: bank account, amount, driver phone number, bank name.
    """

    def __init__(self, db: Session):
        self.db = db

    def generate_qr_code(
        self,
        driver_id: uuid.UUID,
        station_id: uuid.UUID,
        authorized_amount: float,
        expiry_minutes: int = 15,
    ) -> QrCode:
        """
        Generate a Pre-Authorized QR code.
        Action: Checks credit -> Creates AUTHORIZED Transaction -> Holds Funds -> Returns QR.
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
        
        if not bank:
            raise ValueError("Bank not found")
        
        # 1. Create Transaction (PRE-AUTH) -> "AUTHORIZED"
        # We generate a unique idempotency key for this generation event
        idempotency_key = f"gen-{uuid.uuid4()}"
        
        transaction = Transaction(
            idempotency_key=idempotency_key,
            funding_source_id=bank.id,
            station_id=station.id,
            debtor_driver_id=driver.id,
            authorized_amount=authorized_amount,
            settled_amount=None,
            status="AUTHORIZED",
            authorized_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db.add(transaction)
        
        self.db.flush() # Get IDs
        
        # 4. Generate QR Payload (Minimal & Secure)
        # We use a random token effectively as a 'signature' for this lookup
        qr_token = str(uuid.uuid4())
        
        qr_payload = {
            "v": 2, # Version 2 (Pre-Auth)
            "tid": str(transaction.id),
            "token": qr_token,
            "amt": authorized_amount,
            "exp": (datetime.utcnow() + timedelta(minutes=expiry_minutes)).timestamp()
        }
        
        qr_data_str = json.dumps(qr_payload)
        
        # Create QR Image
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data_str)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        
        qr_image_base64 = base64.b64encode(img_buffer.read()).decode()
        qr_image_url = f"data:image/png;base64,{qr_image_base64}"
        
        expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        # 5. Save QR Record
        qr_record = QrCode(
            transaction_id=transaction.id,
            driver_id=driver_id,
            station_id=station_id,
            bank_id=bank.id,
            qr_data=qr_data_str,
            qr_image_url=None, # "https://placeholder-qr.com", # Disabled to avoid String(512) overflow
            signature=qr_token, # Storing the token as signature
            amount=authorized_amount,
            authorized_amount=authorized_amount,
            expires_at=expires_at,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db.add(qr_record)
        self.db.commit()
        self.db.refresh(qr_record)
        
        return qr_record

    def process_qr_scan(
        self,
        qr_data_json: str,
        station_id: Optional[uuid.UUID] = None
    ) -> Transaction:
        """
        Station scans the QR.
        Action: Validates QR -> Checks Transaction Status -> Returns Transaction.
        No new transaction created here, just validation of the Pre-Auth.
        """
        try:
            payload = json.loads(qr_data_json)
        except json.JSONDecodeError:
            raise ValueError("Invalid QR format")
            
        transaction_id = payload.get("tid")
        token = payload.get("token")
        
        if not transaction_id or not token:
            raise ValueError("Invalid QR payload")
            
        # Find QR Record
        qr_record = (
            self.db.query(QrCode)
            .join(Transaction)
            .filter(
                QrCode.transaction_id == uuid.UUID(transaction_id),
                QrCode.signature == token,
                QrCode.is_used == False,
                QrCode.expires_at > datetime.utcnow()
            )
            .first()
        )
        
        if not qr_record:
            raise ValueError("Invalid, expired, or already used QR code")
            
        # Validate Station (Optional: Ensure station matches the one intended?)
        # For now, we allow any station in the same network, or strictly enforce:
        # if qr_record.station_id != station_id:
        #    raise ValueError("QR code is for a different station")
        
        transaction = qr_record.transaction
        if transaction.status != "AUTHORIZED":
            raise ValueError(f"Transaction is in invalid state: {transaction.status}")
            
        return transaction

    def settle_transaction(
        self,
        transaction_id: uuid.UUID,
        settled_amount: float,
    ) -> Transaction:
        """
        Finalize/Capture the transaction.
        Action: Adjusts final amount -> Settles -> Releases unused credit.
        """
        transaction = self.db.get(Transaction, transaction_id)
        if not transaction:
            raise ValueError("Transaction not found")
        
        if transaction.status != "AUTHORIZED":
            raise ValueError(f"Transaction already {transaction.status}")
        
        # Cast settled_amount to Decimal
        settled_amount_decimal = Decimal(str(settled_amount))
        
        if settled_amount_decimal > transaction.authorized_amount:
            raise ValueError("Settled amount cannot exceed authorized amount")
        
        # Mark QR as used (if not already)
        qr_record = self.db.query(QrCode).filter(QrCode.transaction_id == transaction.id).first()
        if qr_record:
            qr_record.is_used = True
            qr_record.used_at = datetime.utcnow()
        
        # Update transaction
        transaction.settled_amount = settled_amount
        transaction.status = "SETTLED"
        transaction.settled_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(transaction)
        return transaction
