import os

from pydantic_settings import BaseSettings


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

    ANTHROPIC_API_KEY: str

    @property
    def DATABASE_URL(self):
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings(
    POSTGRES_SERVER=os.getenv("POSTGRES_SERVER") or "localhost",
    POSTGRES_USER=os.getenv("POSTGRES_USER") or "user",
    POSTGRES_PASSWORD=os.getenv("POSTGRES_PASSWORD") or "password",
    POSTGRES_DB=os.getenv("POSTGRES_DB") or "computer_use",
    POSTGRES_PORT=os.getenv("POSTGRES_PORT") or "5432",
    ANTHROPIC_API_KEY=os.getenv("ANTHROPIC_API_KEY") or "",
)
