import sys
import os

# Add current dir to path
sys.path.append(os.getcwd())

print("Verifying imports...")

try:
    print("1. Importing app.models...")
    import app.models
    print("   Success: app.models")

    print("2. Importing app.main...")
    from app.main import app
    print("   Success: app.main")
    
    print("3. Checking key models...")
    from app.models import User, Driver, Bank, Transaction
    print("   Success: Key models imported")

    print("\nALL CHECKS PASSED")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
