from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from app.core.config import settings


engine = create_engine(settings.database_url, future=True)
SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


