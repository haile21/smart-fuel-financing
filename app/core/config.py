from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    # Database - Render provides DATABASE_URL environment variable
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://neondb_owner:npg_hdaLNnvp0A1g@ep-weathered-violet-adx1wz8m-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
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
    
    # CORS settings
    cors_origins: str = os.getenv(
        "CORS_ORIGINS",
        "*"  # Default: allow all origins (for development). In production, use comma-separated list like "https://app.example.com,https://admin.example.com"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()


