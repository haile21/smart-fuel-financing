
import urllib.request
import urllib.parse
import json
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# App imports for DB access
sys.path.append(".")
from app.core.config import settings
from app.models import Merchant

# Constants
BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@smartfuel.com"
ADMIN_PASS = "admin123"

def post_json(url, data, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f"Bearer {token}"
        
    req = urllib.request.Request(
        url, 
        data=json.dumps(data).encode('utf-8'),
        headers=headers
    )
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
        raise

def get_json(url, token=None):
    headers = {}
    if token:
        headers['Authorization'] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
        raise

def get_any_merchant_id():
    engine = create_engine(str(settings.database_url))
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        merchant = db.query(Merchant).first()
        if merchant:
            return str(merchant.id)
        return None
    finally:
        db.close()

def verify_pricing():
    print("1. Getting Merchant ID...")
    merchant_id = get_any_merchant_id()
    if not merchant_id:
        print("❌ No merchants found in DB. Did you seed?")
        return
    print(f"   Found Merchant: {merchant_id}")

    print("\n2. Logging in as Admin (via OTP)...")
    admin_phone = "+251911000000"
    admin_role = "SUPER_ADMIN"
    
    try:
        # Request OTP
        print(f"   Requesting OTP for {admin_phone}...")
        otp_req = {
            "phone_number": admin_phone,
            "role": admin_role
        }
        otp_resp = post_json(f"{BASE_URL}/auth/otp/send", otp_req)
        
        # Extract Code
        message = otp_resp.get("message", "")
        if "Use " not in message:
            print("❌ Could not extract OTP from message.")
            return
        otp_code = message.split("Use ")[1].split(" ")[0].strip()
        print(f"   OTP Code: {otp_code}")
        
        # Verify OTP
        print(f"   Verifying OTP...")
        verify_req = {
            "phone_number": admin_phone,
            "otp_code": otp_code,
            "role": admin_role
        }
        verify_resp = post_json(f"{BASE_URL}/auth/otp/verify", verify_req)
        
        token = verify_resp["access_token"]
        print("   Logged in successfully. Token obtained.")
        
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return

    print("\n3. Creating Station with Per-Fuel Pricing...")
    station_payload = {
        "merchant_id": merchant_id,
        "name": "Test Station Pricing",
        "latitude": 9.0,
        "longitude": 38.0,
        "fuel_types": [
            {"fuel_type": "Diesel", "price": 80.50},
            {"fuel_type": "Benzene", "price": 77.00}
        ]
    }
    
    try:
        # endpoint: /admin/agent/onboard-station
        station_data = post_json(f"{BASE_URL}/admin/agent/onboard-station", station_payload, token)
        station_id = station_data["station_id"]
        print(f"   Station Created! ID: {station_id}")
    except Exception as e:
        print(f"❌ Failed to create station: {e}")
        return

    print("\n4. Verifying Availability & Prices...")
    try:
        availability = get_json(f"{BASE_URL}/stations/availability?station_id={station_id}")
        
        prices = {item['fuel_type']: item['price_per_liter'] for item in availability['fuel_availability']}
        print(f"   Prices Found: {prices}")
        
        if prices.get("Diesel") == 80.50 and prices.get("Benzene") == 77.00:
            print("\n✅ Verification PASSED: Prices match payload.")
        else:
            print("\n❌ Verification FAILED: Prices do not match.")
            
    except Exception as e:
        print(f"❌ Failed to get availability: {e}")

if __name__ == "__main__":
    verify_pricing()
