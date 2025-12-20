import sys
import os
import uuid
import json
from datetime import datetime

# Add current dir to path
sys.path.append(os.getcwd())

from app.db.session import SessionLocal
from app.models import Driver, FuelStation, Bank, Merchant, CreditLine, Transaction, QrCode
from app.services.transaction_qr_service import TransactionQrService

def run_verification():
    db = SessionLocal()
    try:
        print("1. Setting up test data...")
        # Create or Get Merchant
        suffix = str(uuid.uuid4())[:8]
        
        # Create Merchant
        merchant = Merchant(name=f"Test Merchant {suffix}")
        db.add(merchant)
        db.commit()
        db.refresh(merchant)
            
        # Create Bank
        bank = Bank(name=f"Test Bank {suffix}", account_number="1001")
        db.add(bank)
        db.commit()
        db.refresh(bank)
            
        # Create Station
        station = FuelStation(
            name=f"Test Station {suffix}", 
            merchant_id=merchant.id,
            address="Addis Ababa",
            latitude=9.0,
            longitude=38.0,
            phone_number="+251111111111",
            email=f"station{suffix}@test.com",
            is_open=True,
            fuel_types_available="[]",
            operating_hours="{}",
            current_fuel_price_per_liter=50.0,
            last_status_update=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(station)
        db.commit()
        db.refresh(station)
            
        # Create Driver
        driver = Driver(
            name=f"Test Driver {suffix}", 
            phone_number=f"+251{suffix}", 
            preferred_bank_id=bank.id
        )
        db.add(driver)
        db.commit()
            
        # Update Credit Line
        credit_line = db.query(CreditLine).filter(CreditLine.driver_id == driver.id, CreditLine.bank_id == bank.id).first()
        if not credit_line:
            credit_line = CreditLine(driver_id=driver.id, bank_id=bank.id, credit_limit=5000, utilized_amount=0)
            db.add(credit_line)
        else:
            credit_line.credit_limit = 5000
            credit_line.utilized_amount = 0 # Reset for test
        db.commit()
        
        print("2. Generating Pre-Auth QR...")
        service = TransactionQrService(db)
        auth_amount = 1000.0
        
        qr_record = service.generate_qr_code(
            driver_id=driver.id,
            station_id=station.id,
            authorized_amount=auth_amount
        )
        
        print(f"   QR Generated. ID: {qr_record.id}")
        
        # Verify Transaction Created
        trx = db.get(Transaction, qr_record.transaction_id)
        if not trx:
            print("FAIL: Transaction not found")
            sys.exit(1)
            
        if trx.status != "AUTHORIZED":
            print(f"FAIL: Transaction status is {trx.status}, expected AUTHORIZED")
            sys.exit(1)
            
        if trx.authorized_amount != auth_amount:
            print(f"FAIL: Auth amount mismatch. {trx.authorized_amount} vs {auth_amount}")
            sys.exit(1)
            
        print("   Transaction AUTHORIZED successfully.")
        
        # Verify Credit Held
        db.refresh(credit_line)
        if credit_line.utilized_amount != auth_amount:
            print(f"FAIL: Credit not held. Utilized: {credit_line.utilized_amount}")
            sys.exit(1)
            
        print("   Funds held successfully.")
        
        print("3. Simulating Station Scan...")
        # Get the QR payload string (simulating scan)
        qr_data_string = qr_record.qr_data
        
        scanned_trx = service.process_qr_scan(
            qr_data_json=qr_data_string,
            station_id=station.id
        )
        
        if scanned_trx.id != trx.id:
            print("FAIL: Scanned transaction mismatch")
            sys.exit(1)
            
        print("   Scan validated successfully.")
        
        print("4. Settling Transaction...")
        settle_amount = 800.0 # Less than auth
        
        settled_trx = service.settle_transaction(
            transaction_id=trx.id,
            settled_amount=settle_amount
        )
        
        if settled_trx.status != "SETTLED":
            print("FAIL: Transaction not settled")
            sys.exit(1)
            
        if settled_trx.settled_amount != settle_amount:
            print("FAIL: Settled amount mismatch")
            sys.exit(1)
            
        # Verify Credit Release
        db.refresh(credit_line)
        # Should be 800 now (auth 1000 -> settle 800, release 200)
        # Note: if previous runs left utilized amount, this might fail unless we strictly reset.
        # But we reset to 0 at start.
        if float(credit_line.utilized_amount) != settle_amount:
            print(f"FAIL: Credit not released correctly. Expected {settle_amount}, got {credit_line.utilized_amount}")
            sys.exit(1)
            
        print("   Transaction settled and credit released successfully.")
        
        print("\nSUCCESS: Pre-Auth Flow Verified.")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        if hasattr(e, 'orig'):
            print(f"Original DB Error: {e.orig}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    run_verification()
