"""
Helper script to initialize Alembic if not already done.
Run this once before your first migration.
"""

import os
import subprocess
import sys

def check_alembic_exists():
    """Check if alembic directory exists."""
    return os.path.exists("alembic") and os.path.exists("alembic.ini")

def init_alembic():
    """Initialize Alembic for database migrations."""
    print("Initializing Alembic...")
    try:
        subprocess.run(["alembic", "init", "alembic"], check=True)
        print("✅ Alembic initialized successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error initializing Alembic: {e}")
        return False
    except FileNotFoundError:
        print("❌ Alembic not found. Please install it: pip install alembic")
        return False

def update_alembic_config():
    """Update alembic.ini and env.py with correct configuration."""
    if not os.path.exists("alembic.ini"):
        print("❌ alembic.ini not found. Run 'alembic init alembic' first.")
        return False
    
    # Update alembic.ini - comment out sqlalchemy.url (we'll use env var)
    print("Updating alembic.ini...")
    with open("alembic.ini", "r") as f:
        content = f.read()
    
    # Comment out sqlalchemy.url line if not already commented
    lines = content.split("\n")
    updated_lines = []
    for line in lines:
        if line.strip().startswith("sqlalchemy.url"):
            updated_lines.append("# sqlalchemy.url = driver://user:pass@localhost/dbname")
            updated_lines.append("# Using DATABASE_URL from environment variable instead")
        else:
            updated_lines.append(line)
    
    with open("alembic.ini", "w") as f:
        f.write("\n".join(updated_lines))
    
    # Update alembic/env.py
    env_py_path = "alembic/env.py"
    if os.path.exists(env_py_path):
        print("Updating alembic/env.py...")
        with open(env_py_path, "r") as f:
            env_content = f.read()
        
        # Add imports and configuration
        imports_to_add = """
from app.core.config import settings
from app.db.base import Base
from app.models import entities  # Import all models
"""
        
        # Check if imports already exist
        if "from app.core.config import settings" not in env_content:
            # Find the line with "from alembic import context"
            lines = env_content.split("\n")
            insert_index = None
            for i, line in enumerate(lines):
                if "from alembic import context" in line:
                    insert_index = i + 1
                    break
            
            if insert_index:
                lines.insert(insert_index, imports_to_add.strip())
                env_content = "\n".join(lines)
        
        # Update target_metadata
        if "target_metadata = None" in env_content:
            env_content = env_content.replace(
                "target_metadata = None",
                "target_metadata = Base.metadata"
            )
        
        # Update sqlalchemy.url to use settings
        if "url = config.get_main_option(\"sqlalchemy.url\")" in env_content:
            env_content = env_content.replace(
                "url = config.get_main_option(\"sqlalchemy.url\")",
                "# url = config.get_main_option(\"sqlalchemy.url\")\n    url = settings.database_url"
            )
        
        with open(env_py_path, "w") as f:
            f.write(env_content)
        
        print("✅ alembic/env.py updated successfully!")
        return True
    
    return False

def main():
    print("=" * 50)
    print("Alembic Setup Helper")
    print("=" * 50)
    
    if check_alembic_exists():
        print("✅ Alembic is already initialized.")
        response = input("Do you want to update the configuration? (y/n): ")
        if response.lower() == 'y':
            update_alembic_config()
        else:
            print("Skipping configuration update.")
    else:
        print("Alembic not found. Initializing...")
        if init_alembic():
            update_alembic_config()
            print("\n" + "=" * 50)
            print("✅ Setup complete!")
            print("\nNext steps:")
            print("1. Review alembic/env.py to ensure all models are imported")
            print("2. Create initial migration: alembic revision --autogenerate -m 'Initial migration'")
            print("3. Apply migration: alembic upgrade head")
            print("=" * 50)
        else:
            print("\n❌ Setup failed. Please check the errors above.")
            sys.exit(1)

if __name__ == "__main__":
    main()

