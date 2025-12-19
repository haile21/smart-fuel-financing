"""
Script to create initial super admin user.
Run this after deployment to create the first admin user.
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.services.user_service import UserService
from app.models.entities import UserRole


def create_super_admin():
    """Create the first super admin user."""
    db = SessionLocal()
    try:
        service = UserService(db)
        
        # Check if super admin already exists
        existing = service.get_users_by_role(UserRole.SUPER_ADMIN)
        if existing:
            print(f"Super admin already exists: {existing[0].email}")
            return
        
        # Create super admin
        admin = service.create_user(
            role=UserRole.SUPER_ADMIN,
            email=os.getenv("SUPER_ADMIN_EMAIL", "admin@system.com"),
            username=os.getenv("SUPER_ADMIN_USERNAME", "superadmin"),
            password=os.getenv("SUPER_ADMIN_PASSWORD", "ChangeThisPassword123!"),
            full_name=os.getenv("SUPER_ADMIN_NAME", "System Administrator"),
            created_by_user_id=None,  # First user
        )
        print(f"✅ Super admin created successfully!")
        print(f"   ID: {admin.id}")
        print(f"   Email: {admin.email}")
        print(f"   Username: {admin.username}")
        print(f"   ⚠️  Please change the default password!")
    except Exception as e:
        print(f"❌ Error creating super admin: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    create_super_admin()

