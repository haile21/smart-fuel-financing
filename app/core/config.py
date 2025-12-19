from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    # Database - Render provides DATABASE_URL environment variable
    database_url: str = os.getenv(
        "DATABASE_URL",
     )
    
    # JWT Settings
    secret_key: str = os.getenv(
        "SECRET_KEY",
        "your-secret-key-change-in-production-use-env-var"
    )
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 days
    
    # Render port (automatically set by Render)
    port: int = int(os.getenv("PORT", "8000"))

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()


