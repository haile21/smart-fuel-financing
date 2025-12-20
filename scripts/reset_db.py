
import sys
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())
load_dotenv()

from app.core.config import settings

def reset_database():
    print(f"Resetting database: {settings.database_url}")
    
    db_url = str(settings.database_url)
    engine = create_engine(db_url, echo=True)
    
    with engine.connect() as conn:
        print("Dropping all tables...")
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public;")) # Optional but good practice
        # conn.execute(text("GRANT ALL ON SCHEMA public TO neondb_owner;")) # Removed hardcoded role
        
        # Restore extensions
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        conn.commit()
        
    engine.dispose()
    print("Database reset complete.")

if __name__ == "__main__":
    if "postgresql" not in str(settings.database_url):
        print("This script is designed for PostgreSQL.")
        # Proceed anyway if user insists or just warn
        pass
        
    reset_database()
