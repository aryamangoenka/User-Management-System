"""
Configuration settings for FastAPI application
"""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Database settings
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/paktolus"
    SQLITE_URL: str = "sqlite+aiosqlite:///./fastapi_app.db"
    USE_SQLITE: bool = True  # Set to False to use PostgreSQL
    
    # Security settings
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS settings
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "*"]
    
    # File upload settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = [
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "application/pdf", "text/plain", "text/csv"
    ]
    UPLOAD_DIR: str = "uploads"
    
    # Pagination settings
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Redis settings (for caching)
    REDIS_URL: str = "redis://localhost:6379"
    
    @property
    def database_url(self) -> str:
        """Get the appropriate database URL"""
        return self.SQLITE_URL if self.USE_SQLITE else self.DATABASE_URL
    
    model_config = ConfigDict(env_file=".env")


settings = Settings() 