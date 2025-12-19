"""
Script to create initial super admin user.
Run this after deployment to create the first admin user.

Usage:
    python scripts/create_super_admin.py
    # or with environment variables:
    SUPER_ADMIN_EMAIL=admin@example.com SUPER_ADMIN_USERNAME=admin SUPER_ADMIN_PASSWORD=SecurePass123 python scripts/create_super_admin.py
"""

import sys
import os
import getpass

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.services.user_service import UserService
from app.models.entities import UserRole


def create_super_admin(
    email: str = None,
    username: str = None,
    password: str = None,
    full_name: str = None,
    interactive: bool = True
):
    """
    Create the first super admin user.
    
    Args:
        email: Email for super admin (from env var or interactive input)
        username: Username for super admin (from env var or interactive input)
        password: Password for super admin (from env var or interactive input)
        full_name: Full name for super admin (from env var or interactive input)
        interactive: If True, prompt for missing values interactively
    """
    db = SessionLocal()
    try:
        service = UserService(db)
        
        # Check if super admin already exists
        existing = service.get_users_by_role(UserRole.SUPER_ADMIN)
        if existing:
            print(f"⚠️  Super admin already exists!")
            print(f"   ID: {existing[0].id}")
            print(f"   Email: {existing[0].email}")
            print(f"   Username: {existing[0].username}")
            return existing[0]
        
        # Get values from environment variables or use defaults
        if not email:
            email = os.getenv("SUPER_ADMIN_EMAIL")
        if not username:
            username = os.getenv("SUPER_ADMIN_USERNAME")
        if not password:
            password = os.getenv("SUPER_ADMIN_PASSWORD")
        if not full_name:
            full_name = os.getenv("SUPER_ADMIN_NAME", "System Administrator")
        
        # Interactive prompts if values are missing and interactive mode is enabled
        if interactive:
            if not email:
                email = input("Enter super admin email (required): ").strip()
                if not email:
                    print("❌ Email is required!")
                    return None
            if not username:
                username = input("Enter super admin username (required): ").strip()
                if not username:
                    print("❌ Username is required!")
                    return None
            if not password:
                password = getpass.getpass("Enter super admin password (required): ").strip()
                if not password:
                    print("❌ Password is required!")
                    return None
                confirm_password = getpass.getpass("Confirm password: ").strip()
                if password != confirm_password:
                    print("❌ Passwords do not match!")
                    return None
            if not full_name or full_name == "System Administrator":
                name_input = input(f"Enter full name (default: System Administrator): ").strip()
                if name_input:
                    full_name = name_input
        
        # Validate required fields
        if not email or not username or not password:
            print("❌ Email, username, and password are required!")
            return None
        
        # Create super admin
        admin = service.create_user(
            role=UserRole.SUPER_ADMIN,
            email=email,
            username=username,
            password=password,
            full_name=full_name,
            created_by_user_id=None,  # First user
        )
        
        print(f"\n✅ Super admin created successfully!")
        print(f"   ID: {admin.id}")
        print(f"   Email: {admin.email}")
        print(f"   Username: {admin.username}")
        print(f"   Full Name: {admin.full_name}")
        print(f"   Role: {admin.role}")
        print(f"\n⚠️  IMPORTANT: Please change the default password after first login!")
        return admin
        
    except ValueError as e:
        print(f"❌ Validation error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error creating super admin: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()


if __name__ == "__main__":
    # Allow command-line arguments for non-interactive mode
    import argparse
    parser = argparse.ArgumentParser(description="Create a super admin user")
    parser.add_argument("--email", help="Super admin email")
    parser.add_argument("--username", help="Super admin username")
    parser.add_argument("--password", help="Super admin password")
    parser.add_argument("--full-name", help="Super admin full name")
    parser.add_argument("--non-interactive", action="store_true", help="Do not prompt for input")
    args = parser.parse_args()
    
    create_super_admin(
        email=args.email,
        username=args.username,
        password=args.password,
        full_name=getattr(args, 'full_name', None),
        interactive=not args.non_interactive
    )

