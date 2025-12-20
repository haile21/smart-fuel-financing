
import sys
import os
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Add current dir to path
sys.path.append(os.getcwd())

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.core.security import require_super_admin, require_bank_admin
from app.models import User, Bank

from sqlalchemy.pool import StaticPool

# --- Override DB with SQLite for testing ---
print("Setting up in-memory SQLite DB...")
engine = create_engine(
    "sqlite:///:memory:", 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

# Fix UUID for SQLite
@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
    dbapi_connection.create_function("uuid_generate_v4", 0, lambda: str(uuid.uuid4()))

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

# Dependency override
def override_get_db():
    # Auto-assign UUIDs
    @event.listens_for(TestingSessionLocal, "before_flush")
    def receive_before_flush(session, flush_context, instances):
        for obj in session.new:
            if hasattr(obj, "id") and getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
                
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Mock Authentication overrides
# We need to bypass actual auth logic and just inject a user/role
def override_require_super_admin():
    return User(id=1, role="SUPER_ADMIN", email="admin@example.com")

def override_require_bank_admin():
    return User(id=2, role="BANK_ADMIN", email="bank@example.com")

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[require_super_admin] = override_require_super_admin
app.dependency_overrides[require_bank_admin] = override_require_bank_admin

client = TestClient(app)

def verify_crud():
    print("Starting Bank CRUD Verification...")
    
    unique_suffix = str(uuid.uuid4())[:8]
    bank_name = f"Test Bank {unique_suffix}"
    bank_code = f"TB_{unique_suffix}"
    
    # 1. Create Bank
    print(f"1. Creating Bank: {bank_name}...")
    response = client.post("/banks/", json={
        "name": bank_name,
        "bank_code": bank_code,
        "account_number": "1234567890"
    })
    
    if response.status_code != 201:
        print(f"FAILED to create bank: {response.text}")
        return
        
    data = response.json()
    bank_id = data["id"]
    print(f"   Success! Bank ID: {bank_id}")
    assert data["name"] == bank_name
    assert data["bank_code"] == bank_code
    
    # 2. Get Bank by ID
    print(f"2. Getting Bank by ID: {bank_id}...")
    response = client.get(f"/banks/{bank_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == bank_id
    print("   Success!")
    
    # 3. List Banks
    print("3. Listing Banks...")
    response = client.get("/banks/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    found = any(b["id"] == bank_id for b in data)
    assert found
    print(f"   Success! Found {len(data)} banks.")
    
    # 4. Update Bank
    print("4. Updating Bank...")
    new_name = f"Updated {bank_name}"
    response = client.put(f"/banks/{bank_id}", json={
        "name": new_name
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name
    print(f"   Success! Name updated to: {data['name']}")
    
    # 5. Delete Bank
    print("5. Deleting Bank...")
    response = client.delete(f"/banks/{bank_id}")
    assert response.status_code == 204
    print("   Success!")
    
    # 6. Verify Deletion
    print("6. Verifying Deletion...")
    response = client.get(f"/banks/{bank_id}")
    assert response.status_code == 404
    print("   Success! Bank not found as expected.")
    
    print("\nALL CHECKS PASSED!")

if __name__ == "__main__":
    verify_crud()
