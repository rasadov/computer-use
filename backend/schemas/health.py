from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., description="Health status (healthy/unhealthy)")


class DatabaseHealthResponse(BaseModel):
    status: str = Field(..., description="Health status (healthy/unhealthy)")
    error: Optional[str] = Field(
        None, description="Error message if unhealthy")


class RedisHealthResponse(BaseModel):
    status: str = Field(..., description="Health status (healthy/unhealthy)")
    error: Optional[str] = Field(
        None, description="Error message if unhealthy")
