import sys
import os
from sqlalchemy import create_engine, inspect, text
from app.core.config import settings

# Add current dir to path
sys.path.append(os.getcwd())

def debug():
    engine = create_engine(settings.database_url)
    inspector = inspect(engine)
    
    print("\n--- Columns in fuelstation ---")
    columns = inspector.get_columns("fuelstation")
    for col in columns:
        print(f"Name: {col['name']}, Type: {col['type']}, Nullable: {col['nullable']}, Default: {col.get('default')}")

    print("\n--- Constraints in fuelstation ---")
    try:
        fks = inspector.get_foreign_keys("fuelstation")
        print(f"Foreign Keys: {fks}")
        unique = inspector.get_unique_constraints("fuelstation")
        print(f"Unique Constraints: {unique}")
    except Exception as e:
        print(f"Error inspecting constraints: {e}")

    print("\n--- Trying Raw Insert ---")
    with engine.connect() as conn:
        try:
            # First create a merchant
            result = conn.execute(text("INSERT INTO merchant (name) VALUES ('Debug Merchant') RETURNING id"))
            merchant_id = result.scalar()
            conn.commit()
            print(f"Created Merchant ID: {merchant_id}")

            # Try inserting station
            sql = """
            INSERT INTO fuelstation (
                merchant_id, name, address, latitude, longitude, phone_number, email, 
                is_open, fuel_types_available, current_fuel_price_per_liter, 
                operating_hours, last_status_update
            ) VALUES (
                :mid, 'Debug Station', 'Address', 9.0, 38.0, '+251000', 'debug@test.com', 
                true, '[]', 50.0, '{}', NOW()
            )
            """
            conn.execute(text(sql), {"mid": merchant_id})
            conn.commit()
            print("Raw Insert Successful")
        except Exception as e:
            print(f"Raw Insert Failed: {e}")
            if hasattr(e, 'orig'):
                print(f"Orig: {e.orig}")

if __name__ == "__main__":
    debug()
