from pydantic import BaseModel, Field
from typing import Optional

class RateCheckRequest(BaseModel):
    client_key: Optional[str] = Field(None, description="The 'company:tier' string from the JWT audience claim.")
    ip_key: str = Field(..., description="The raw public IP address of the incoming request.")
    max_requests: Optional[int] = Field(None, alias="limit", gt=0)
    window_seconds: Optional[int] = Field(None, alias="window", gt=0)

    model_config = {
        "populate_by_name": True
    }