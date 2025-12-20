
import sys
import os
import uuid
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add current dir to path
sys.path.append(os.getcwd())

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.core.security import require_super_admin, require_bank_admin
from app.models import User, Bank, Driver

# SQLite setup removed in favor of Mock


from unittest.mock import MagicMock

# Dependency override with Mock
def override_get_db():
    mock_db = MagicMock()
    # Mock driver retrieval
    mock_driver = Driver(
        id=uuid.uuid4(),
        car_model="Toyota",
        car_year=2018,
        fuel_tank_capacity_liters=50.0
    )
    # mock_db.get.return_value = mock_driver (Doesn't work well with MagicMock sometimes if not configured right)
    
    def side_effect_get(model, id):
        if model == Driver:
            return mock_driver
        return None
    
    mock_db.get.side_effect = side_effect_get
    
    yield mock_db

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def verify_ml_endpoint():
    print("Starting ML Score Verification...")
    
    # Generate random driver_id for request (mock db ignores it and returns mock_driver)
    driver_id = uuid.uuid4()
    
    # 2. Call Score Endpoint
    print("2. Calling /credit-scoring/credit/score...")
    
    payload = {
        "driver_id": str(driver_id), 
        # Wait, the Driver model uses Integer ID? 
        # Let's check Driver model. app/models/driver.py inherits from Base.
        # Base uses UUID! 
        # But ScoreRequest schema uses int! 
        # I need to fix ScoreRequest schema to use UUID or int depending on what ID type is used.
        # Based on my previous viewing of Base, it uses UUID.
        # So ScoreRequest schema in router is WRONG if it expects int.
        # I will check this.
        
        "monthly_income": 50000,
        "account_age_months": 24,
        "avg_monthly_balance": 25000,
        "monthly_inflow_avg": 52000,
        "monthly_outflow_avg": 45000,
        "balance_trend_3m": 0.1,
        "overdraft_count_6m": 1,
        "returned_payments_count": 0,
        "age": 35
    }
    
    # Need to verify if ID is int or str/uuid in schema
    # If schema says int, and DB uses UUID, it will 422.
    # I'll try passing 1 (dummy) and see if validation fails.
    # Ah, the driver I created above has a UUID.
    
    # Let's check the schema file or router content I just wrote.
    # "driver_id: int"
    # This is likely a bug since I switched everything to UUIDs. 
    # I will proceed to run this and EXPECT failure, then fix it.
    
    try:
        response = client.post("/credit-scoring/credit/score", json=payload)
    except Exception as e:
        print(f"Error calling endpoint: {e}")
        return

    print(f"Response Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("SUCCESS: Endpoint returned score.")
    else:
        print("FAILURE: Endpoint did not return 200.")

if __name__ == "__main__":
    verify_ml_endpoint()
