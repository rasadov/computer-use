from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
import os

class Settings(BaseSettings):
    APP_NAME: str = "Computer Use Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: str

    VNC_HOST: str = "localhost"
    VNC_PORT: int = 6080
    VNC_PASSWORD: Optional[str] = None

    ANTHROPIC_API_KEY: Optional[str] = None

    BACKEND_CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000"]

    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30

    @property
    def DATABASE_URL(self):
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @field_validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if not v:
            return f"postgresql+asyncpg://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}@{cls.POSTGRES_SERVER}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
        return v

settings = Settings(
    POSTGRES_SERVER=os.getenv("POSTGRES_SERVER") or "localhost",
    POSTGRES_USER=os.getenv("POSTGRES_USER") or "user",
    POSTGRES_PASSWORD=os.getenv("POSTGRES_PASSWORD") or "password",
    POSTGRES_DB=os.getenv("POSTGRES_DB") or "computer_use",
    POSTGRES_PORT=os.getenv("POSTGRES_PORT") or "5432",
    VNC_PASSWORD=os.getenv("VNC_PASSWORD"),
    ANTHROPIC_API_KEY=os.getenv("ANTHROPIC_API_KEY"),
)