from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(description="Current service health state.", examples=["ok"])
