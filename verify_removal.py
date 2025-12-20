
import sys
import os
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add current dir to path
sys.path.append(os.getcwd())

from app.core.config import settings
from app.db.base import Base
from app.models import Bank, Driver, Merchant, FuelStation, Transaction, Loan
from app.services.transaction_qr_service import TransactionQrService
from app.services.loan_service import LoanService

def verify():
    print("Connecting to database (SQLite)...")
    # Use SQLite for validation to avoid local DB migration issues
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    
    # Register uuid_generate_v4 function
    from sqlalchemy import event
    
    @event.listens_for(engine, "connect")
    def connect(dbapi_connection, connection_record):
        dbapi_connection.create_function("uuid_generate_v4", 0, lambda: str(uuid.uuid4()))
        
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Auto-assign UUIDs
    @event.listens_for(SessionLocal, "before_flush")
    def receive_before_flush(session, flush_context, instances):
        for obj in session.new:
            if hasattr(obj, "id") and getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
    
    db = SessionLocal()
    
    unique_suffix = str(uuid.uuid4())[:8]

    try:
        print("Creating test data...")
        # 1. Create Bank
        bank_id = uuid.uuid4()
        bank = Bank(
            id=bank_id,
            name=f"Test Bank {unique_suffix}",
            bank_code=f"TB_{unique_suffix}"
        )
        db.add(bank)
        db.flush()
        
        # 2. Create Driver
        driver_id = uuid.uuid4()
        driver = Driver(
            id=driver_id,
            name=f"Test Driver {unique_suffix}",
            phone_number=f"+251911{unique_suffix}",
            preferred_bank_id=bank_id
        )
        db.add(driver)
        db.flush()
        
        # 3. Create Merchant & Station
        merchant = Merchant(
            id=uuid.uuid4(),
            name=f"Test Merchant {unique_suffix}"
        )
        db.add(merchant)
        db.flush()
        
        station = FuelStation(
            id=uuid.uuid4(),
            merchant_id=merchant.id,
            name=f"Test Station {unique_suffix}",
            latitude=9.0,
            longitude=38.0
        )
        db.add(station)
        db.commit()
        
        # Debug: Check if data exists
        print(f"Drivers count: {db.query(Driver).count()}")
        print(f"Driver ID from obj (pre-refresh): {driver.id}")
        
        db.refresh(driver)
        db.refresh(bank)
        db.refresh(station)
        
        print(f"Data created. Driver ID: {driver.id}, Bank ID: {bank.id}")
        
        # 4. Generate QR (Transaction Creation)
        print("Generating QR Code...")
        qr_service = TransactionQrService(db)
        qr = qr_service.generate_qr_code(
            driver_id=driver.id,
            station_id=station.id,
            authorized_amount=1000.0
        )
        
        transaction = qr.transaction
        print(f"QR Generated. Transaction ID: {transaction.id}, Status: {transaction.status}")
        assert transaction.status == "AUTHORIZED"
        assert transaction.authorized_amount == 1000.0
        
        # 5. Settle Transaction
        print("Settling Transaction...")
        settled_txn = qr_service.settle_transaction(
            transaction_id=transaction.id,
            settled_amount=950.0
        )
        print(f"Transaction Settled. Status: {settled_txn.status}, Settled Amount: {settled_txn.settled_amount}")
        assert settled_txn.status == "SETTLED"
        assert settled_txn.settled_amount == 950.0
        
        # 6. Create Loan
        print("Creating Loan...")
        loan_service = LoanService(db)
        loan = loan_service.create_loan_from_transaction(
            transaction_id=settled_txn.id,
            bank_id=bank.id
        )
        
        print(f"Loan Created. Loan ID: {loan.id}, Bank ID: {loan.bank_id}, Principal: {loan.principal_amount}")
        assert loan.bank_id == bank.id
        assert loan.principal_amount == 950.0
        assert loan.driver_id == driver.id
        
        print("VERIFICATION SUCCESSFUL!")
        
    except Exception as e:
        print(f"VERIFICATION FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify()
