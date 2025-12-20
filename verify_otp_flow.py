
import urllib.request
import urllib.parse
import json
import sys

# Constants
BASE_URL = "http://localhost:8000"
PHONE_NUMBER = "+251911555555" # Abebe Bikila from seed_data
ROLE = "DRIVER"

def verify_otp_flow():
    print(f"Testing OTP Flow for {PHONE_NUMBER} as {ROLE}...")
    
    # helper for post json
    def post_json(url, data):
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
            raise

    # 1. Request OTP
    print(f"\n1. Requesting OTP from {BASE_URL}/auth/otp/send")
    try:
        req_payload = {"phone_number": PHONE_NUMBER, "role": ROLE}
        data = post_json(f"{BASE_URL}/auth/otp/send", req_payload)
        print("   Success! Response:", data)
        
        # Extract OTP
        message = data.get("message", "")
        if "Use " in message:
            otp_code = message.split("Use ")[1].split(" ")[0].strip()
            print(f"   Extracted OTP: {otp_code}")
        else:
            print("   ERROR: Could not extract OTP from message.")
            return

    except Exception as e:
        print(f"   FAILED to request OTP: {e}")
        return

    # 2. Verify OTP
    print(f"\n2. Verifying OTP at {BASE_URL}/auth/otp/verify")
    try:
        verify_payload = {
            "phone_number": PHONE_NUMBER,
            "otp_code": otp_code,
            "role": ROLE
        }
        data = post_json(f"{BASE_URL}/auth/otp/verify", verify_payload)
        
        print("   Success! Login successful.")
        print(f"   Access Token: {data.get('access_token')[:20]}...")
        print(f"   User ID: {data.get('user_id')}")
        print(f"   Role: {data.get('role')}")
        
        if data.get("role") == ROLE:
            print("\n✅ OTP Flow Verification PASSED")
        else:
            print(f"\n❌ Role mismatch. Expected {ROLE}, got {data.get('role')}")

    except Exception as e:
        print(f"   FAILED to verify OTP: {e}")

if __name__ == "__main__":
    verify_otp_flow()
