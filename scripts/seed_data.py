
import sys
import os
import uuid
import random
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Add current dir to path
sys.path.append(os.getcwd())

from app.core.config import settings
from app.db.base import Base
from app.models.user import User, UserRole
from app.models.bank import Bank

from app.models.station import FuelStation, FuelAvailability
from app.models.driver import Driver

# Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def seed_db():
    print(f"Seeding database: {settings.database_url}")
    
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if already seeded (simple check)
        if db.query(User).filter(User.role == UserRole.SUPER_ADMIN).first():
            print("Database appears to be seeded. Skipping seed.")
            return

        print("Creating Super Admin...")
        super_admin = User(
            id=uuid.uuid4(),
            email="admin@smartfuel.com",
            phone_number="+251911000000",
            username="superadmin",
            password_hash=get_password_hash("admin123"),
            full_name="System Administrator",
            role=UserRole.SUPER_ADMIN,
            is_active=True,
            is_verified=True
        )
        db.add(super_admin)
        
        print("Creating Banks...")
        # 1. Commercial Bank of Ethiopia
        cbe = Bank(
            id=uuid.uuid4(),
            name="Commercial Bank of Ethiopia",
            bank_code="CBE",
            account_number="1000000001"
        )
        db.add(cbe)
        
        # 2. Dashen Bank
        dashen = Bank(
            id=uuid.uuid4(),
            name="Dashen Bank",
            bank_code="DASHEN",
            account_number="2000000002"
        )
        db.add(dashen)
        
        # 3. Cooperative Bank of Oromia
        coop = Bank(
            id=uuid.uuid4(),
            name="Cooperative Bank of Oromia",
            bank_code="COOP",
            account_number="3000000003"
        )
        db.add(coop)

        # 4. Wegagen Bank
        wegagen = Bank(
            id=uuid.uuid4(),
            name="Wegagen Bank",
            bank_code="WEGAGEN",
            account_number="4000000004"
        )
        db.add(wegagen)

        # 5. Bunna Bank
        bunna = Bank(
            id=uuid.uuid4(),
            name="Bunna Bank",
            bank_code="BUNNA",
            account_number="5000000005"
        )
        db.add(bunna)

        # 6. Enat Bank
        enat = Bank(
            id=uuid.uuid4(),
            name="Enat Bank",
            bank_code="ENAT",
            account_number="6000000006"
        )
        db.add(enat)
        db.flush() # to get IDs
        
        print("Creating Bank Admins...")
        cbe_admin = User(
            id=uuid.uuid4(),
            email="admin@cbe.com.et",
            phone_number="+251911111111",
            username="cbe_admin",
            password_hash=get_password_hash("cbe123"),
            full_name="CBE Administrator",
            role=UserRole.BANKER,
            bank_id=cbe.id,
            is_active=True,
            is_verified=True
        )
        db.add(cbe_admin)
        
        dashen_admin = User(
            id=uuid.uuid4(),
            email="admin@dashen.com.et",
            phone_number="+251911222222",
            username="dashen_admin",
            password_hash=get_password_hash("dashen123"),
            full_name="Dashen Administrator",
            role=UserRole.BANKER,
            bank_id=dashen.id,
            is_active=True,
            is_verified=True
        )
        db.add(dashen_admin)

        coop_admin = User(
            id=uuid.uuid4(),
            email="admin@coopbank.com.et",
            phone_number="+251911777777",
            username="coop_admin",
            password_hash=get_password_hash("coop123"),
            full_name="Coop Administrator",
            role=UserRole.BANKER,
            bank_id=coop.id,
            is_active=True,
            is_verified=True
        )
        db.add(coop_admin)

        wegagen_admin = User(
            id=uuid.uuid4(),
            email="admin@wegagen.com.et",
            phone_number="+251911888888",
            username="wegagen_admin",
            password_hash=get_password_hash("wegagen123"),
            full_name="Wegagen Administrator",
            role=UserRole.BANKER,
            bank_id=wegagen.id,
            is_active=True,
            is_verified=True
        )
        db.add(wegagen_admin)

        bunna_admin = User(
            id=uuid.uuid4(),
            email="admin@bunnabank.com.et",
            phone_number="+251911999999",
            username="bunna_admin",
            password_hash=get_password_hash("bunna123"),
            full_name="Bunna Administrator",
            role=UserRole.BANKER,
            bank_id=bunna.id,
            is_active=True,
            is_verified=True
        )
        db.add(bunna_admin)

        enat_admin = User(
            id=uuid.uuid4(),
            email="admin@enatbank.com.et",
            phone_number="+251911010101",
            username="enat_admin",
            password_hash=get_password_hash("enat123"),
            full_name="Enat Administrator",
            role=UserRole.BANKER,
            bank_id=enat.id,
            is_active=True,
            is_verified=True
        )
        db.add(enat_admin)

        print("Creating Fuel Stations...")
        stations = []
        # Total Bole
        s1 = FuelStation(
            id=uuid.uuid4(),
            name="Total Bole",
            bank_account_number="100011112222",
            bank_routing_number="CBE-001",
            address="Bole Road, Addis Ababa",
            latitude=9.0100,
            longitude=38.7600,
            is_open=True,
            fuel_types_available=json.dumps(["Diesel", "Benzene"]),
            current_fuel_price_per_liter=75.00 # Base price
        )
        stations.append(s1)
        
        # Total Kazanchis
        s2 = FuelStation(
            id=uuid.uuid4(),
            name="Total Kazanchis",
            bank_account_number="100011112222", # Same bank acc for same brand
            bank_routing_number="CBE-001",
            address="Kazanchis, Addis Ababa",
            latitude=9.0200,
            longitude=38.7700,
            is_open=True,
            fuel_types_available=json.dumps(["Diesel"]),
            current_fuel_price_per_liter=78.50
        )
        stations.append(s2)
        
        # OLibya Piassa
        s3 = FuelStation(
            id=uuid.uuid4(),
            name="OLibya Piassa",
            bank_account_number="200033334444",
            bank_routing_number="DASHEN-001",
            address="Piassa, Addis Ababa",
            latitude=9.0300,
            longitude=38.7500,
            is_open=True,
            fuel_types_available=json.dumps(["Benzene"]),
            current_fuel_price_per_liter=75.00
        )
        stations.append(s3)
        
        db.add_all(stations)
        db.flush()
        
        print("Creating Station Attendants...")
        # Attendant for Total Bole
        total_attendant = User(
            id=uuid.uuid4(),
            email="attendant@total.et",
            phone_number="+251911333333",
            username="total_attendant",
            password_hash=get_password_hash("total123"),
            full_name="Total Station Attendant",
            role=UserRole.STATION_ATTENDANT,
            station_id=s1.id,
            is_active=True,
            is_verified=True
        )
        db.add(total_attendant)
        
        # Attendant for OLibya
        olibya_attendant = User(
            id=uuid.uuid4(),
            email="attendant@olibya.et",
            phone_number="+251911444444",
            username="olibya_attendant",
            password_hash=get_password_hash("olibya123"),
            full_name="OLibya Station Attendant",
            role=UserRole.STATION_ATTENDANT,
            station_id=s3.id,
            is_active=True,
            is_verified=True
        )
        db.add(olibya_attendant)
        
        print("Adding Fuel Availability...")
        for station in stations:
            fa1 = FuelAvailability(
                id=uuid.uuid4(),
                station_id=station.id,
                fuel_type="Diesel",
                is_available=True,
                estimated_liters_remaining=5000.0,
                price_per_liter=78.50
            )
            fa2 = FuelAvailability(
                id=uuid.uuid4(),
                station_id=station.id,
                fuel_type="Benzene",
                is_available=True,
                estimated_liters_remaining=3000.0,
                price_per_liter=75.00
            )
            db.add(fa1)
            db.add(fa2)
            
        print("Creating Drivers...")
        # Driver 1 (CBE)
        d1 = Driver(
            id=uuid.uuid4(),
            name="Abebe Bikila",
            phone_number="+251911555555",
            preferred_bank_id=cbe.id,
            driver_license_number="ET-DR-1001",
            national_id="NID-1001",
            car_model="Toyota Corolla",
            car_year=2005,
            plate_number="A-12345",
            is_fayda_verified=True,
            kyc_level="TIER_1",
            fuel_tank_capacity_liters=50
        )
        db.add(d1)
        
        d1_user = User(
            id=uuid.uuid4(),
            email="abebe@gmail.com",
            phone_number="+251911555555",
            username="abebe",
            password_hash=get_password_hash("abebe123"),
            full_name="Abebe Bikila",
            role=UserRole.DRIVER,
            driver_id=d1.id,
            is_active=True,
            is_verified=True
        )
        db.add(d1_user)
        
        # Driver 2 (Dashen)
        d2 = Driver(
            id=uuid.uuid4(),
            name="Kebede Michael",
            phone_number="+251911666666",
            preferred_bank_id=dashen.id,
            driver_license_number="ET-DR-1002",
            national_id="NID-1002",
            car_model="Isuzu FSR",
            car_year=2010,
            plate_number="3-67890",
            is_fayda_verified=True,
            kyc_level="TIER_2",
            fuel_tank_capacity_liters=200
        )
        db.add(d2)
        
        d2_user = User(
            id=uuid.uuid4(),
            email="kebede@gmail.com",
            phone_number="+251911666666",
            username="kebede",
            password_hash=get_password_hash("kebede123"),
            full_name="Kebede Michael",
            role=UserRole.DRIVER,
            driver_id=d2.id,
            is_active=True,
            is_verified=True
        )
        db.add(d2_user)
        
        db.commit()
        print("Seeding complete!")
        
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
